import { useEffect, useRef, useState } from "react";
import { useStore } from "../store/store";
import { EDIT_KINDS, REJECT_REASONS } from "../types";
import type { PitchCardT } from "../types";

/** Backend stamps are UTC but may arrive without a timezone suffix; treat
 * offset-less strings as UTC or every pitch reads hours off. */
function parseUtc(iso: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z");
}

/** "just now", "12m ago", "3h ago", "2d ago", then a date. */
function timeAgo(iso: string): string {
  const then = parseUtc(iso).getTime();
  if (Number.isNaN(then)) return "";
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)}d ago`;
  return parseUtc(iso).toLocaleDateString();
}

export function PitchCard({ card, index }: { card: PitchCardT; index: number }) {
  const sendFeedback = useStore((s) => s.sendFeedback);
  const original = useRef(card.text);
  const [text, setText] = useState(card.text);
  const [rating, setRating] = useState(card.rating);
  const [comment, setComment] = useState(card.comment);
  const [noteOpen, setNoteOpen] = useState(Boolean(card.comment));
  const [kindsOpen, setKindsOpen] = useState(false);
  const [kinds, setKinds] = useState<string[]>([]);
  const [reasonsOpen, setReasonsOpen] = useState(false);
  const [reasons, setReasons] = useState<string[]>([]);
  const [touched, setTouched] = useState(false);
  const [saved, setSaved] = useState(false);
  const starTimer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(starTimer.current), []);

  const edited = text.trim() !== original.current.trim();
  const rejected = card.status === "rejected";
  // fresh from the oven: glows gold until any interaction teaches the app
  const isNew =
    card.status === "pending" && rating === 0 && !card.comment && !touched;

  const acknowledge = () => setSaved(true);

  const rate = (n: number) => {
    setRating(n);
    setTouched(true);
    // debounce: settle on a star before persisting (avoids a call per click)
    window.clearTimeout(starTimer.current);
    starTimer.current = window.setTimeout(() => {
      sendFeedback(card, "rated", n, text, "");
      acknowledge();
    }, 500);
  };

  const saveNote = () => {
    if (!comment.trim()) return;
    setTouched(true);
    sendFeedback(card, "rated", rating, text, comment.trim());
    acknowledge();
  };

  const saveEdit = (tagged: string[]) => {
    original.current = text;
    setTouched(true);
    sendFeedback(card, "edited", rating, text, "", tagged);
    setKindsOpen(false);
    setKinds([]);
    acknowledge();
  };

  const doReject = (tapped: string[]) => {
    setTouched(true);
    sendFeedback(card, "rejected", rating, text, "", [], tapped);
    setReasonsOpen(false);
    setReasons([]);
    acknowledge();
  };

  return (
    <article
      className={`glass card pitch ${rejected ? "is-rejected" : ""} ${isNew ? "is-new" : ""} ${saved ? "just-saved" : ""}`}
      onAnimationEnd={(e) => {
        if (e.animationName === "savedpulse") setSaved(false);
      }}
    >
      <header className="pitch-head">
        <span className="pitch-n">
          Pitch {index + 1}
          <time
            className="pitch-time"
            dateTime={card.created_at}
            title={parseUtc(card.created_at).toLocaleString()}
          >
            {timeAgo(card.created_at)}
          </time>
        </span>
        <div className="pitch-tags">
          {isNew && <span className="new-flag">new</span>}
          {card.audit_removed.length > 0 && (
            <span className="audit-note" title={card.audit_removed.join(", ")}>
              {card.audit_removed.length} scrubbed
            </span>
          )}
          {card.status !== "pending" && (
            <span className={`status-flag ${card.status}`}>{card.status}</span>
          )}
        </div>
      </header>

      <textarea
        className="pitch-text"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setTouched(true);
        }}
        rows={Math.max(6, Math.ceil(text.length / 58))}
      />

      <div className="pitch-foot">
        <div className="stars">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              className={`star ${n <= rating ? "on" : ""}`}
              onClick={() => rate(n)}
              aria-label={`${n} star${n > 1 ? "s" : ""}`}
            >
              ★
            </button>
          ))}
        </div>
        <div className="pitch-actions">
          <button
            className="btn ghost sm"
            onClick={() => setNoteOpen((o) => !o)}
            aria-expanded={noteOpen}
          >
            {noteOpen ? "Hide note" : card.comment ? "Edit note" : "＋ Note"}
          </button>
          <button
            className="btn ghost sm"
            onClick={() => setReasonsOpen((o) => !o)}
            aria-expanded={reasonsOpen}
          >
            Reject
          </button>
          <button
            className="btn sm"
            onClick={() => {
              if (edited) {
                // ask what genre of change this was before it teaches anything
                setKindsOpen((o) => !o);
                return;
              }
              setTouched(true);
              sendFeedback(card, "accepted", rating, text);
              acknowledge();
            }}
          >
            {edited ? "Save edit" : "Accept"}
          </button>
        </div>
      </div>

      {reasonsOpen && (
        <div className="kind-picker">
          <span className="kind-q">
            What went wrong? One tap teaches the exact lesson — no guessing
            from the stars.
          </span>
          <div className="chips">
            {REJECT_REASONS.map((r) => (
              <button
                key={r}
                className={`chip toggle ${reasons.includes(r) ? "on" : "off"}`}
                onClick={() =>
                  setReasons((cur) =>
                    cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r],
                  )
                }
              >
                {r}
              </button>
            ))}
          </div>
          <div className="kind-actions">
            <button className="btn ghost sm" onClick={() => doReject([])}>
              Just reject
            </button>
            <button
              className="btn sm"
              onClick={() => doReject(reasons)}
              disabled={reasons.length === 0}
            >
              Reject{reasons.length > 0 ? ` — ${reasons.join(" + ")}` : ""}
            </button>
          </div>
        </div>
      )}

      {kindsOpen && edited && (
        <div className="kind-picker">
          <span className="kind-q">
            What kind of edit was that? Tagging it teaches the app the right
            lesson (a phrasing fix won't be read as "avoid this topic").
          </span>
          <div className="chips">
            {EDIT_KINDS.map((k) => (
              <button
                key={k}
                className={`chip toggle ${kinds.includes(k) ? "on" : "off"}`}
                onClick={() =>
                  setKinds((cur) =>
                    cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k],
                  )
                }
              >
                {k}
              </button>
            ))}
          </div>
          <div className="kind-actions">
            <button className="btn ghost sm" onClick={() => saveEdit([])}>
              Skip tagging
            </button>
            <button
              className="btn sm"
              onClick={() => saveEdit(kinds)}
              disabled={kinds.length === 0}
            >
              Save edit{kinds.length > 0 ? ` as ${kinds.join(" + ")}` : ""}
            </button>
          </div>
        </div>
      )}

      {noteOpen && (
        <div className="pitch-note">
          <textarea
            className="note-input"
            placeholder="Tell Pitchsmith what's working or not — it becomes a house rule for every artist…"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
          />
          <button
            className="btn sm"
            onClick={saveNote}
            disabled={!comment.trim() || comment.trim() === card.comment}
          >
            Save note
          </button>
        </div>
      )}
    </article>
  );
}

import { useState } from "react";
import { useStore } from "../store/store";
import { ARCHETYPE_LABELS } from "../types";
import type { Archetype, ExemplarT } from "../types";

/** The gold-pitch library: the curated examples every generation imitates.
 * This is the highest-leverage lever in the app — a new great reference here
 * beats any number of learned rules. */
export function GoldLibrary() {
  const { exemplars, loadingExemplars, addingExemplar, addExemplar } = useStore();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [notes, setNotes] = useState("");

  const save = async () => {
    if (await addExemplar(title.trim(), text.trim(), notes.trim())) {
      setTitle("");
      setText("");
      setNotes("");
    }
  };

  return (
    <div className="gold-lib">
      <section className="glass card">
        <div className="hub-head">
          <div>
            <h2 className="display hub-name">Gold pitches</h2>
            <p className="gold-sub">
              The reference pitches every new draft studies. Paste any pitch you
              consider excellent (yours or one you admire) and Pitchsmith will
              tag it and pull the most relevant ones into each brief. A great
              example here teaches more than a hundred rules.
            </p>
          </div>
        </div>
        <div className="gold-form">
          <input
            className="gold-input"
            placeholder="Title — artist / campaign (optional but helpful)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="gold-text"
            placeholder="Paste the full pitch text here…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={7}
          />
          <input
            className="gold-input"
            placeholder="Why is it great? (optional — helps retrieval and future you)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="kind-actions">
            <button
              className="btn primary"
              onClick={save}
              disabled={text.trim().length < 80 || addingExemplar}
            >
              {addingExemplar ? "Tagging…" : "Add to library"}
            </button>
          </div>
        </div>
      </section>

      {loadingExemplars && <p className="empty">Loading the library…</p>}
      {exemplars.map((ex) => (
        <ExemplarCard key={ex.id} ex={ex} />
      ))}
    </div>
  );
}

function ExemplarCard({ ex }: { ex: ExemplarT }) {
  const { setExemplarActive, deleteExemplar } = useStore();
  const [open, setOpen] = useState(false);
  const benched = ex.active !== 1;
  const arch = ARCHETYPE_LABELS[ex.archetype as Archetype];

  return (
    <article className={`glass card gold-card ${benched ? "benched" : ""}`}>
      <header className="hub-head">
        <div>
          <h3 className="gold-title">{ex.title || "Untitled reference"}</h3>
          <div className="chips gold-tags">
            {arch && <span className="chip gold-arch">{arch}</span>}
            {ex.tags.map((t) => (
              <span key={t} className="chip">{t}</span>
            ))}
            {ex.source === "seed" && <span className="chip">built-in</span>}
          </div>
        </div>
        <div className="hub-actions">
          <button className="btn ghost sm" onClick={() => setOpen((o) => !o)}>
            {open ? "Hide" : "Read"}
          </button>
          <button
            className="btn ghost sm"
            onClick={() => setExemplarActive(ex.id, benched)}
            title={benched
              ? "Put it back into retrieval"
              : "Keep it, but stop new pitches from imitating it"}
          >
            {benched ? "Unbench" : "Bench"}
          </button>
          <button
            className="btn ghost sm danger"
            onClick={() => {
              if (confirm("Remove this reference pitch from the library?")) {
                deleteExemplar(ex.id);
              }
            }}
          >
            Delete
          </button>
        </div>
      </header>
      {ex.notes && <p className="gold-notes">{ex.notes}</p>}
      {open ? (
        <p className="gold-body">{ex.text}</p>
      ) : (
        <p className="gold-body preview">{ex.text.slice(0, 220)}…</p>
      )}
    </article>
  );
}

import { useStore } from "../store/store";
import { ARCHETYPE_LABELS } from "../types";
import { HouseRulesCard } from "./HouseRulesCard";
import { InsightsBlurb } from "./InsightsBlurb";
import { PitchCard } from "./PitchCard";

export function ArtistHub() {
  const {
    detail, loadingDetail, activeGenerationId, generatingMore, house,
    newPitch, generateMore, saveArtistRules, saveHouseRules,
    resetArtist, deleteArtist,
  } = useStore();

  if (loadingDetail && !detail) {
    return <div className="glass card placeholder"><span className="spin" /> Loading project…</div>;
  }
  if (!detail) return null;

  return (
    <div className="hub">
      <header className="hub-head">
        <div>
          <h1 className="display hub-name">{detail.name}</h1>
          {detail.archetype && (
            <span className={`arch-badge ${detail.archetype === "Archetype_A" ? "arch-a" : "arch-b"}`}>
              {ARCHETYPE_LABELS[detail.archetype]}
            </span>
          )}
        </div>
        <div className="hub-actions">
          <button className="btn ghost sm" onClick={newPitch}>＋ New pitch</button>
          <button
            className="btn ghost sm danger"
            title="Delete all pitches and learnings for this artist; keep the artist"
            onClick={() => {
              if (window.confirm(
                `Clear all of ${detail.name}'s data? Every pitch, rating, and learned insight is deleted; the artist and their sheet stay. This can't be undone.`,
              )) resetArtist();
            }}
          >
            Reset data
          </button>
          <button
            className="btn ghost sm danger"
            title="Delete this artist and everything under them"
            onClick={() => {
              if (window.confirm(
                `Delete ${detail.name} entirely — pitches, ratings, learnings, everything? This can't be undone.`,
              )) deleteArtist();
            }}
          >
            Delete artist
          </button>
        </div>
      </header>

      <InsightsBlurb insights={detail.insights} onSave={saveArtistRules} />
      <HouseRulesCard house={house} onSave={saveHouseRules} />

      {detail.pitches.length === 0 ? (
        <div className="glass card placeholder muted">No pitches yet for this artist.</div>
      ) : (
        <div className="pitch-list">
          {detail.pitches.map((p, i) => (
            <PitchCard key={p.id} card={p} index={i} />
          ))}
        </div>
      )}

      {activeGenerationId != null && (
        <button
          className="btn more-btn"
          onClick={generateMore}
          disabled={generatingMore}
        >
          {generatingMore ? "Drafting more…" : "＋ Generate more pitches"}
        </button>
      )}
    </div>
  );
}

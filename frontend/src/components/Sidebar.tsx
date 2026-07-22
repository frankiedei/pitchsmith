import { useStore } from "../store/store";

const THEMES = ["apricot", "glass", "sage", "lavender", "sand", "mint", "ocean", "blush"];

function Stars({ n }: { n: number | null }) {
  if (!n) return <span className="mini-muted">unrated</span>;
  return (
    <span className="mini-stars" title={`${n}/5 average`}>
      {"★".repeat(Math.round(n))}
      <span className="mini-dim">{"★".repeat(5 - Math.round(n))}</span>
    </span>
  );
}

export function Sidebar() {
  const {
    health, theme, setTheme, artists, selectedArtistId, view,
    newPitch, selectArtist,
  } = useStore();

  return (
    <aside className="sidebar glass">
      <div className="side-top">
        <div className="brand">
          <span className="brand-tile display">P</span>
          <div>
            <h1 className="display brand-name">Pitchsmith</h1>
            <span className="brand-sub">Pitch hub</span>
          </div>
        </div>
        {health && (
          <span className={`keychip ${health.ai_key_set ? "on" : "off"}`}>
            {health.ai_key_set ? "AI on" : "no key"}
          </span>
        )}
      </div>

      <button
        className={`btn primary newpitch ${view === "compose" ? "active" : ""}`}
        onClick={newPitch}
      >
        ＋ New pitch
      </button>

      <div className="artist-list">
        <div className="list-label">Artists</div>
        {artists.length === 0 && <p className="empty">No projects yet. Start a pitch.</p>}
        {artists.map((a) => (
          <button
            key={a.id}
            className={`artist-row ${selectedArtistId === a.id ? "sel" : ""}`}
            onClick={() => selectArtist(a.id)}
          >
            <span className="artist-name">{a.name}</span>
            <span className="artist-meta">
              {a.pitch_count} pitch{a.pitch_count === 1 ? "" : "es"} · <Stars n={a.avg_rating} />
            </span>
          </button>
        ))}
      </div>

      <div className="side-foot">
        <select className="theme-pick" value={theme} onChange={(e) => setTheme(e.target.value)}>
          {THEMES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
    </aside>
  );
}

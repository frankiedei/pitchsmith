import { useState } from "react";
import { LENGTH_OPTIONS, useStore } from "../store/store";
import { ARCHETYPE_LABELS } from "../types";

const ACCEPTED = /\.(pdf|txt)$/i;

function UploadStep() {
  const { files, artistName, analyzing, set, analyze } = useStore();
  const [dragging, setDragging] = useState(false);
  const [dropErr, setDropErr] = useState<string | null>(null);

  function take(incoming: FileList | null) {
    if (!incoming || incoming.length === 0) return;
    const list = Array.from(incoming);
    const good = list.filter((f) => ACCEPTED.test(f.name));
    setDropErr(good.length < list.length ? "Skipped non .pdf/.txt files." : null);
    if (!good.length) return;
    const have = new Set(files.map((f) => f.name + f.size));
    const merged = [...files, ...good.filter((f) => !have.has(f.name + f.size))];
    set("files", merged);
  }

  const removeFile = (i: number) => set("files", files.filter((_, j) => j !== i));

  return (
    <section className="glass card composer">
      <div className="composer-head">
        <h2 className="display">New pitch</h2>
        <p className="sub">
          Drag the artist's one-sheet, bio, and press notes onto the box below.
          Add as many as you like. Pitchsmith reads them, pulls out the themes
          worth pitching, and you shape the rest with a couple of clicks.
        </p>
      </div>

      <label
        className={`drop ${files.length ? "has-file" : ""} ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragEnter={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragging(false); }}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          take(e.dataTransfer.files);
        }}
      >
        <input
          type="file"
          accept=".pdf,.txt"
          multiple
          onChange={(e) => { take(e.target.files); e.currentTarget.value = ""; }}
        />
        <span className="drop-hint">
          <strong>
            {dragging ? "Drop them here"
              : files.length ? "Add more sheets" : "Drag sheets here"}
          </strong>
          <em>{dropErr ?? "or click to browse · .pdf or .txt · multiple ok"}</em>
        </span>
      </label>

      {files.length > 0 && (
        <ul className="filelist">
          {files.map((f, i) => (
            <li key={f.name + i}>
              <span className="filelist-name">{f.name}</span>
              <button className="filelist-x" onClick={() => removeFile(i)} aria-label="Remove">✕</button>
            </li>
          ))}
        </ul>
      )}

      <label className="fld">
        <span>Artist name <i>(optional)</i></span>
        <input
          value={artistName}
          onChange={(e) => set("artistName", e.target.value)}
          placeholder="Autofilled from the sheet if left blank"
        />
      </label>

      <button className="btn primary" onClick={analyze} disabled={analyzing || !files.length}>
        {analyzing ? "Reading the sheets…"
          : `Analyze ${files.length || ""} sheet${files.length === 1 ? "" : "s"}`.trim()}
      </button>
    </section>
  );
}

function ComposeStep() {
  const {
    analysis, artistName, chips, newChip, suggesting, style, angle, customAngle,
    numOptions, length, styles, generating,
    set, toggleChip, addChip, suggestMore, newPitch, generate,
  } = useStore();
  if (!analysis) return null;
  const onCount = chips.filter((c) => c.on).length;

  return (
    <section className="glass card composer">
      <div className="compose-top">
        <div className="compose-title">
          <input
            className="artist-name-input display"
            value={artistName}
            onChange={(e) => set("artistName", e.target.value)}
            placeholder="Artist name"
          />
          <span className={`arch-badge ${analysis.archetype === "Archetype_A" ? "arch-a" : "arch-b"}`}>
            {ARCHETYPE_LABELS[analysis.archetype]}
          </span>
        </div>
        <button className="btn ghost sm" onClick={newPitch}>Start over</button>
      </div>

      {/* Themes — clickable include/exclude */}
      <div className="block">
        <div className="block-head">
          <span className="block-title">Themes to pitch</span>
          <span className="block-meta">{onCount} on</span>
        </div>
        <div className="chips">
          {chips.map((c, i) => (
            <button
              key={c.label + i}
              className={`chip toggle ${c.on ? "on" : "off"}`}
              onClick={() => toggleChip(i)}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="chip-add">
          <input
            value={newChip}
            onChange={(e) => set("newChip", e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addChip()}
            placeholder="Add a theme…"
          />
          <button className="btn ghost sm" onClick={addChip}>Add</button>
          <button className="btn ghost sm" onClick={suggestMore} disabled={suggesting}>
            {suggesting ? "…" : "✦ More"}
          </button>
        </div>
      </div>

      {/* Style + angle dropdowns */}
      <div className="fld-row">
        <label className="fld">
          <span>Style</span>
          <select value={style} onChange={(e) => set("style", e.target.value)}>
            {styles.map((s) => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
        </label>
        <label className="fld">
          <span>Length</span>
          <select value={length} onChange={(e) => set("length", e.target.value)}>
            {LENGTH_OPTIONS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </label>
        <label className="fld narrow">
          <span>Options</span>
          <select value={numOptions} onChange={(e) => set("numOptions", Number(e.target.value))}>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </select>
        </label>
      </div>

      <label className="fld">
        <span>Lead angle</span>
        <select value={angle} onChange={(e) => set("angle", e.target.value)}>
          {analysis.angle_options.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
          <option value="">Custom angle…</option>
        </select>
      </label>
      {angle === "" && (
        <input
          className="custom-angle"
          value={customAngle}
          onChange={(e) => set("customAngle", e.target.value)}
          placeholder="Write your own lead angle"
        />
      )}

      <button className="btn primary" onClick={generate} disabled={generating || !onCount}>
        {generating ? "Drafting…" : `Generate ${numOptions} pitches`}
      </button>
    </section>
  );
}

export function Composer() {
  const analysis = useStore((s) => s.analysis);
  return analysis ? <ComposeStep /> : <UploadStep />;
}

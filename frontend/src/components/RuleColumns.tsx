import { useState } from "react";

/** The two editable worked/avoid columns shared by the artist insights card
 * and the house-rules card. Deleting a rule tells the learner it was a wrong
 * inference (it won't come back); adding one pins it through refreshes. */
export function RuleColumns({
  worked, avoid, workedLabel, avoidLabel, onSave,
}: {
  worked: string[];
  avoid: string[];
  workedLabel: string;
  avoidLabel: string;
  onSave: (worked: string[], avoid: string[]) => void;
}) {
  return (
    <div className="insights-cols">
      <RuleColumn
        tone="worked" label={workedLabel} items={worked}
        onChange={(items) => onSave(items, avoid)}
      />
      <RuleColumn
        tone="avoid" label={avoidLabel} items={avoid}
        onChange={(items) => onSave(worked, items)}
      />
    </div>
  );
}

function RuleColumn({
  tone, label, items, onChange,
}: {
  tone: "worked" | "avoid";
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
}) {
  const [draft, setDraft] = useState("");

  const add = () => {
    const rule = draft.trim();
    if (!rule || items.some((i) => i.toLowerCase() === rule.toLowerCase())) {
      setDraft("");
      return;
    }
    onChange([...items, rule]);
    setDraft("");
  };

  return (
    <div className={`ins-col ${tone}`}>
      <span className="ins-col-label">{label}</span>
      <ul>
        {items.map((rule, i) => (
          <li key={`${rule}-${i}`}>
            <span className="rule-text">{rule}</span>
            <button
              className="rule-x"
              title="Delete — the app won't infer this again"
              aria-label={`Delete rule: ${rule}`}
              onClick={() => onChange(items.filter((_, j) => j !== i))}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
      <div className="rule-add">
        <input
          value={draft}
          placeholder="Add your own rule…"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
        />
        <button className="btn ghost sm" onClick={add} disabled={!draft.trim()}>
          Add
        </button>
      </div>
    </div>
  );
}

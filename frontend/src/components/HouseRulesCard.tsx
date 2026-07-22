import type { HouseRules } from "../types";
import { RuleColumns } from "./RuleColumns";

/** The label-wide learnings: rules generalized from EVERY artist's feedback,
 * applied to every future batch. Editable — deletions stay gone, additions
 * are pinned through future refreshes. */
export function HouseRulesCard({
  house, onSave,
}: {
  house: HouseRules | null;
  onSave: (worked: string[], avoid: string[]) => void;
}) {
  if (!house || (!house.blurb && !house.worked.length && !house.avoid.length)) {
    return null;
  }
  return (
    <section className="glass card insights house-rules">
      <div className="insights-head">
        <span className="insights-title">House rules</span>
        <span className="insights-avg">
          learned across all artists
          {house.count ? ` · ${house.count} rated` : ""}
        </span>
      </div>
      {house.blurb && <p className="insights-blurb">{house.blurb}</p>}
      <RuleColumns
        worked={house.worked}
        avoid={house.avoid}
        workedLabel="Every pitch"
        avoidLabel="Never again"
        onSave={onSave}
      />
    </section>
  );
}

import type { Insights } from "../types";
import { RuleColumns } from "./RuleColumns";

export function InsightsBlurb({
  insights, onSave,
}: {
  insights: Insights | null;
  onSave: (worked: string[], avoid: string[]) => void;
}) {
  if (!insights || (!insights.blurb && !insights.worked.length && !insights.avoid.length)) {
    return null;
  }
  return (
    <section className="glass card insights">
      <div className="insights-head">
        <span className="insights-title">What's working</span>
        {insights.avg_rating != null && (
          <span className="insights-avg">avg {insights.avg_rating}/5 · {insights.count} rated</span>
        )}
      </div>
      {insights.blurb && <p className="insights-blurb">{insights.blurb}</p>}
      <RuleColumns
        worked={insights.worked}
        avoid={insights.avoid}
        workedLabel="Do more"
        avoidLabel="Avoid"
        onSave={onSave}
      />
    </section>
  );
}

import type { AnalysisSummary } from "../../lib/api/types";
import { formatNumber } from "../../lib/utils/format";
import { formatUtcDateTime } from "./presentation";
import { formatMetricValue } from "./comparison-presentation";

interface ComparisonSummaryCardsProps {
  baselineLabel: string;
  comparisonLabel: string;
  baseline: AnalysisSummary;
  comparison: AnalysisSummary;
  durationMs: number;
}

export function ComparisonSummaryCards({
  baselineLabel,
  comparisonLabel,
  baseline,
  comparison,
  durationMs
}: ComparisonSummaryCardsProps) {
  return (
    <section aria-labelledby="comparison-summary-heading" className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="comparison-summary-heading" className="font-display text-lg font-semibold">
            Dönem özeti
          </h2>
          <p className="text-sm text-inkSoft">
            Her iki kart aynı process-local event snapshotından filtrelenir.
          </p>
        </div>
        <p className="text-xs text-inkSoft">Karşılaştırma süresi: {durationMs.toFixed(2)} ms</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <PeriodCard label={baselineLabel} summary={baseline} tone="baseline" />
        <PeriodCard label={comparisonLabel} summary={comparison} tone="comparison" />
      </div>
    </section>
  );
}

function PeriodCard({
  label,
  summary,
  tone
}: {
  label: string;
  summary: AnalysisSummary;
  tone: "baseline" | "comparison";
}) {
  return (
    <article
      className={`rounded-2xl border p-4 ${
        tone === "baseline" ? "border-accent2/25 bg-accent2/5" : "border-accent/25 bg-accent/5"
      }`}
    >
      <p className="text-xs uppercase tracking-[0.16em] text-inkSoft">{label}</p>
      <p className="mt-2 font-display text-3xl font-semibold text-ink">
        {formatNumber(summary.matched_event_count)}
      </p>
      <p className="text-xs text-inkSoft">eşleşen event</p>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-xs text-inkSoft">Hata + kritik</dt>
          <dd className="mt-1 font-medium text-ink">
            {formatMetricValue(summary.error_rate, "ratio")}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-inkSoft">Event / dk</dt>
          <dd className="mt-1 font-medium text-ink">
            {formatMetricValue(summary.events_per_minute, "events_per_minute")}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-inkSoft">Servis</dt>
          <dd className="mt-1 font-medium text-ink">
            {formatNumber(summary.unique_service_count)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-inkSoft">Host</dt>
          <dd className="mt-1 font-medium text-ink">{formatNumber(summary.unique_host_count)}</dd>
        </div>
      </dl>

      <p className="mt-4 text-xs text-inkSoft">
        {summary.earliest_timestamp && summary.latest_timestamp
          ? `${formatUtcDateTime(summary.earliest_timestamp)} – ${formatUtcDateTime(
              summary.latest_timestamp
            )}`
          : "Eşleşen event zaman aralığı yok."}
      </p>
    </article>
  );
}

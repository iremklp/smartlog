import { StatusBadge } from "../../components/StatusBadge";
import type { MetricComparison } from "../../lib/api/types";
import {
  METRIC_LABELS,
  directionLabel,
  formatAbsoluteChange,
  formatComparisonNote,
  formatMetricValue,
  formatPercentChange,
  interpretationLabel,
  interpretationTone
} from "./comparison-presentation";

interface MetricComparisonPanelProps {
  metrics: MetricComparison[];
  baselineLabel: string;
  comparisonLabel: string;
}

export function MetricComparisonPanel({
  metrics,
  baselineLabel,
  comparisonLabel
}: MetricComparisonPanelProps) {
  return (
    <section aria-labelledby="metric-comparison-heading" className="grid gap-3">
      <div>
        <h2 id="metric-comparison-heading" className="font-display text-lg font-semibold">
          Metrik değişimleri
        </h2>
        <p className="text-sm text-inkSoft">
          Yüzde değişim baseline değerine göre hesaplanır; oran metriklerinin mutlak farkı yüzde
          puan olarak gösterilir.
        </p>
      </div>

      {metrics.length === 0 ? (
        <p role="status" className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm">
          Bu karşılaştırmada metrik seçilmedi.
        </p>
      ) : (
        <dl className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {metrics.map((metric) => (
            <MetricCard
              key={metric.metric}
              metric={metric}
              baselineLabel={baselineLabel}
              comparisonLabel={comparisonLabel}
            />
          ))}
        </dl>
      )}
    </section>
  );
}

function MetricCard({
  metric,
  baselineLabel,
  comparisonLabel
}: {
  metric: MetricComparison;
  baselineLabel: string;
  comparisonLabel: string;
}) {
  const lowSample = metric.notes.includes("LOW_SAMPLE_SIZE");
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <dt className="text-sm font-medium text-ink">
          {METRIC_LABELS[metric.metric] ?? metric.metric}
        </dt>
        <StatusBadge
          label={
            lowSample
              ? "Düşük örnek · yorum güvenilmez"
              : interpretationLabel(metric.interpretation)
          }
          tone={lowSample ? "warn" : interpretationTone(metric.interpretation)}
        />
      </div>
      <dd className="mt-3 font-display text-2xl font-semibold text-ink">
        {formatPercentChange(metric.percent_change)}
      </dd>
      <p className="mt-1 text-xs text-inkSoft">
        {directionLabel(metric.direction)} · {formatAbsoluteChange(metric)}
      </p>

      <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-white/10 pt-3 text-sm">
        <div>
          <dt className="truncate text-xs text-inkSoft" title={baselineLabel}>
            {baselineLabel}
          </dt>
          <dd className="mt-1 font-medium">
            {formatMetricValue(metric.baseline_value, metric.unit)}
          </dd>
        </div>
        <div>
          <dt className="truncate text-xs text-inkSoft" title={comparisonLabel}>
            {comparisonLabel}
          </dt>
          <dd className="mt-1 font-medium">
            {formatMetricValue(metric.comparison_value, metric.unit)}
          </dd>
        </div>
      </dl>

      <p className="mt-3 text-xs font-medium text-inkSoft">
        {lowSample
          ? "Düşük örnek nedeniyle eşik kararı bastırıldı"
          : metric.significant
            ? "Değişim eşiğini aşıyor"
            : "Değişim eşiğinin altında"}
      </p>
      {metric.notes.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-warn">
          {metric.notes.map((note) => (
            <li key={note}>{formatComparisonNote(note)}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

import type { AnalysisSummary } from "../../lib/api/types";
import { formatDate, formatNumber } from "../../lib/utils/format";

interface AnalysisSummaryCardsProps {
  summary: AnalysisSummary | null;
  generatedAt: string;
  durationMs: number;
}

export function AnalysisSummaryCards({
  summary,
  generatedAt,
  durationMs
}: AnalysisSummaryCardsProps) {
  if (!summary) {
    return (
      <section aria-labelledby="analysis-summary-heading">
        <h2 id="analysis-summary-heading" className="font-display text-lg font-semibold">
          Özet
        </h2>
        <p className="mt-2 rounded-xl border border-warn/30 bg-warn/10 p-4 text-sm text-warn">
          Bu yanıtta özet modülü bulunmuyor.
        </p>
      </section>
    );
  }

  const metrics = [
    {
      label: "Eşleşen event",
      value: formatNumber(summary.matched_event_count),
      detail: `${formatNumber(summary.input_event_count)} event tarandı`
    },
    {
      label: "Hata + kritik oranı",
      value: formatRate(summary.error_rate),
      detail: `${formatNumber(summary.error_or_critical_count)} event`
    },
    {
      label: "Dakikadaki event",
      value: summary.events_per_minute === null ? "—" : formatDecimal(summary.events_per_minute),
      detail: summary.time_span_seconds === null ? "Zaman aralığı yok" : "Seçili dönem"
    },
    {
      label: "Benzersiz servis",
      value: formatNumber(summary.unique_service_count),
      detail: `${formatNumber(summary.unique_event_type_count)} event type`
    },
    {
      label: "Benzersiz host",
      value: formatNumber(summary.unique_host_count),
      detail: `${formatNumber(summary.unique_parser_count)} parser`
    }
  ];

  return (
    <section aria-labelledby="analysis-summary-heading" className="grid gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="analysis-summary-heading" className="font-display text-lg font-semibold">
            Analiz özeti
          </h2>
          <p className="text-sm text-inkSoft">
            {formatDate(summary.earliest_timestamp)} – {formatDate(summary.latest_timestamp)}
          </p>
        </div>
        <p className="text-xs text-inkSoft">
          Üretim: {formatDate(generatedAt)} · {durationMs.toFixed(2)} ms
        </p>
      </div>
      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <dt className="text-xs uppercase tracking-[0.16em] text-inkSoft">{metric.label}</dt>
            <dd className="mt-2 font-display text-2xl font-semibold text-ink">{metric.value}</dd>
            <p className="mt-1 text-xs text-inkSoft">{metric.detail}</p>
          </div>
        ))}
      </dl>
    </section>
  );
}

function formatRate(value: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "percent",
    maximumFractionDigits: 1
  }).format(value);
}

function formatDecimal(value: number): string {
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
}

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import type { TimelineResult } from "../../lib/api/types";
import { formatNumber } from "../../lib/utils/format";
import { boundTimelineBuckets, formatUtcDateTime } from "./presentation";

interface AnalysisTimelineChartProps {
  timeline: TimelineResult | null;
}

export function AnalysisTimelineChart({ timeline }: AnalysisTimelineChartProps) {
  if (!timeline || timeline.buckets.length === 0) {
    return (
      <section aria-labelledby="analysis-timeline-heading">
        <h2 id="analysis-timeline-heading" className="font-display text-lg font-semibold">
          Zaman çizgisi
        </h2>
        <p
          role="status"
          className="mt-2 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-inkSoft"
        >
          Seçili dönem için timeline verisi bulunamadı.
        </p>
      </section>
    );
  }

  const bounded = boundTimelineBuckets(timeline.buckets);
  const chartData = bounded.buckets.map((bucket) => ({
    ...bucket,
    label: formatBucketLabel(bucket.start),
    problem_count: bucket.error_count + bucket.critical_count
  }));

  return (
    <figure aria-labelledby="analysis-timeline-heading" className="grid gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="analysis-timeline-heading" className="font-display text-lg font-semibold">
            Event hareketi
          </h2>
          <p className="text-sm text-inkSoft">
            Event hacmi ile error + critical sayısı aynı UTC bucketlarında gösterilir.
          </p>
        </div>
        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-inkSoft">
          {formatNumber(timeline.bucket_seconds)} saniye / bucket
          {bounded.coarsened
            ? ` · en fazla ${formatNumber(
                timeline.bucket_seconds * bounded.maxBucketsPerPoint
              )} saniye / görsel nokta`
            : null}
        </span>
      </div>

      <div className="h-80 w-full" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
            <XAxis dataKey="label" stroke="#9eb0c3" minTickGap={28} tick={{ fontSize: 12 }} />
            <YAxis stroke="#9eb0c3" allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: "#121c29",
                border: "1px solid rgba(255,255,255,0.16)",
                borderRadius: "12px"
              }}
            />
            <Legend />
            <Bar
              dataKey="event_count"
              name="Event"
              fill="#21d4fd"
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="problem_count"
              name="Error + critical"
              stroke="#ff6f6f"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <figcaption className="text-xs text-inkSoft">
        {bounded.coarsened
          ? `${formatNumber(bounded.originalCount)} API bucketı, tarayıcı performansı için ${formatNumber(bounded.buckets.length)} görsel noktada birleştirildi. Birleştirilmiş noktalarda percentile gösterilmez.`
          : `${formatNumber(bounded.buckets.length)} bucket, API sırası korunarak gösteriliyor.`}
      </figcaption>

      <details className="rounded-xl border border-white/10 bg-black/15">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-ink">
          Erişilebilir timeline tablosu
        </summary>
        <div className="max-h-96 overflow-auto border-t border-white/10">
          <table className="w-full min-w-[680px] text-left text-sm">
            <caption className="sr-only">
              Zaman bucketlarına göre event, warning, error, critical ve HTTP 5xx sayıları
            </caption>
            <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-inkSoft">
              <tr>
                <th scope="col" className="px-3 py-2">
                  Başlangıç
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Event
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Warning
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Error
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Critical
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  HTTP 5xx
                </th>
              </tr>
            </thead>
            <tbody>
              {bounded.buckets.map((bucket) => (
                <tr key={`${bucket.start}-${bucket.end}`} className="border-t border-white/5">
                  <th scope="row" className="px-3 py-2 font-medium text-ink">
                    {formatUtcDateTime(bucket.start)}
                  </th>
                  <td className="px-3 py-2 text-right">{formatNumber(bucket.event_count)}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(bucket.warning_count)}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(bucket.error_count)}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(bucket.critical_count)}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(bucket.status_5xx_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

function formatBucketLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${new Intl.DateTimeFormat("tr-TR", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23"
  }).format(date)} UTC`;
}

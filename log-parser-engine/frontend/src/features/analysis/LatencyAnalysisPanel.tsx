import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { LatencyAnalysis } from "../../lib/api/types";
import { formatNumber } from "../../lib/utils/format";
import { formatUtcDateTime } from "./presentation";

interface LatencyAnalysisPanelProps {
  latency: LatencyAnalysis | null;
}

export function LatencyAnalysisPanel({ latency }: LatencyAnalysisPanelProps) {
  if (!latency) {
    return (
      <section aria-labelledby="analysis-latency-heading">
        <h2 id="analysis-latency-heading" className="font-display text-lg font-semibold">
          Latency analizi
        </h2>
        <p
          role="status"
          className="mt-2 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-inkSoft"
        >
          Bu yanıtta latency modülü bulunmuyor.
        </p>
      </section>
    );
  }

  const percentileRows = Object.entries(latency.percentiles.percentile_values)
    .map(([percentile, value]) => ({ percentile, value }))
    .sort((left, right) => Number(left.percentile) - Number(right.percentile));

  return (
    <section aria-labelledby="analysis-latency-heading" className="grid gap-3">
      <div>
        <h2 id="analysis-latency-heading" className="font-display text-lg font-semibold">
          Latency analizi
        </h2>
        <p className="text-sm text-inkSoft">
          Süre istatistikleri deterministic olarak hesaplanır; yaklaşık değerler varsa sonuç içinde
          açıkça işaretlenir.
        </p>
      </div>

      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          label="Örnek"
          value={formatNumber(latency.sample_count)}
          detail={`Eksik: ${formatNumber(latency.missing_count)}`}
        />
        <MetricCard
          label="P95"
          value={formatMilliseconds(percentileValue(latency, "95"))}
          detail="ms"
        />
        <MetricCard label="Ortalama" value={formatMilliseconds(latency.mean_ms)} detail="ms" />
        <MetricCard label="Median" value={formatMilliseconds(latency.median_ms)} detail="ms" />
        <MetricCard label="Maksimum" value={formatMilliseconds(latency.maximum_ms)} detail="ms" />
      </dl>

      {latency.latency_buckets.length > 0 ? (
        <div className="h-72 rounded-2xl border border-white/10 bg-black/20 p-3" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={latency.latency_buckets}
              margin={{ top: 8, right: 12, left: 8, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
              <XAxis
                dataKey="label"
                stroke="#9eb0c3"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={60}
              />
              <YAxis stroke="#9eb0c3" allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: "#121c29",
                  border: "1px solid rgba(255,255,255,0.16)",
                  borderRadius: "12px"
                }}
              />
              <Bar
                dataKey="count"
                name="Event"
                fill="#21d4fd"
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <details className="rounded-xl border border-white/10 bg-black/15" open>
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-ink">
            Percentile tablosu
          </summary>
          <div className="max-h-72 overflow-auto border-t border-white/10">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Latency percentile dağılımı (milisaniye)</caption>
              <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-inkSoft">
                <tr>
                  <th scope="col" className="px-3 py-2">
                    Percentile
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    Değer (ms)
                  </th>
                </tr>
              </thead>
              <tbody>
                {percentileRows.length > 0 ? (
                  percentileRows.map((row) => (
                    <tr key={row.percentile} className="border-t border-white/5">
                      <th scope="row" className="px-3 py-2 font-medium text-ink">
                        P{row.percentile}
                      </th>
                      <td className="px-3 py-2 text-right">{formatMilliseconds(row.value)}</td>
                    </tr>
                  ))
                ) : (
                  <tr className="border-t border-white/5">
                    <td className="px-3 py-3 text-inkSoft" colSpan={2}>
                      Percentile verisi bulunamadı.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </details>

        <details className="rounded-xl border border-white/10 bg-black/15" open>
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-ink">
            En yavaş eventler
          </summary>
          <div className="max-h-72 overflow-auto border-t border-white/10">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">En yavaş event örnekleri (milisaniye)</caption>
              <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-inkSoft">
                <tr>
                  <th scope="col" className="px-3 py-2">
                    Zaman
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    Süre (ms)
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Servis
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Event type
                  </th>
                </tr>
              </thead>
              <tbody>
                {latency.slowest_events.length > 0 ? (
                  latency.slowest_events.map((event) => (
                    <tr key={event.event_id} className="border-t border-white/5">
                      <th scope="row" className="px-3 py-2 font-medium text-ink">
                        {formatUtcDateTime(event.timestamp)}
                      </th>
                      <td className="px-3 py-2 text-right">
                        {formatMilliseconds(event.duration_ms)}
                      </td>
                      <td className="px-3 py-2">{event.service ?? "—"}</td>
                      <td className="px-3 py-2">{event.event_type ?? "—"}</td>
                    </tr>
                  ))
                ) : (
                  <tr className="border-t border-white/5">
                    <td className="px-3 py-3 text-inkSoft" colSpan={4}>
                      Yavaş event örneği bulunamadı.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </details>
      </div>

      {latency.warnings.length > 0 ? (
        <p className="rounded-lg border border-warn/30 bg-warn/10 p-3 text-xs text-warn">
          Uyarılar: {latency.warnings.join(" · ")}
        </p>
      ) : null}
    </section>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-inkSoft">{label}</p>
      <p className="mt-2 font-display text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-xs text-inkSoft">{detail}</p>
    </div>
  );
}

function percentileValue(latency: LatencyAnalysis, percentile: string): number | null {
  const values = latency.percentiles.percentile_values;
  return (
    values[percentile] ?? values[`${percentile}.0`] ?? values[String(Number(percentile))] ?? null
  );
}

function formatMilliseconds(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
}

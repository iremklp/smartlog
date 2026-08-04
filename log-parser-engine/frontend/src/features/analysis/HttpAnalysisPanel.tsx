import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { HTTPAnalysis } from "../../lib/api/types";
import { formatNumber } from "../../lib/utils/format";

interface HttpAnalysisPanelProps {
  http: HTTPAnalysis | null;
}

export function HttpAnalysisPanel({ http }: HttpAnalysisPanelProps) {
  if (!http) {
    return (
      <section aria-labelledby="analysis-http-heading">
        <h2 id="analysis-http-heading" className="font-display text-lg font-semibold">
          HTTP analizi
        </h2>
        <p
          role="status"
          className="mt-2 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-inkSoft"
        >
          Bu yanıtta HTTP modülü bulunmuyor.
        </p>
      </section>
    );
  }

  const statusClassData = http.status_class_distribution.items.map((item) => ({
    label: item.display_value,
    count: item.count
  }));

  return (
    <section aria-labelledby="analysis-http-heading" className="grid gap-3">
      <div>
        <h2 id="analysis-http-heading" className="font-display text-lg font-semibold">
          HTTP analizi
        </h2>
        <p className="text-sm text-inkSoft">
          HTTP event kapsamı, status sınıfları ve endpoint hata eğilimleri tek snapshot üzerinde
          hesaplanır.
        </p>
      </div>

      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <MetricCard
          label="HTTP event"
          value={formatNumber(http.http_event_count)}
          detail="Toplam"
        />
        <MetricCard
          label="2xx"
          value={formatNumber(http.success_count)}
          detail={formatRatio(http.success_rate)}
        />
        <MetricCard
          label="4xx"
          value={formatNumber(http.client_error_count)}
          detail={formatRatio(http.client_error_rate)}
        />
        <MetricCard
          label="5xx"
          value={formatNumber(http.server_error_count)}
          detail={formatRatio(http.server_error_rate)}
        />
        <MetricCard
          label="Hata oranı"
          value={formatRatio(http.total_error_rate)}
          detail="4xx + 5xx"
        />
        <MetricCard
          label="Endpoint"
          value={formatNumber(http.endpoint_distribution.unique_value_count)}
          detail="Benzersiz"
        />
      </dl>

      {statusClassData.length > 0 ? (
        <div className="h-64 rounded-2xl border border-white/10 bg-black/20 p-3" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={statusClassData} margin={{ top: 8, right: 12, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
              <XAxis dataKey="label" stroke="#9eb0c3" tick={{ fontSize: 12 }} />
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
                fill="#f9d423"
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
            Method dağılımı
          </summary>
          <div className="max-h-72 overflow-auto border-t border-white/10">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">HTTP method dağılımı</caption>
              <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-inkSoft">
                <tr>
                  <th scope="col" className="px-3 py-2">
                    Method
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    Sayı
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    Yüzde
                  </th>
                </tr>
              </thead>
              <tbody>
                {http.method_distribution.items.length > 0 ? (
                  http.method_distribution.items.map((item) => (
                    <tr key={item.key} className="border-t border-white/5">
                      <th scope="row" className="px-3 py-2 font-medium text-ink">
                        {item.display_value}
                      </th>
                      <td className="px-3 py-2 text-right">{formatNumber(item.count)}</td>
                      <td className="px-3 py-2 text-right">{item.percentage.toFixed(1)}%</td>
                    </tr>
                  ))
                ) : (
                  <tr className="border-t border-white/5">
                    <td className="px-3 py-3 text-inkSoft" colSpan={3}>
                      Method dağılımı bulunamadı.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </details>

        <details className="rounded-xl border border-white/10 bg-black/15" open>
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-ink">
            En yüksek hata oranlı endpointler
          </summary>
          <div className="max-h-72 overflow-auto border-t border-white/10">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Endpoint hata oranı sıralaması</caption>
              <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-inkSoft">
                <tr>
                  <th scope="col" className="px-3 py-2">
                    Endpoint
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    İstek
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    Hata
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    Oran
                  </th>
                </tr>
              </thead>
              <tbody>
                {http.highest_error_endpoints.length > 0 ? (
                  http.highest_error_endpoints.map((endpoint) => (
                    <tr key={endpoint.endpoint} className="border-t border-white/5">
                      <th scope="row" className="px-3 py-2 font-medium text-ink">
                        {endpoint.endpoint}
                      </th>
                      <td className="px-3 py-2 text-right">
                        {formatNumber(endpoint.request_count)}
                      </td>
                      <td className="px-3 py-2 text-right">{formatNumber(endpoint.error_count)}</td>
                      <td className="px-3 py-2 text-right">{formatRatio(endpoint.error_rate)}</td>
                    </tr>
                  ))
                ) : (
                  <tr className="border-t border-white/5">
                    <td className="px-3 py-3 text-inkSoft" colSpan={4}>
                      Endpoint hata oranı verisi bulunamadı.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </details>
      </div>

      {http.warnings.length > 0 ? (
        <p className="rounded-lg border border-warn/30 bg-warn/10 p-3 text-xs text-warn">
          Uyarılar: {http.warnings.join(" · ")}
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

function formatRatio(value: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "percent",
    maximumFractionDigits: 1
  }).format(value);
}

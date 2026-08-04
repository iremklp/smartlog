import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { DistributionResult } from "../../lib/api/types";
import { formatNumber } from "../../lib/utils/format";
import { boundDistributionItems } from "./presentation";

interface DistributionPanelsProps {
  distributions: DistributionResult[];
}

export function DistributionPanels({ distributions }: DistributionPanelsProps) {
  if (distributions.length === 0) {
    return (
      <section aria-labelledby="analysis-distributions-heading">
        <h2 id="analysis-distributions-heading" className="font-display text-lg font-semibold">
          Dağılımlar
        </h2>
        <p
          role="status"
          className="mt-2 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-inkSoft"
        >
          Bu yanıtta dağılım modülü bulunmuyor.
        </p>
      </section>
    );
  }

  return (
    <section aria-labelledby="analysis-distributions-heading" className="grid gap-3">
      <div>
        <h2 id="analysis-distributions-heading" className="font-display text-lg font-semibold">
          Tanısal dağılımlar
        </h2>
        <p className="text-sm text-inkSoft">
          Seçilen boyutlarda en sık değerler; yüzdeler API toplamına göre hesaplanır.
        </p>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {distributions.map((distribution) => (
          <DistributionCard key={distribution.field} distribution={distribution} />
        ))}
      </div>
    </section>
  );
}

function DistributionCard({ distribution }: { distribution: DistributionResult }) {
  const bounded = boundDistributionItems(distribution);
  const items = bounded.items;
  const hiddenCategoryCount =
    (distribution.truncated ? Math.max(distribution.unique_value_count - items.length, 0) : 0) +
    bounded.hiddenItemCount;
  const chartHeight = Math.max(220, items.length * 34 + 44);
  const fieldLabel = formatFieldLabel(distribution.field);

  return (
    <figure
      aria-labelledby={`distribution-${distribution.field}`}
      className="grid gap-3 rounded-2xl border border-white/10 bg-black/20 p-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3
            id={`distribution-${distribution.field}`}
            className="font-display font-semibold text-ink"
          >
            {fieldLabel}
          </h3>
          <p className="text-xs text-inkSoft">
            {formatNumber(distribution.unique_value_count)} benzersiz ·{" "}
            {formatNumber(distribution.missing_count)} eksik
          </p>
        </div>
        {distribution.truncated || bounded.clientTruncated ? (
          <span className="rounded-full border border-warn/30 bg-warn/10 px-2 py-1 text-xs text-warn">
            Top N
          </span>
        ) : null}
      </div>

      {items.length > 0 ? (
        <div style={{ height: chartHeight }} aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={items}
              layout="vertical"
              margin={{ top: 4, right: 16, left: 16, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis type="number" allowDecimals={false} stroke="#9eb0c3" />
              <YAxis
                type="category"
                dataKey="display_value"
                width={110}
                stroke="#9eb0c3"
                tick={{ fontSize: 11 }}
              />
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
                radius={[0, 6, 6, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="rounded-lg border border-white/10 p-3 text-sm text-inkSoft">
          Bu boyut için değer bulunamadı.
        </p>
      )}

      <figcaption className="text-xs text-inkSoft">
        {formatNumber(distribution.matched_value_count)} eşleşen değer; gösterilmeyen gruplar{" "}
        {formatNumber(distribution.other_count + bounded.hiddenEventCount)} event içerir.
        {bounded.clientTruncated
          ? ` Tarayıcı sınırı nedeniyle ${formatNumber(bounded.hiddenItemCount)} ek kategori gizlendi.`
          : null}
      </figcaption>

      {distribution.truncated || bounded.clientTruncated ? (
        <p className="rounded-lg border border-warn/30 bg-warn/10 px-3 py-2 text-xs text-warn">
          Görünüm sınırı aktif: {formatNumber(hiddenCategoryCount)} kategori ve{" "}
          {formatNumber(distribution.other_count + bounded.hiddenEventCount)} event tabloda
          gösterilmiyor.
        </p>
      ) : null}

      <details className="rounded-lg border border-white/10">
        <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
          {fieldLabel} dağılım tablosu
        </summary>
        <div className="max-h-80 overflow-auto border-t border-white/10">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">
              {fieldLabel} değerlerinin sırası, sayısı ve yüzdesi
            </caption>
            <thead className="sticky top-0 bg-panel text-xs uppercase text-inkSoft">
              <tr>
                <th scope="col" className="px-3 py-2">
                  Sıra
                </th>
                <th scope="col" className="px-3 py-2">
                  Değer
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
              {items.length > 0 ? (
                items.map((item) => (
                  <tr key={`${item.rank}-${item.key}`} className="border-t border-white/5">
                    <td className="px-3 py-2">{item.rank}</td>
                    <th scope="row" className="px-3 py-2 font-medium">
                      {item.display_value}
                    </th>
                    <td className="px-3 py-2 text-right">{formatNumber(item.count)}</td>
                    <td className="px-3 py-2 text-right">{item.percentage.toFixed(1)}%</td>
                  </tr>
                ))
              ) : (
                <tr className="border-t border-white/5">
                  <td colSpan={4} className="px-3 py-3 text-inkSoft">
                    Bu boyut için dağılım satırı bulunamadı.
                  </td>
                </tr>
              )}
              {hiddenCategoryCount > 0 ? (
                <tr className="border-t border-white/10 bg-warn/5 text-xs text-warn">
                  <td colSpan={4} className="px-3 py-2">
                    {formatNumber(hiddenCategoryCount)} kategori görünüm sınırı nedeniyle gizlendi.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

function formatFieldLabel(field: string): string {
  return field
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

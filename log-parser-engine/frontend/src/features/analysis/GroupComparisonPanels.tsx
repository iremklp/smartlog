import { StatusBadge } from "../../components/StatusBadge";
import type { GroupComparison } from "../../lib/api/types";
import { formatNumber } from "../../lib/utils/format";
import { GROUP_LABELS, groupAndBoundComparisons } from "./comparison-presentation";

interface GroupComparisonPanelsProps {
  comparisons: GroupComparison[];
  baselineLabel: string;
  comparisonLabel: string;
}

export function GroupComparisonPanels({
  comparisons,
  baselineLabel,
  comparisonLabel
}: GroupComparisonPanelsProps) {
  const sections = groupAndBoundComparisons(comparisons);

  return (
    <section aria-labelledby="group-comparison-heading" className="grid gap-3">
      <div>
        <h2 id="group-comparison-heading" className="font-display text-lg font-semibold">
          Grup hareketleri
        </h2>
        <p className="text-sm text-inkSoft">
          Gruplar, dönem payındaki mutlak değişime göre backend sırası korunarak gösterilir.
        </p>
      </div>

      {sections.length === 0 ? (
        <p role="status" className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm">
          Seçilen grup boyutlarında karşılaştırılabilir sonuç bulunamadı.
        </p>
      ) : (
        <div className="grid gap-4">
          {sections.map((section) => (
            <article
              key={section.field}
              className="rounded-2xl border border-white/10 bg-black/20"
              aria-labelledby={`group-comparison-${section.field}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <h3 id={`group-comparison-${section.field}`} className="font-display font-semibold">
                  {GROUP_LABELS[section.field] ?? section.field}
                </h3>
                <span className="text-xs text-inkSoft">
                  {formatNumber(section.originalCount)} grup
                </span>
              </div>
              <div className="overflow-auto border-t border-white/10">
                <table className="w-full min-w-[860px] text-left text-sm">
                  <caption className="sr-only">
                    {GROUP_LABELS[section.field] ?? section.field} için {baselineLabel} ve{" "}
                    {comparisonLabel} dönemlerinin karşılaştırması
                  </caption>
                  <thead className="bg-panel text-xs uppercase tracking-wide text-inkSoft">
                    <tr>
                      <th scope="col" className="px-4 py-3">
                        Grup
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        {baselineLabel}
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        {comparisonLabel}
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        Sayı farkı
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        Pay farkı
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Durum
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {section.items.map((item) => (
                      <GroupRow key={`${section.field}-${item.key}`} item={item} />
                    ))}
                  </tbody>
                </table>
              </div>
              {section.hiddenCount > 0 ? (
                <p className="border-t border-white/10 px-4 py-3 text-xs text-inkSoft">
                  Tarayıcı sınırı nedeniyle {formatNumber(section.hiddenCount)} ek grup
                  gösterilmedi.
                </p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function GroupRow({ item }: { item: GroupComparison }) {
  const status = groupStatus(item);
  return (
    <tr className="border-t border-white/5">
      <th scope="row" className="max-w-xs px-4 py-3 font-medium text-ink">
        <span className="block truncate" title={item.key}>
          {item.key}
        </span>
      </th>
      <td className="px-4 py-3 text-right">
        {formatNumber(item.baseline_count)}
        <span className="ml-1 text-xs text-inkSoft">
          ({formatPercentage(item.baseline_percentage)})
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        {formatNumber(item.comparison_count)}
        <span className="ml-1 text-xs text-inkSoft">
          ({formatPercentage(item.comparison_percentage)})
        </span>
      </td>
      <td className="px-4 py-3 text-right font-medium">
        {item.absolute_change > 0 ? "+" : ""}
        {formatNumber(item.absolute_change)}
        <span className="ml-1 block text-xs font-normal text-inkSoft sm:inline">
          {formatRelativeChange(item)}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        {item.percentage_point_change > 0 ? "+" : ""}
        {formatDecimal(item.percentage_point_change)} yp
      </td>
      <td className="px-4 py-3">
        <StatusBadge label={status.label} tone={status.tone} />
      </td>
    </tr>
  );
}

function groupStatus(item: GroupComparison): {
  label: string;
  tone: "ok" | "warn" | "err" | "info";
} {
  const lowSample = item.metric_comparisons.some((metric) =>
    metric.notes.includes("LOW_SAMPLE_SIZE")
  );
  if (item.new_group) {
    return { label: lowSample ? "Yeni grup · düşük örnek" : "Yeni grup", tone: "info" };
  }
  if (item.disappeared_group) {
    return {
      label: lowSample ? "Kaybolan grup · düşük örnek" : "Kaybolan grup",
      tone: "warn"
    };
  }
  if (lowSample) return { label: "Düşük örnek", tone: "warn" };
  if (item.significant) return { label: "Eşik aşıldı", tone: "warn" };
  return { label: "Eşik altı", tone: "info" };
}

function formatRelativeChange(item: GroupComparison): string {
  if (item.percent_change === null || !Number.isFinite(item.percent_change)) {
    return item.new_group ? "Yeni" : item.disappeared_group ? "Kayboldu" : "—";
  }
  const prefix = item.percent_change > 0 ? "+" : "";
  return `${prefix}${formatDecimal(item.percent_change)}%`;
}

function formatPercentage(value: number): string {
  return `${formatDecimal(value)}%`;
}

function formatDecimal(value: number): string {
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
}

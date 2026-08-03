import type {
  AnalysisInsight,
  ChangeDirection,
  GroupComparison,
  MetricComparison,
  MetricInterpretation
} from "../../lib/api/types";

export const MAX_GROUP_ROWS_PER_FIELD = 20;

export const METRIC_LABELS: Record<string, string> = {
  event_count: "Event sayısı",
  error_rate: "Hata + kritik oranı",
  critical_rate: "Kritik + fatal oranı",
  average_duration_ms: "Ortalama gecikme",
  p50_duration_ms: "P50 gecikme",
  p95_duration_ms: "P95 gecikme",
  p99_duration_ms: "P99 gecikme",
  server_error_rate: "HTTP 5xx oranı",
  client_error_rate: "HTTP 4xx oranı",
  throughput: "Dakikadaki event"
};

export const GROUP_LABELS: Record<string, string> = {
  endpoint: "Endpoint",
  event_type: "Event type",
  host: "Host",
  http_status: "HTTP status",
  parser: "Parser",
  parser_name: "Parser",
  service: "Service",
  severity: "Severity",
  status_code: "HTTP status"
};

export interface BoundedGroupSection {
  field: string;
  items: GroupComparison[];
  originalCount: number;
  hiddenCount: number;
}

export function groupAndBoundComparisons(
  comparisons: GroupComparison[],
  maxRows = MAX_GROUP_ROWS_PER_FIELD
): BoundedGroupSection[] {
  if (!Number.isInteger(maxRows) || maxRows < 1) {
    throw new Error("maxRows must be a positive integer");
  }
  const grouped = new Map<string, GroupComparison[]>();
  for (const comparison of comparisons) {
    const items = grouped.get(comparison.group_field) ?? [];
    items.push(comparison);
    grouped.set(comparison.group_field, items);
  }
  return Array.from(grouped, ([field, items]) => ({
    field,
    items: items.slice(0, maxRows),
    originalCount: items.length,
    hiddenCount: Math.max(0, items.length - maxRows)
  }));
}

export function formatMetricValue(value: number | null, unit: string | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "—";
  }
  if (unit === "ratio") {
    return new Intl.NumberFormat("tr-TR", {
      style: "percent",
      maximumFractionDigits: 2
    }).format(value);
  }
  if (unit === "ms") {
    return `${formatDecimal(value)} ms`;
  }
  if (unit === "events_per_minute") {
    return `${formatDecimal(value)} / dk`;
  }
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
}

export function formatPercentChange(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Hesaplanamadı";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatDecimal(value)}%`;
}

export function formatAbsoluteChange(comparison: MetricComparison): string {
  const value = comparison.absolute_change;
  if (value === null || !Number.isFinite(value)) {
    return "—";
  }
  const prefix = value > 0 ? "+" : "";
  if (comparison.unit === "ratio") {
    return `${prefix}${formatDecimal(value * 100)} yüzde puan`;
  }
  if (comparison.unit === "ms") {
    return `${prefix}${formatDecimal(value)} ms`;
  }
  if (comparison.unit === "events_per_minute") {
    return `${prefix}${formatDecimal(value)} / dk`;
  }
  return `${prefix}${formatDecimal(value)}`;
}

export function directionLabel(direction: ChangeDirection): string {
  const labels: Record<ChangeDirection, string> = {
    increase: "Artış",
    decrease: "Azalış",
    unchanged: "Değişmedi",
    new: "Yeni",
    removed: "Kayboldu",
    undefined: "Tanımsız"
  };
  return labels[direction];
}

export function interpretationLabel(interpretation: MetricInterpretation): string {
  const labels: Record<MetricInterpretation, string> = {
    improved: "İyileşme",
    degraded: "Kötüleşme",
    neutral: "Nötr",
    unknown: "Belirsiz"
  };
  return labels[interpretation];
}

export function interpretationTone(
  interpretation: MetricInterpretation
): "ok" | "warn" | "err" | "info" {
  if (interpretation === "improved") return "ok";
  if (interpretation === "degraded") return "err";
  if (interpretation === "unknown") return "warn";
  return "info";
}

export function formatComparisonNote(note: string): string {
  const known: Record<string, string> = {
    LOW_SAMPLE_SIZE: "Örnek sayısı güvenilir değişim değerlendirmesi için yetersiz.",
    "baseline is zero; percent change is undefined":
      "Başlangıç değeri sıfır olduğu için yüzde değişim hesaplanamadı.",
    "percent change exceeds finite numeric range":
      "Yüzde değişim gösterilebilir sayısal aralığı aşıyor.",
    "normalized by observed time span": "Throughput gözlenen zaman aralığına normalize edildi.",
    "time-span normalization disabled; raw event counts compared":
      "Throughput yerine ham event sayıları karşılaştırıldı."
  };
  return known[note] ?? note;
}

export function insightKey(insight: AnalysisInsight): string {
  return `${insight.code}-${insight.metric ?? "general"}`;
}

function formatDecimal(value: number): string {
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(
    Object.is(value, -0) ? 0 : value
  );
}

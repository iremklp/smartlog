import { StatusBadge } from "../../components/StatusBadge";
import type { AnalysisInsight } from "../../lib/api/types";
import { insightKey } from "./comparison-presentation";

export function ComparisonInsights({ insights }: { insights: AnalysisInsight[] }) {
  if (insights.length === 0) {
    return null;
  }

  return (
    <section aria-labelledby="comparison-insights-heading" className="grid gap-3">
      <div>
        <h2 id="comparison-insights-heading" className="font-display text-lg font-semibold">
          Deterministik bulgular
        </h2>
        <p className="text-sm text-inkSoft">
          Bulgular ölçülen değişimlerden üretilir; kök neden veya yapay zekâ yorumu değildir.
        </p>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {insights.map((insight) => (
          <article
            key={insightKey(insight)}
            className="rounded-2xl border border-white/10 bg-black/20 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="font-semibold text-ink">{insightTitle(insight)}</h3>
              <StatusBadge
                label={insightLevelLabel(insight.level)}
                tone={insightTone(insight.level)}
              />
            </div>
            <p className="mt-2 text-sm text-inkSoft">{insight.message}</p>
            {insight.recommendations.length > 0 ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink">
                {insight.recommendations.map((recommendation) => (
                  <li key={recommendation}>{recommendation}</li>
                ))}
              </ul>
            ) : null}
            <p className="mt-3 font-mono text-xs text-inkSoft">{insight.code}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function insightTitle(insight: AnalysisInsight): string {
  const known: Record<string, string> = {
    ERROR_SPIKE: "Hata oranı yükseldi",
    SERVER_ERROR_SPIKE: "Sunucu hata oranı yükseldi"
  };
  return known[insight.code] ?? insight.title;
}

function insightLevelLabel(level: AnalysisInsight["level"]): string {
  const labels: Record<AnalysisInsight["level"], string> = {
    critical: "Kritik",
    warning: "Uyarı",
    info: "Bilgi"
  };
  return labels[level];
}

function insightTone(level: AnalysisInsight["level"]): "warn" | "err" | "info" {
  if (level === "critical") return "err";
  if (level === "warning") return "warn";
  return "info";
}

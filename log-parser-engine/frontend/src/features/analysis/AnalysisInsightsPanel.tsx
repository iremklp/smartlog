import { StatusBadge } from "../../components/StatusBadge";
import type { AnalysisInsight } from "../../lib/api/types";

interface AnalysisInsightsPanelProps {
  insights: AnalysisInsight[];
}

export function AnalysisInsightsPanel({ insights }: AnalysisInsightsPanelProps) {
  return (
    <section aria-labelledby="analysis-insights-heading" className="grid gap-3">
      <div>
        <h2 id="analysis-insights-heading" className="font-display text-lg font-semibold">
          Deterministik bulgular
        </h2>
        <p className="text-sm text-inkSoft">
          Bulgular eşik ve metrik değişimlerinden türetilir; kök neden çıkarımı veya yapay zekâ
          yorumu değildir.
        </p>
      </div>

      {insights.length === 0 ? (
        <p
          role="status"
          className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-inkSoft"
        >
          Seçili kapsam için insight üretilmedi.
        </p>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {insights.map((insight) => (
            <article
              key={`${insight.code}-${insight.message}`}
              className="rounded-2xl border border-white/10 bg-black/20 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="font-semibold text-ink">{insight.title}</h3>
                <StatusBadge label={levelLabel(insight.level)} tone={levelTone(insight.level)} />
              </div>
              <p className="mt-2 text-sm text-inkSoft">{insight.message}</p>
              {insight.recommendations.length > 0 ? (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink">
                  {insight.recommendations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              <p className="mt-3 font-mono text-xs text-inkSoft">{insight.code}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function levelLabel(level: AnalysisInsight["level"]): string {
  const labels: Record<AnalysisInsight["level"], string> = {
    critical: "Kritik",
    warning: "Uyarı",
    info: "Bilgi"
  };
  return labels[level];
}

function levelTone(level: AnalysisInsight["level"]): "warn" | "err" | "info" {
  if (level === "critical") return "err";
  if (level === "warning") return "warn";
  return "info";
}

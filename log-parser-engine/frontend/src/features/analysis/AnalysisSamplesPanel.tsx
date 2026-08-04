import type { AnalysisEventSample } from "../../lib/api/types";
import { formatNumber } from "../../lib/utils/format";
import { formatUtcDateTime } from "./presentation";

interface AnalysisSamplesPanelProps {
  samples: AnalysisEventSample[];
}

const MAX_SAMPLE_ROWS = 100;

export function AnalysisSamplesPanel({ samples }: AnalysisSamplesPanelProps) {
  const visibleSamples = samples.slice(0, MAX_SAMPLE_ROWS);
  const hiddenSampleCount = Math.max(samples.length - visibleSamples.length, 0);

  return (
    <section aria-labelledby="analysis-samples-heading" className="grid gap-3">
      <div>
        <h2 id="analysis-samples-heading" className="font-display text-lg font-semibold">
          Örnek eventler
        </h2>
        <p className="text-sm text-inkSoft">
          Bu tablo yalnız bounded örnekleri gösterir; tam event içeriğini veya raw logu içermez.
        </p>
      </div>

      {samples.length === 0 ? (
        <p
          role="status"
          className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-inkSoft"
        >
          İstekte örnek event üretimi kapalı veya sonuç boş.
        </p>
      ) : (
        <div className="rounded-xl border border-white/10 bg-black/15">
          {hiddenSampleCount > 0 ? (
            <p className="border-b border-warn/30 bg-warn/10 px-3 py-2 text-xs text-warn">
              Görünüm sınırı aktif: {formatNumber(hiddenSampleCount)} örnek event gösterilmiyor.
            </p>
          ) : null}
          <div className="max-h-80 overflow-auto">
            <table className="w-full min-w-[740px] text-left text-sm">
              <caption className="sr-only">Analiz için dönen bounded örnek event listesi</caption>
              <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-inkSoft">
                <tr>
                  <th scope="col" className="px-3 py-2">
                    Zaman
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Severity
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Service
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Event type
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Önizleme
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibleSamples.map((sample) => (
                  <tr key={sample.event_id} className="border-t border-white/5">
                    <th scope="row" className="px-3 py-2 font-medium text-ink">
                      {formatUtcDateTime(sample.timestamp)}
                    </th>
                    <td className="px-3 py-2">{sample.severity}</td>
                    <td className="px-3 py-2">{sample.service ?? "—"}</td>
                    <td className="px-3 py-2">{sample.event_type ?? "—"}</td>
                    <td className="px-3 py-2 text-inkSoft">{sample.message_preview}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="border-t border-white/10 px-3 py-2 text-xs text-inkSoft">
            {formatNumber(visibleSamples.length)} örnek event gösteriliyor.
          </p>
        </div>
      )}
    </section>
  );
}

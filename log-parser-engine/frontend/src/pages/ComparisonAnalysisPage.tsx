import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { AnalyticsTabs } from "../features/analysis/AnalyticsTabs";
import { ComparisonInsights } from "../features/analysis/ComparisonInsights";
import { ComparisonRequestForm } from "../features/analysis/ComparisonRequestForm";
import { ComparisonSummaryCards } from "../features/analysis/ComparisonSummaryCards";
import { GroupComparisonPanels } from "../features/analysis/GroupComparisonPanels";
import { MetricComparisonPanel } from "../features/analysis/MetricComparisonPanel";
import { formatUtcDateTime } from "../features/analysis/presentation";
import {
  buildComparisonRequest,
  createDefaultComparisonRequestState,
  type ComparisonRequestState
} from "../features/analysis/request-state";
import { ApiError } from "../lib/api/client";
import { compareEvents } from "../lib/api/endpoints";
import type { ComparisonRequest } from "../lib/api/types";
import { formatNumber } from "../lib/utils/format";

export function ComparisonAnalysisPage() {
  const [defaultValues] = useState(() => createDefaultComparisonRequestState());
  const [lastRequest, setLastRequest] = useState<ComparisonRequest | null>(null);
  const comparisonMutation = useMutation({
    mutationFn: (request: ComparisonRequest) => compareEvents(request)
  });

  function runComparison(values: ComparisonRequestState): void {
    const request = buildComparisonRequest(values);
    setLastRequest(request);
    comparisonMutation.mutate(request);
  }

  function rerunComparison(): void {
    if (lastRequest) {
      comparisonMutation.mutate(lastRequest);
    }
  }

  const result = comparisonMutation.isSuccess ? comparisonMutation.data : undefined;
  const bothPeriodsEmpty =
    result?.baseline_event_count === 0 && result.comparison_event_count === 0;

  return (
    <div className="grid gap-4">
      <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-white/10 bg-panel/70 p-5 backdrop-blur">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-accent2">Period comparison</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Dönem Karşılaştırma</h2>
          <p className="mt-2 max-w-3xl text-sm text-inkSoft">
            Aynı process-local snapshot içindeki iki yarı açık zaman aralığını karşılaştırın. Eşik
            göstergeleri deterministik değişim kurallarıdır; istatistiksel anlamlılık veya kök neden
            iddiası değildir.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label="process-local" tone="warn" />
          {comparisonMutation.isPending ? (
            <StatusBadge label="comparing" tone="info" />
          ) : comparisonMutation.isError ? (
            <StatusBadge label="error" tone="err" />
          ) : result ? (
            <StatusBadge label="ready" tone="ok" />
          ) : (
            <StatusBadge label="awaiting input" tone="info" />
          )}
        </div>
      </header>

      <AnalyticsTabs />

      <Panel
        title="Karşılaştırma kapsamı"
        subtitle="Başlangıç dahil, bitiş hariçtir. Presetler eşit uzunlukta ve bitişik iki dönem oluşturur."
      >
        <ComparisonRequestForm
          defaultValues={defaultValues}
          pending={comparisonMutation.isPending}
          onSubmit={runComparison}
        />
      </Panel>

      <section
        aria-live="polite"
        aria-busy={comparisonMutation.isPending}
        aria-label="Dönem karşılaştırma sonucu"
        className="grid gap-4"
      >
        {comparisonMutation.isIdle ? <InitialComparisonState /> : null}

        {comparisonMutation.isPending ? (
          <div
            role="status"
            className="rounded-2xl border border-white/10 bg-panel/80 p-6 text-sm text-inkSoft"
          >
            Dönem snapshotları karşılaştırılıyor…
          </div>
        ) : null}

        {comparisonMutation.isError ? (
          <ComparisonErrorState
            error={comparisonMutation.error}
            pending={comparisonMutation.isPending}
            onRetry={rerunComparison}
          />
        ) : null}

        {result ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-panel/70 px-4 py-3 text-sm">
              <p className="text-inkSoft">
                <span className="font-medium text-ink">{result.baseline_label}</span>:{" "}
                {formatNumber(result.baseline_event_count)} event ·{" "}
                <span className="font-medium text-ink">{result.comparison_label}</span>:{" "}
                {formatNumber(result.comparison_event_count)} event
              </p>
              <button
                type="button"
                disabled={comparisonMutation.isPending}
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
                onClick={rerunComparison}
              >
                Aynı isteği yeniden çalıştır
              </button>
            </div>

            {lastRequest ? <SubmittedComparisonScope request={lastRequest} /> : null}

            {result.warnings.length > 0 ? (
              <aside
                aria-label="Karşılaştırma uyarıları"
                className="rounded-2xl border border-warn/30 bg-warn/10 p-4"
              >
                <h3 className="font-semibold text-warn">Karşılaştırma uyarıları</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-warn">
                  {result.warnings.map((warning) => (
                    <li key={warning}>{formatWarning(warning)}</li>
                  ))}
                </ul>
              </aside>
            ) : null}

            <div className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel">
              <ComparisonSummaryCards
                baselineLabel={result.baseline_label}
                comparisonLabel={result.comparison_label}
                baseline={result.baseline_summary}
                comparison={result.comparison_summary}
                durationMs={result.duration_ms}
              />
            </div>

            {bothPeriodsEmpty ? (
              <EmptyComparisonState />
            ) : (
              <>
                <div className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel">
                  <MetricComparisonPanel
                    metrics={result.metric_comparisons}
                    baselineLabel={result.baseline_label}
                    comparisonLabel={result.comparison_label}
                  />
                </div>

                {result.insights.length > 0 ? (
                  <div className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel">
                    <ComparisonInsights insights={result.insights} />
                  </div>
                ) : null}

                <div className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel">
                  <GroupComparisonPanels
                    comparisons={result.group_comparisons}
                    baselineLabel={result.baseline_label}
                    comparisonLabel={result.comparison_label}
                  />
                </div>
              </>
            )}
          </>
        ) : null}
      </section>
    </div>
  );
}

function SubmittedComparisonScope({ request }: { request: ComparisonRequest }) {
  return (
    <section
      aria-labelledby="submitted-comparison-scope-heading"
      className="rounded-2xl border border-white/10 bg-panel/70 p-4"
    >
      <h3 id="submitted-comparison-scope-heading" className="font-semibold text-ink">
        Çalıştırılan dönem sınırları
      </h3>
      <p className="mt-1 text-xs text-inkSoft">
        Bu değerler başarılı sonucun gönderilmiş istek snapshotıdır; başlangıç dahil, bitiş
        hariçtir.
      </p>
      <dl className="mt-3 grid gap-3 text-sm md:grid-cols-2">
        <SubmittedPeriod
          label={request.baseline_label ?? "Referans dönemi"}
          start={request.baseline_filter?.start_time}
          end={request.baseline_filter?.end_time}
        />
        <SubmittedPeriod
          label={request.comparison_label ?? "Karşılaştırma dönemi"}
          start={request.comparison_filter?.start_time}
          end={request.comparison_filter?.end_time}
        />
      </dl>
    </section>
  );
}

function SubmittedPeriod({
  label,
  start,
  end
}: {
  label: string;
  start?: string | null;
  end?: string | null;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <dt className="font-medium text-ink">{label}</dt>
      <dd className="mt-1 text-xs text-inkSoft">
        {start && end ? (
          <>
            <time dateTime={start}>{formatUtcDateTime(start)}</time>
            {" – "}
            <time dateTime={end}>{formatUtcDateTime(end)}</time>
          </>
        ) : (
          "Zaman sınırı gönderilmedi"
        )}
      </dd>
    </div>
  );
}

function InitialComparisonState() {
  return (
    <div role="status" className="rounded-2xl border border-white/10 bg-panel/80 p-6 text-sm">
      <h3 className="font-display text-lg font-semibold text-ink">Karşılaştırma çalıştırılmadı</h3>
      <p className="mt-2 max-w-3xl text-inkSoft">
        Hazır dönem presetini veya kendi yerel zaman aralıklarınızı seçip “Karşılaştırmayı uygula”
        düğmesini kullanın. İlk açılışta aynı snapshot kendisiyle otomatik karşılaştırılmaz.
      </p>
    </div>
  );
}

function EmptyComparisonState() {
  return (
    <div role="status" className="rounded-2xl border border-white/10 bg-panel/90 p-6 text-center">
      <h3 className="font-display text-lg font-semibold">Her iki dönem de boş</h3>
      <p className="mx-auto mt-2 max-w-2xl text-sm text-inkSoft">
        Dönemleri store event zamanlarına göre yeniden seçin veya Ingest ekranından parse edilen
        eventleri geçici store'a ekleyin.
      </p>
      <Link
        to="/analysis"
        className="mt-4 inline-flex rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Ingest ekranına git
      </Link>
    </div>
  );
}

function ComparisonErrorState({
  error,
  pending,
  onRetry
}: {
  error: Error;
  pending: boolean;
  onRetry: () => void;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const guidance =
    apiError?.status === 429
      ? "Analiz kapasitesi dolu. Kısa bir süre sonra aynı isteği tekrar deneyin."
      : apiError?.status === 413
        ? "Snapshot yapılandırılmış sınırı aşıyor. Dönem kapsamını daraltın."
        : apiError?.code === "ANALYSIS_INSUFFICIENT_DATA"
          ? "Dönem aralıklarını genişletin veya store'a daha fazla event ekleyin."
          : "Dönemleri ve seçili metrikleri kontrol edip tekrar deneyin.";

  return (
    <div role="alert" className="rounded-2xl border border-err/40 bg-err/10 p-5">
      <h3 className="font-semibold text-err">Karşılaştırma tamamlanamadı</h3>
      <p className="mt-1 text-sm text-ink">{error.message}</p>
      <p className="mt-2 text-sm text-inkSoft">{guidance}</p>
      {apiError?.code || apiError?.requestId ? (
        <p className="mt-3 font-mono text-xs text-inkSoft">
          {apiError.code ? `Kod: ${apiError.code}` : null}
          {apiError.code && apiError.requestId ? " · " : null}
          {apiError.requestId ? `Request ID: ${apiError.requestId}` : null}
        </p>
      ) : null}
      <button
        type="button"
        disabled={pending}
        className="mt-4 rounded-xl border border-err/40 bg-err/10 px-4 py-2 text-sm font-semibold text-err transition hover:bg-err/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-err disabled:opacity-60"
        onClick={onRetry}
      >
        {pending ? "Yeniden deneniyor…" : "Tekrar dene"}
      </button>
    </div>
  );
}

function formatWarning(warning: string): string {
  const known: Record<string, string> = {
    "baseline dataset contains no matching events": "Referans dönemde eşleşen event yok.",
    "comparison dataset contains no matching events": "Karşılaştırma döneminde eşleşen event yok.",
    "baseline throughput is undefined for a zero time span":
      "Referans dönemin zaman aralığı sıfır olduğu için throughput hesaplanamadı.",
    "comparison throughput is undefined for a zero time span":
      "Karşılaştırma döneminin zaman aralığı sıfır olduğu için throughput hesaplanamadı.",
    LOW_SAMPLE_SIZE: "Bazı metriklerde güvenilir eşik değerlendirmesi için örnek sayısı yetersiz."
  };
  return known[warning] ?? warning;
}

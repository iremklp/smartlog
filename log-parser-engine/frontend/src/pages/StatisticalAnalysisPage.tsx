import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { AnalysisRequestForm } from "../features/analysis/AnalysisRequestForm";
import { AnalysisSummaryCards } from "../features/analysis/AnalysisSummaryCards";
import { AnalysisTimelineChart } from "../features/analysis/AnalysisTimelineChart";
import { AnalyticsTabs } from "../features/analysis/AnalyticsTabs";
import { DistributionPanels } from "../features/analysis/DistributionPanels";
import {
  DEFAULT_ANALYSIS_REQUEST_STATE,
  buildAnalysisRequest,
  type AnalysisRequestState
} from "../features/analysis/request-state";
import { ApiError } from "../lib/api/client";
import { analyzeEvents } from "../lib/api/endpoints";
import type { AnalysisRequest } from "../lib/api/types";
import { formatDate, formatNumber } from "../lib/utils/format";

export function StatisticalAnalysisPage() {
  const [execution, setExecution] = useState<{ request: AnalysisRequest; runId: number }>(() => ({
    request: buildAnalysisRequest(DEFAULT_ANALYSIS_REQUEST_STATE),
    runId: 0
  }));

  const analysisQuery = useQuery({
    queryKey: ["statistical-analysis", execution.runId, execution.request],
    queryFn: ({ signal }) => analyzeEvents(execution.request, signal),
    retry: false,
    staleTime: 0,
    refetchOnWindowFocus: false
  });

  function applyRequest(values: AnalysisRequestState): void {
    setExecution((current) => ({
      request: buildAnalysisRequest(values),
      runId: current.runId + 1
    }));
  }

  function rerunCurrentRequest(): void {
    setExecution((current) => ({ ...current, runId: current.runId + 1 }));
  }

  const result = analysisQuery.error ? undefined : analysisQuery.data;

  return (
    <div className="grid gap-4">
      <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-white/10 bg-panel/70 p-5 backdrop-blur">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-accent2">Store snapshot</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">
            Statistical Analytics
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-inkSoft">
            Event hacmini, hata oranını ve tanısal dağılımları aynı canonical event snapshotı
            üzerinde inceleyin. Sonuçlar deterministiktir; kök neden iddiası değildir.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label="process-local" tone="warn" />
          {analysisQuery.isFetching ? (
            <StatusBadge label="refreshing" tone="info" />
          ) : analysisQuery.error ? (
            <StatusBadge label="error" tone="err" />
          ) : result ? (
            <StatusBadge label="ready" tone="ok" />
          ) : null}
        </div>
      </header>

      <AnalyticsTabs />

      <Panel
        title="Analiz kapsamı"
        subtitle="Zaman filtresi başlangıç dahil, bitiş hariç olacak şekilde backend'e gönderilir."
      >
        <AnalysisRequestForm
          defaultValues={DEFAULT_ANALYSIS_REQUEST_STATE}
          pending={analysisQuery.isFetching}
          onSubmit={applyRequest}
        />
      </Panel>

      <section
        aria-live="polite"
        aria-busy={analysisQuery.isFetching}
        aria-label="İstatistiksel analiz sonucu"
        className="grid gap-4"
      >
        {analysisQuery.isPending ? (
          <div
            role="status"
            className="rounded-2xl border border-white/10 bg-panel/80 p-6 text-sm text-inkSoft"
          >
            In-memory event snapshotı analiz ediliyor…
          </div>
        ) : null}

        {analysisQuery.error ? (
          <AnalysisErrorState
            error={analysisQuery.error}
            pending={analysisQuery.isFetching}
            onRetry={rerunCurrentRequest}
          />
        ) : null}

        {result ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-panel/70 px-4 py-3 text-sm">
              <p className="text-inkSoft">
                <span className="font-medium text-ink">
                  {formatNumber(result.matched_event_count)}
                </span>{" "}
                eşleşen / {formatNumber(result.input_event_count)} taranan event ·{" "}
                {formatDate(result.generated_at)}
              </p>
              <button
                type="button"
                disabled={analysisQuery.isFetching}
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
                onClick={rerunCurrentRequest}
              >
                Snapshotı yenile
              </button>
            </div>

            {result.warnings.length > 0 ? (
              <aside
                aria-label="Analiz uyarıları"
                className="rounded-2xl border border-warn/30 bg-warn/10 p-4"
              >
                <h3 className="font-semibold text-warn">Analiz uyarıları</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-warn">
                  {result.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </aside>
            ) : null}

            <div className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel">
              <AnalysisSummaryCards
                summary={result.summary}
                generatedAt={result.generated_at}
                durationMs={result.analysis_duration_ms}
              />
            </div>

            {result.matched_event_count === 0 ? (
              <EmptyAnalysisState />
            ) : (
              <>
                <div className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel">
                  <AnalysisTimelineChart timeline={result.timeline} />
                </div>
                <div className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel">
                  <DistributionPanels distributions={result.distributions} />
                </div>
              </>
            )}
          </>
        ) : null}
      </section>
    </div>
  );
}

function AnalysisErrorState({
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
      ? "Analiz kapasitesi dolu. Kısa bir süre sonra tekrar deneyin."
      : apiError?.status === 413
        ? "Snapshot veya istek yapılandırılmış sınırı aşıyor. Kapsamı daraltın."
        : "Filtreleri kontrol edip tekrar deneyin.";

  return (
    <div role="alert" className="rounded-2xl border border-err/40 bg-err/10 p-5">
      <h3 className="font-semibold text-err">Analiz tamamlanamadı</h3>
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

function EmptyAnalysisState() {
  return (
    <div role="status" className="rounded-2xl border border-white/10 bg-panel/90 p-6 text-center">
      <h3 className="font-display text-lg font-semibold">Bu kapsamda event bulunamadı</h3>
      <p className="mx-auto mt-2 max-w-2xl text-sm text-inkSoft">
        Zaman filtresini genişletin veya Ingest ekranından parse edilen eventleri geçici store'a
        ekleyin. Store, uygulama veya pod yeniden başladığında temizlenir.
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

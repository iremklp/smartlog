import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { ApiError } from "../lib/api/client";
import { analyzeEvents } from "../lib/api/endpoints";
import type { AnalysisResponse, AnalysisSummary } from "../lib/api/types";
import { StatisticalAnalysisPage } from "./StatisticalAnalysisPage";

vi.mock("../lib/api/endpoints", () => ({
  analyzeEvents: vi.fn()
}));

const analyzeEventsMock = vi.mocked(analyzeEvents);

beforeEach(() => {
  analyzeEventsMock.mockReset();
});

describe("StatisticalAnalysisPage", () => {
  it("loads the default snapshot and renders summary, timeline and distribution semantics", async () => {
    const user = userEvent.setup();
    analyzeEventsMock.mockResolvedValue(analysisFixture());

    renderPage();

    const errorRateCard = (await screen.findByText("Hata + kritik oranı")).parentElement;
    expect(errorRateCard).toHaveTextContent("%20");
    expect(screen.getByText("2 event")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Event hareketi" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Severity" })).toBeInTheDocument();

    await user.click(screen.getByText("Erişilebilir timeline tablosu"));
    expect(
      screen.getByText(
        "Zaman bucketlarına göre event, warning, error, critical ve HTTP 5xx sayıları"
      )
    ).toBeInTheDocument();

    await user.click(screen.getByText("Severity dağılım tablosu"));
    expect(screen.getByRole("rowheader", { name: "error" })).toBeInTheDocument();
    expect(screen.getByText("Service dağılım tablosu")).toBeInTheDocument();
  });

  it("submits bounded typed filter state to the analysis endpoint", async () => {
    const user = userEvent.setup();
    analyzeEventsMock.mockResolvedValue(analysisFixture());

    renderPage();
    await waitFor(() => expect(analyzeEventsMock).toHaveBeenCalledTimes(1));

    const topN = screen.getByLabelText(/Her boyutta Top N/);
    await user.clear(topN);
    await user.type(topN, "5");
    await user.click(screen.getByRole("button", { name: "Analizi uygula" }));

    await waitFor(() => expect(analyzeEventsMock).toHaveBeenCalledTimes(2));
    expect(analyzeEventsMock.mock.calls[1]?.[0]).toMatchObject({
      top_n: 5,
      group_fields: ["severity", "service", "event_type"],
      include_samples: false
    });
    expect(analyzeEventsMock.mock.calls[1]?.[0]).not.toHaveProperty("time_bucket_seconds");
  });

  it("runs the same request again when the form is resubmitted unchanged", async () => {
    const user = userEvent.setup();
    analyzeEventsMock.mockResolvedValue(analysisFixture());

    renderPage();
    await screen.findByText("Analiz özeti");
    await user.click(screen.getByRole("button", { name: "Analizi uygula" }));

    await waitFor(() => expect(analyzeEventsMock).toHaveBeenCalledTimes(2));
    expect(analyzeEventsMock.mock.calls[1]?.[0]).toEqual(analyzeEventsMock.mock.calls[0]?.[0]);
  });

  it("renders a clear empty-store path without requiring chart output", async () => {
    analyzeEventsMock.mockResolvedValue({
      ...analysisFixture(),
      matched_event_count: 0,
      summary: emptySummary(),
      timeline: null,
      distributions: []
    });

    renderPage();

    expect(await screen.findByText("Bu kapsamda event bulunamadı")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ingest ekranına git" })).toHaveAttribute(
      "href",
      "/analysis"
    );
  });

  it("shows safe analysis error metadata and capacity guidance", async () => {
    const user = userEvent.setup();
    analyzeEventsMock
      .mockRejectedValueOnce(
        new ApiError(429, "Analysis capacity is temporarily exhausted.", undefined, {
          code: "ANALYSIS_CONCURRENCY_LIMIT_REACHED",
          requestId: "request-123",
          retryAfter: "1"
        })
      )
      .mockResolvedValueOnce(analysisFixture());

    renderPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Analiz kapasitesi dolu");
    expect(alert).toHaveTextContent("ANALYSIS_CONCURRENCY_LIMIT_REACHED");
    expect(alert).toHaveTextContent("request-123");

    await user.click(screen.getByRole("button", { name: "Tekrar dene" }));
    expect(await screen.findByText("Analiz özeti")).toBeInTheDocument();
    expect(analyzeEventsMock).toHaveBeenCalledTimes(2);
  });

  it("does not present retained data as ready when a snapshot refresh fails", async () => {
    const user = userEvent.setup();
    analyzeEventsMock
      .mockResolvedValueOnce(analysisFixture())
      .mockRejectedValueOnce(new ApiError(503, "Analysis is temporarily unavailable."));

    renderPage();
    await screen.findByText("Analiz özeti");
    await user.click(screen.getByRole("button", { name: "Snapshotı yenile" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Analiz tamamlanamadı");
    expect(screen.queryByText("Analiz özeti")).not.toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
  });
});

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <StatisticalAnalysisPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function analysisFixture(): AnalysisResponse {
  return {
    analysis_id: "73d64de4-04a2-45cb-8d6c-530f6332dd77",
    generated_at: "2026-08-03T12:00:00Z",
    input_event_count: 10,
    matched_event_count: 10,
    analysis_duration_ms: 3.25,
    summary: {
      ...emptySummary(),
      input_event_count: 10,
      matched_event_count: 10,
      info_count: 8,
      error_count: 2,
      error_or_critical_count: 2,
      error_rate: 0.2,
      unique_event_type_count: 2,
      unique_service_count: 2,
      unique_host_count: 1,
      unique_parser_count: 1,
      unique_source_type_count: 1,
      earliest_timestamp: "2026-08-03T11:55:00Z",
      latest_timestamp: "2026-08-03T12:00:00Z",
      time_span_seconds: 300,
      events_per_second: 0.033,
      events_per_minute: 2,
      events_with_duration: 10,
      events_with_http_status: 10
    },
    timeline: {
      bucket_seconds: 300,
      start: "2026-08-03T11:55:00Z",
      end: "2026-08-03T12:00:00Z",
      buckets: [
        {
          start: "2026-08-03T11:55:00Z",
          end: "2026-08-03T12:00:00Z",
          event_count: 10,
          warning_count: 0,
          error_count: 2,
          critical_count: 0,
          error_rate: 0.2,
          average_duration_ms: 42,
          p95_duration_ms: 90,
          status_5xx_count: 2
        }
      ],
      empty_bucket_count: 0,
      max_bucket_event_count: 10,
      average_bucket_event_count: 10,
      peak_bucket_start: "2026-08-03T11:55:00Z",
      warnings: []
    },
    distributions: [
      {
        field: "severity",
        total_count: 10,
        matched_value_count: 10,
        missing_count: 0,
        unique_value_count: 2,
        items: [
          {
            rank: 1,
            key: "error",
            display_value: "error",
            count: 2,
            percentage: 20,
            metric_value: null,
            metric_unit: null,
            attributes: {}
          }
        ],
        other_count: 8,
        truncated: true
      },
      {
        field: "service",
        total_count: 10,
        matched_value_count: 10,
        missing_count: 0,
        unique_value_count: 1,
        items: [
          {
            rank: 1,
            key: "checkout",
            display_value: "checkout",
            count: 10,
            percentage: 100,
            metric_value: null,
            metric_unit: null,
            attributes: {}
          }
        ],
        other_count: 0,
        truncated: false
      }
    ],
    latency: null,
    http: null,
    insights: [],
    samples: [],
    warnings: []
  };
}

function emptySummary(): AnalysisSummary {
  return {
    input_event_count: 0,
    matched_event_count: 0,
    trace_count: 0,
    debug_count: 0,
    info_count: 0,
    warning_count: 0,
    error_count: 0,
    critical_count: 0,
    unknown_count: 0,
    error_or_critical_count: 0,
    error_rate: 0,
    critical_rate: 0,
    unique_event_type_count: 0,
    unique_service_count: 0,
    unique_host_count: 0,
    unique_parser_count: 0,
    unique_source_type_count: 0,
    earliest_timestamp: null,
    latest_timestamp: null,
    time_span_seconds: null,
    events_per_second: null,
    events_per_minute: null,
    events_with_duration: 0,
    events_with_http_status: 0,
    duplicate_content_count: 0,
    out_of_order_timestamp_count: 0
  };
}

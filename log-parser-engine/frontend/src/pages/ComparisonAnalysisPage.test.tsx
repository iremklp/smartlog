import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { ApiError } from "../lib/api/client";
import { compareEvents } from "../lib/api/endpoints";
import type {
  AnalysisSummary,
  ComparisonRequest,
  ComparisonResponse,
  GroupComparison,
  MetricComparison
} from "../lib/api/types";
import { ComparisonAnalysisPage } from "./ComparisonAnalysisPage";

vi.mock("../lib/api/endpoints", () => ({
  compareEvents: vi.fn()
}));

const compareEventsMock = vi.mocked(compareEvents);

beforeEach(() => {
  compareEventsMock.mockReset();
});

describe("ComparisonAnalysisPage", () => {
  it("does not compare the store snapshot automatically on first render", () => {
    renderPage();

    expect(compareEventsMock).not.toHaveBeenCalled();
    expect(screen.getByText("Karşılaştırma çalıştırılmadı")).toBeInTheDocument();
    expect(screen.getByText("awaiting input")).toBeInTheDocument();
  });

  it("submits explicit adjacent half-open periods and bounded comparison options", async () => {
    const user = userEvent.setup();
    compareEventsMock.mockResolvedValue(comparisonFixture());
    renderPage();

    fireEvent.change(screen.getByLabelText("Referans etiketi"), {
      target: { value: "Geçen vardiya" }
    });
    fireEvent.change(screen.getByLabelText("Karşılaştırma etiketi"), {
      target: { value: "Bu vardiya" }
    });
    fireEvent.change(screen.getByLabelText("Referans başlangıcı"), {
      target: { value: "2026-08-01T08:00" }
    });
    fireEvent.change(screen.getByLabelText("Referans bitişi"), {
      target: { value: "2026-08-01T10:00" }
    });
    fireEvent.change(screen.getByLabelText("Karşılaştırma başlangıcı"), {
      target: { value: "2026-08-01T10:00" }
    });
    fireEvent.change(screen.getByLabelText("Karşılaştırma bitişi"), {
      target: { value: "2026-08-01T12:00" }
    });
    fireEvent.change(screen.getByLabelText("Boyut başına Top N"), {
      target: { value: "7" }
    });

    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));

    await waitFor(() => expect(compareEventsMock).toHaveBeenCalledTimes(1));
    expect(compareEventsMock).toHaveBeenCalledWith({
      baseline_label: "Geçen vardiya",
      comparison_label: "Bu vardiya",
      baseline_filter: {
        start_time: new Date("2026-08-01T08:00").toISOString(),
        end_time: new Date("2026-08-01T10:00").toISOString()
      },
      comparison_filter: {
        start_time: new Date("2026-08-01T10:00").toISOString(),
        end_time: new Date("2026-08-01T12:00").toISOString()
      },
      metrics: ["event_count", "error_rate", "p95_duration_ms"],
      group_by: ["service", "severity"],
      top_n: 7,
      minimum_group_count: 1,
      include_new_groups: true,
      include_disappeared_groups: true,
      normalize_by_time_span: true
    });
  });

  it("renders ratio, percentage-point and relative changes with findings and group movement", async () => {
    const user = userEvent.setup();
    compareEventsMock.mockResolvedValue(comparisonFixture());
    renderPage();

    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));

    expect(await screen.findByRole("heading", { name: "Dönem özeti" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Çalıştırılan dönem sınırları" })
    ).toBeInTheDocument();
    expect(document.querySelectorAll("time[datetime]")).toHaveLength(4);
    expect(screen.getByText("+100%")).toBeInTheDocument();
    expect(screen.getByText(/\+10 yüzde puan/)).toBeInTheDocument();
    expect(screen.getByText("Kötüleşme")).toBeInTheDocument();
    expect(screen.getByText("Değişim eşiğini aşıyor")).toBeInTheDocument();
    expect(screen.getByText("Düşük örnek · yorum güvenilmez")).toBeInTheDocument();
    expect(screen.getByText("Düşük örnek nedeniyle eşik kararı bastırıldı")).toBeInTheDocument();
    expect(screen.getAllByText("%10").length).toBeGreaterThan(0);
    expect(screen.getAllByText("%20").length).toBeGreaterThan(0);

    expect(screen.getByRole("heading", { name: "Service" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "billing" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "legacy" })).toBeInTheDocument();
    expect(screen.getByText("Yeni grup · düşük örnek")).toBeInTheDocument();
    expect(screen.getByText("Kaybolan grup · düşük örnek")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Hata oranı yükseldi" })).toBeInTheDocument();
    expect(
      screen.getByText("Hata dağılımlarını servis ve event türü bazında inceleyin.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Bazı metriklerde güvenilir eşik değerlendirmesi için örnek sayısı yetersiz."
      )
    ).toBeInTheDocument();
  });

  it("renders the dedicated empty state when both periods contain no events", async () => {
    const user = userEvent.setup();
    compareEventsMock.mockResolvedValue(emptyComparisonFixture());
    renderPage();

    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));

    expect(await screen.findByText("Her iki dönem de boş")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ingest ekranına git" })).toHaveAttribute(
      "href",
      "/analysis"
    );
    expect(screen.queryByRole("heading", { name: "Metrik değişimleri" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Grup hareketleri" })).not.toBeInTheDocument();
  });

  it("shows safe 429 metadata and retries the exact same request", async () => {
    const user = userEvent.setup();
    compareEventsMock
      .mockRejectedValueOnce(
        new ApiError(429, "Analysis capacity is temporarily exhausted.", undefined, {
          code: "ANALYSIS_CONCURRENCY_LIMIT_REACHED",
          requestId: "comparison-request-123",
          retryAfter: "2"
        })
      )
      .mockResolvedValueOnce(comparisonFixture());
    renderPage();

    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Analiz kapasitesi dolu");
    expect(alert).toHaveTextContent("ANALYSIS_CONCURRENCY_LIMIT_REACHED");
    expect(alert).toHaveTextContent("comparison-request-123");
    const firstRequest = compareEventsMock.mock.calls[0]?.[0] as ComparisonRequest;

    await user.click(screen.getByRole("button", { name: "Tekrar dene" }));

    expect(await screen.findByRole("heading", { name: "Dönem özeti" })).toBeInTheDocument();
    expect(compareEventsMock).toHaveBeenCalledTimes(2);
    expect(compareEventsMock.mock.calls[1]?.[0]).toEqual(firstRequest);
  });

  it("does not keep a stale ready result visible when refreshing the snapshot fails", async () => {
    const user = userEvent.setup();
    compareEventsMock
      .mockResolvedValueOnce(comparisonFixture())
      .mockRejectedValueOnce(new ApiError(503, "Comparison service is temporarily unavailable."));
    renderPage();

    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));
    await screen.findByRole("heading", { name: "Dönem özeti" });
    await user.click(screen.getByRole("button", { name: "Aynı isteği yeniden çalıştır" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Karşılaştırma tamamlanamadı");
    expect(screen.queryByRole("heading", { name: "Dönem özeti" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Metrik değişimleri" })).not.toBeInTheDocument();
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
      <MemoryRouter initialEntries={["/analytics/compare"]}>
        <ComparisonAnalysisPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function comparisonFixture(): ComparisonResponse {
  return {
    baseline_label: "Önceki 1 saat",
    comparison_label: "Son 1 saat",
    baseline_summary: summaryFixture({
      matched_event_count: 100,
      error_or_critical_count: 10,
      error_count: 10,
      error_rate: 0.1,
      events_per_minute: 1.67,
      earliest_timestamp: "2026-08-03T10:00:00Z",
      latest_timestamp: "2026-08-03T10:59:59Z"
    }),
    comparison_summary: summaryFixture({
      input_event_count: 120,
      matched_event_count: 120,
      error_or_critical_count: 24,
      error_count: 24,
      error_rate: 0.2,
      events_per_minute: 2,
      earliest_timestamp: "2026-08-03T11:00:00Z",
      latest_timestamp: "2026-08-03T11:59:59Z"
    }),
    baseline_event_count: 100,
    comparison_event_count: 120,
    duration_ms: 4.25,
    metric_comparisons: [
      metricComparison({
        metric: "error_rate",
        unit: "ratio",
        baseline_value: 0.1,
        comparison_value: 0.2,
        absolute_change: 0.1,
        percent_change: 100,
        direction: "increase",
        significant: true,
        interpretation: "degraded"
      }),
      metricComparison({
        metric: "p95_duration_ms",
        unit: "ms",
        baseline_value: 100,
        comparison_value: 125,
        absolute_change: 25,
        percent_change: 25,
        direction: "increase",
        significant: false,
        interpretation: "degraded",
        notes: ["LOW_SAMPLE_SIZE"]
      })
    ],
    group_comparisons: [
      groupComparison({
        key: "billing",
        baseline_count: 0,
        comparison_count: 24,
        absolute_change: 24,
        percent_change: null,
        baseline_percentage: 0,
        comparison_percentage: 20,
        percentage_point_change: 20,
        new_group: true,
        significant: false,
        metric_comparisons: [
          metricComparison({
            metric: "event_count",
            unit: "count",
            baseline_value: 0,
            comparison_value: 24,
            absolute_change: 24,
            percent_change: null,
            direction: "new",
            significant: false,
            interpretation: "unknown",
            notes: ["LOW_SAMPLE_SIZE"]
          })
        ]
      }),
      groupComparison({
        key: "legacy",
        baseline_count: 15,
        comparison_count: 0,
        absolute_change: -15,
        percent_change: -100,
        baseline_percentage: 15,
        comparison_percentage: 0,
        percentage_point_change: -15,
        disappeared_group: true,
        significant: false,
        metric_comparisons: [
          metricComparison({
            metric: "event_count",
            unit: "count",
            baseline_value: 15,
            comparison_value: 0,
            absolute_change: -15,
            percent_change: -100,
            direction: "removed",
            significant: false,
            interpretation: "unknown",
            notes: ["LOW_SAMPLE_SIZE"]
          })
        ]
      })
    ],
    insights: [
      {
        code: "ERROR_SPIKE",
        level: "warning",
        title: "Error rate increased",
        message: "Hata oranı referans döneme göre yükseldi.",
        metric: "error_rate",
        current_value: 0.2,
        reference_value: 0.1,
        unit: "ratio",
        evidence: { absolute_change: 0.1 },
        recommendations: ["Hata dağılımlarını servis ve event türü bazında inceleyin."]
      }
    ],
    warnings: ["LOW_SAMPLE_SIZE"]
  };
}

function emptyComparisonFixture(): ComparisonResponse {
  return {
    ...comparisonFixture(),
    baseline_summary: emptySummary(),
    comparison_summary: emptySummary(),
    baseline_event_count: 0,
    comparison_event_count: 0,
    metric_comparisons: [],
    group_comparisons: [],
    insights: [],
    warnings: [
      "baseline dataset contains no matching events",
      "comparison dataset contains no matching events"
    ]
  };
}

function summaryFixture(overrides: Partial<AnalysisSummary> = {}): AnalysisSummary {
  return {
    ...emptySummary(),
    input_event_count: 100,
    matched_event_count: 100,
    info_count: 90,
    error_count: 10,
    error_or_critical_count: 10,
    error_rate: 0.1,
    unique_event_type_count: 3,
    unique_service_count: 2,
    unique_host_count: 2,
    unique_parser_count: 1,
    unique_source_type_count: 1,
    time_span_seconds: 3_600,
    events_per_second: 0.028,
    events_per_minute: 1.67,
    events_with_duration: 100,
    events_with_http_status: 100,
    ...overrides
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

function metricComparison(overrides: Partial<MetricComparison>): MetricComparison {
  return {
    metric: "event_count",
    unit: "count",
    baseline_value: 100,
    comparison_value: 120,
    absolute_change: 20,
    percent_change: 20,
    direction: "increase",
    significant: true,
    interpretation: "neutral",
    notes: [],
    ...overrides
  };
}

function groupComparison(overrides: Partial<GroupComparison>): GroupComparison {
  return {
    group_field: "service",
    key: "checkout",
    baseline_count: 100,
    comparison_count: 120,
    absolute_change: 20,
    percent_change: 20,
    baseline_percentage: 100,
    comparison_percentage: 100,
    percentage_point_change: 0,
    new_group: false,
    disappeared_group: false,
    significant: false,
    metric_comparisons: [],
    attributes: {},
    ...overrides
  };
}

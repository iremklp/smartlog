import { render, screen } from "@testing-library/react";

import type { HTTPAnalysis, LatencyAnalysis } from "../../lib/api/types";
import { HttpAnalysisPanel } from "./HttpAnalysisPanel";
import { LatencyAnalysisPanel } from "./LatencyAnalysisPanel";

describe("deep analysis panels accessibility", () => {
  it("renders latency table captions and empty rows when datasets are empty", () => {
    render(<LatencyAnalysisPanel latency={latencyFixture()} />);

    expect(screen.getByText("Latency percentile dağılımı (milisaniye)")).toBeInTheDocument();
    expect(screen.getByText("En yavaş event örnekleri (milisaniye)")).toBeInTheDocument();
    expect(screen.getByText("Percentile verisi bulunamadı.")).toBeInTheDocument();
    expect(screen.getByText("Yavaş event örneği bulunamadı.")).toBeInTheDocument();
  });

  it("renders http table captions and empty rows when datasets are empty", () => {
    render(<HttpAnalysisPanel http={httpFixture()} />);

    expect(screen.getByText("HTTP method dağılımı")).toBeInTheDocument();
    expect(screen.getByText("Endpoint hata oranı sıralaması")).toBeInTheDocument();
    expect(screen.getByText("Method dağılımı bulunamadı.")).toBeInTheDocument();
    expect(screen.getByText("Endpoint hata oranı verisi bulunamadı.")).toBeInTheDocument();
  });
});

function latencyFixture(): LatencyAnalysis {
  return {
    detected_field: "duration_ms",
    unit: "ms",
    total_events: 10,
    sample_count: 0,
    missing_count: 10,
    invalid_count: 0,
    minimum_ms: null,
    maximum_ms: null,
    mean_ms: null,
    median_ms: null,
    standard_deviation_ms: null,
    percentiles: {
      sample_count: 0,
      minimum: null,
      maximum: null,
      mean: null,
      median: null,
      standard_deviation: null,
      percentile_values: {},
      missing_count: 10,
      invalid_count: 0,
      percentile_sample_count: null,
      percentiles_approximated: false
    },
    slowest_events: [],
    latency_buckets: [],
    per_service: [],
    per_event_type: [],
    per_endpoint: [],
    warnings: []
  };
}

function httpFixture(): HTTPAnalysis {
  return {
    http_event_count: 0,
    events_with_status: 0,
    events_with_method: 0,
    events_with_path: 0,
    informational_count: 0,
    success_count: 0,
    redirect_count: 0,
    non_error_count: 0,
    client_error_count: 0,
    server_error_count: 0,
    unknown_status_count: 0,
    success_rate: 0,
    non_error_rate: 0,
    client_error_rate: 0,
    server_error_rate: 0,
    total_error_rate: 0,
    status_class_distribution: distributionFixture("status_class"),
    status_code_distribution: distributionFixture("status_code"),
    method_distribution: distributionFixture("method"),
    endpoint_distribution: distributionFixture("endpoint"),
    slowest_endpoints: [],
    highest_error_endpoints: [],
    status_by_method: [],
    status_by_service: [],
    timeline: null,
    warnings: []
  };
}

function distributionFixture(field: string) {
  return {
    field,
    total_count: 0,
    matched_value_count: 0,
    missing_count: 0,
    unique_value_count: 0,
    items: [],
    other_count: 0,
    truncated: false
  };
}

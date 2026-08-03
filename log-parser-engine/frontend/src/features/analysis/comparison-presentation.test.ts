import type { ComparisonGroupField, GroupComparison, MetricComparison } from "../../lib/api/types";
import {
  formatAbsoluteChange,
  formatMetricValue,
  formatPercentChange,
  groupAndBoundComparisons
} from "./comparison-presentation";

describe("comparison presentation", () => {
  it("keeps ratio, percentage-point and relative-change units distinct", () => {
    const metric = metricComparison({
      unit: "ratio",
      baseline_value: 0.1,
      comparison_value: 0.15,
      absolute_change: 0.05,
      percent_change: 50
    });

    expect(formatMetricValue(metric.baseline_value, metric.unit)).toContain("%10");
    expect(formatAbsoluteChange(metric)).toContain("5 yüzde puan");
    expect(formatPercentChange(metric.percent_change)).toBe("+50%");
  });

  it("does not invent a percentage when the backend marks it undefined", () => {
    expect(formatPercentChange(null)).toBe("Hesaplanamadı");
  });

  it("groups rows in API order and bounds each field independently", () => {
    const comparisons = [
      ...Array.from({ length: 22 }, (_, index) => groupComparison("service", `service-${index}`)),
      groupComparison("severity", "error"),
      groupComparison("service", "late-service")
    ];

    const sections = groupAndBoundComparisons(comparisons, 20);

    expect(sections.map((section) => section.field)).toEqual(["service", "severity"]);
    expect(sections[0]).toMatchObject({ originalCount: 23, hiddenCount: 3 });
    expect(sections[0]?.items).toHaveLength(20);
    expect(sections[0]?.items[0]?.key).toBe("service-0");
    expect(sections[1]?.items[0]?.key).toBe("error");
  });
});

function metricComparison(overrides: Partial<MetricComparison> = {}): MetricComparison {
  return {
    metric: "error_rate",
    unit: "ratio",
    baseline_value: 0,
    comparison_value: 0,
    absolute_change: 0,
    percent_change: 0,
    direction: "unchanged",
    significant: false,
    interpretation: "neutral",
    notes: [],
    ...overrides
  };
}

function groupComparison(field: ComparisonGroupField, key: string): GroupComparison {
  return {
    group_field: field,
    key,
    baseline_count: 1,
    comparison_count: 2,
    absolute_change: 1,
    percent_change: 100,
    baseline_percentage: 10,
    comparison_percentage: 20,
    percentage_point_change: 10,
    new_group: false,
    disappeared_group: false,
    significant: true,
    metric_comparisons: [],
    attributes: {}
  };
}

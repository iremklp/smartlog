import type { DistributionResult, TimelineBucket } from "../../lib/api/types";
import {
  MAX_DISTRIBUTION_ITEMS,
  MAX_TIMELINE_POINTS,
  boundDistributionItems,
  boundTimelineBuckets,
  formatUtcDateTime
} from "./presentation";

describe("analysis presentation bounds", () => {
  it("keeps a timeline at the display limit unchanged", () => {
    const buckets = Array.from({ length: MAX_TIMELINE_POINTS }, (_, index) =>
      timelineBucket(index)
    );

    const result = boundTimelineBuckets(buckets);

    expect(result.coarsened).toBe(false);
    expect(result.buckets).toBe(buckets);
    expect(result.maxBucketsPerPoint).toBe(1);
  });

  it("coarsens large timelines while preserving ordered count totals", () => {
    const buckets = Array.from({ length: 241 }, (_, index) => timelineBucket(index));

    const result = boundTimelineBuckets(buckets);

    expect(result.coarsened).toBe(true);
    expect(result.originalCount).toBe(241);
    expect(result.buckets.length).toBeLessThanOrEqual(MAX_TIMELINE_POINTS);
    expect(result.buckets[0]?.start).toBe(buckets[0]?.start);
    expect(result.buckets[result.buckets.length - 1]?.end).toBe(buckets[buckets.length - 1]?.end);
    expect(total(result.buckets, "event_count")).toBe(total(buckets, "event_count"));
    expect(total(result.buckets, "warning_count")).toBe(total(buckets, "warning_count"));
    expect(total(result.buckets, "error_count")).toBe(total(buckets, "error_count"));
    expect(total(result.buckets, "critical_count")).toBe(total(buckets, "critical_count"));
    expect(total(result.buckets, "status_5xx_count")).toBe(total(buckets, "status_5xx_count"));
    expect(result.maxBucketsPerPoint).toBe(3);
    expect(result.buckets.some((bucket) => bucket.p95_duration_ms === null)).toBe(true);
  });

  it("caps defensive distribution rendering at twenty items", () => {
    const distribution: DistributionResult = {
      field: "service",
      total_count: 25,
      matched_value_count: 25,
      missing_count: 0,
      unique_value_count: 25,
      items: Array.from({ length: 25 }, (_, index) => ({
        rank: index + 1,
        key: `service-${index + 1}`,
        display_value: `Service ${index + 1}`,
        count: 1,
        percentage: 4,
        metric_value: null,
        metric_unit: null,
        attributes: {}
      })),
      other_count: 0,
      truncated: false
    };

    expect(boundDistributionItems(distribution)).toMatchObject({
      items: expect.any(Array),
      originalItemCount: 25,
      hiddenItemCount: 5,
      hiddenEventCount: 5,
      clientTruncated: true
    });
    expect(boundDistributionItems(distribution).items).toHaveLength(MAX_DISTRIBUTION_ITEMS);
  });

  it("formats offset timestamps explicitly in UTC", () => {
    const label = formatUtcDateTime("2026-07-25T22:30:00-07:00");

    expect(label).toContain("05:30");
    expect(label).toContain("UTC");
  });
});

function timelineBucket(index: number): TimelineBucket {
  const start = new Date(Date.UTC(2026, 6, 25, 0, index));
  const end = new Date(start.getTime() + 60_000);
  return {
    start: start.toISOString(),
    end: end.toISOString(),
    event_count: 2,
    warning_count: 1,
    error_count: index % 2,
    critical_count: index % 5 === 0 ? 1 : 0,
    error_rate: ((index % 2) + (index % 5 === 0 ? 1 : 0)) / 2,
    average_duration_ms: 12,
    p95_duration_ms: 18,
    status_5xx_count: index % 3 === 0 ? 1 : 0
  };
}

function total(
  buckets: TimelineBucket[],
  field: "event_count" | "warning_count" | "error_count" | "critical_count" | "status_5xx_count"
): number {
  return buckets.reduce((sum, bucket) => sum + bucket[field], 0);
}

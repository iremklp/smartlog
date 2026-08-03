import type { DistributionResult, RankedItem, TimelineBucket } from "../../lib/api/types";

export const MAX_TIMELINE_POINTS = 120;
export const MAX_DISTRIBUTION_ITEMS = 20;

export interface BoundedTimeline {
  buckets: TimelineBucket[];
  originalCount: number;
  coarsened: boolean;
  maxBucketsPerPoint: number;
}

export interface BoundedDistribution {
  items: RankedItem[];
  originalItemCount: number;
  hiddenItemCount: number;
  hiddenEventCount: number;
  clientTruncated: boolean;
}

export function boundTimelineBuckets(
  buckets: TimelineBucket[],
  maxPoints = MAX_TIMELINE_POINTS
): BoundedTimeline {
  if (!Number.isInteger(maxPoints) || maxPoints < 1) {
    throw new Error("maxPoints must be a positive integer");
  }
  if (buckets.length <= maxPoints) {
    return {
      buckets,
      originalCount: buckets.length,
      coarsened: false,
      maxBucketsPerPoint: 1
    };
  }

  const groupSize = Math.ceil(buckets.length / maxPoints);
  const coarsenedBuckets: TimelineBucket[] = [];
  for (let index = 0; index < buckets.length; index += groupSize) {
    const group = buckets.slice(index, index + groupSize);
    coarsenedBuckets.push(mergeTimelineGroup(group));
  }
  return {
    buckets: coarsenedBuckets,
    originalCount: buckets.length,
    coarsened: true,
    maxBucketsPerPoint: groupSize
  };
}

export function boundDistributionItems(
  distribution: DistributionResult,
  maxItems = MAX_DISTRIBUTION_ITEMS
): BoundedDistribution {
  if (!Number.isInteger(maxItems) || maxItems < 1) {
    throw new Error("maxItems must be a positive integer");
  }
  const items = distribution.items.slice(0, maxItems);
  const hiddenItems = distribution.items.slice(maxItems);
  return {
    items,
    originalItemCount: distribution.items.length,
    hiddenItemCount: hiddenItems.length,
    hiddenEventCount: hiddenItems.reduce((total, item) => total + item.count, 0),
    clientTruncated: hiddenItems.length > 0
  };
}

export function formatUtcDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${new Intl.DateTimeFormat("tr-TR", {
    timeZone: "UTC",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23"
  }).format(date)} UTC`;
}

function mergeTimelineGroup(group: TimelineBucket[]): TimelineBucket {
  const first = group[0];
  const last = group[group.length - 1];
  if (!first || !last) {
    throw new Error("timeline group must not be empty");
  }
  if (group.length === 1) {
    return first;
  }

  const eventCount = sum(group, "event_count");
  const errorCount = sum(group, "error_count");
  const criticalCount = sum(group, "critical_count");
  return {
    start: first.start,
    end: last.end,
    event_count: eventCount,
    warning_count: sum(group, "warning_count"),
    error_count: errorCount,
    critical_count: criticalCount,
    error_rate: eventCount === 0 ? 0 : (errorCount + criticalCount) / eventCount,
    average_duration_ms: null,
    p95_duration_ms: null,
    status_5xx_count: sum(group, "status_5xx_count")
  };
}

function sum(
  buckets: TimelineBucket[],
  field: "event_count" | "warning_count" | "error_count" | "critical_count" | "status_5xx_count"
): number {
  return buckets.reduce((total, bucket) => total + bucket[field], 0);
}

import { useQuery } from "@tanstack/react-query";

import { Panel } from "../components/Panel";
import { getStoreStatistics } from "../lib/api/endpoints";
import { formatBytes, formatDate, formatNumber } from "../lib/utils/format";

export function StorePage() {
  const statsQuery = useQuery({
    queryKey: ["store-statistics"],
    queryFn: ({ signal }) => getStoreStatistics(signal)
  });

  const stats = statsQuery.data;

  return (
    <Panel title="Store Overview" subtitle="In-memory event store runtime metrics">
      {statsQuery.isPending ? <p className="text-sm text-inkSoft">Loading...</p> : null}
      {statsQuery.error ? <p className="text-sm text-err">{statsQuery.error.message}</p> : null}
      {stats ? (
        <dl className="grid gap-3 sm:grid-cols-2">
          <Metric label="Event count" value={formatNumber(stats.event_count)} />
          <Metric label="Estimated memory" value={formatBytes(stats.estimated_memory_bytes)} />
          <Metric label="Write count" value={formatNumber(stats.write_count)} />
          <Metric label="Query count" value={formatNumber(stats.query_count)} />
          <Metric label="Evicted" value={formatNumber(stats.evicted_count)} />
          <Metric label="Index enabled" value={String(stats.index_enabled)} />
          <Metric label="Last write" value={formatDate(stats.last_write_at)} />
          <Metric label="Last query" value={formatDate(stats.last_query_at)} />
        </dl>
      ) : null}
      <p className="mt-4 text-xs text-warn">
        Note: current backend store is transient memory-backed. Restarting API clears data.
      </p>
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <dt className="text-xs uppercase tracking-wide text-inkSoft">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-ink">{value}</dd>
    </div>
  );
}

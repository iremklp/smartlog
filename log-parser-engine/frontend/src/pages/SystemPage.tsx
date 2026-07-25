import { useQuery } from "@tanstack/react-query";

import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { getHealth, getRuntimeStatistics } from "../lib/api/endpoints";
import { formatDate, formatNumber } from "../lib/utils/format";

export function SystemPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 10000
  });

  const runtimeQuery = useQuery({
    queryKey: ["runtime-statistics"],
    queryFn: ({ signal }) => getRuntimeStatistics(signal),
    refetchInterval: 10000
  });

  const health = healthQuery.data;
  const runtime = runtimeQuery.data;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel
        title="Service Health"
        subtitle="Live health probe"
        rightSlot={
          health ? (
            <StatusBadge
              label={health.status}
              tone={health.status === "healthy" ? "ok" : "warn"}
            />
          ) : undefined
        }
      >
        {health ? (
          <dl className="grid gap-2 text-sm">
            <Field label="Created at" value={formatDate(health.created_at)} />
            <Field label="Checked at" value={formatDate(health.checked_at)} />
            <Field label="Uptime (ms)" value={formatNumber(Math.round(health.uptime_ms))} />
            <Field label="Parser count" value={formatNumber(health.parser_count)} />
            <Field label="Enabled parsers" value={formatNumber(health.enabled_parser_count)} />
            <Field label="Store events" value={formatNumber(health.store_event_count)} />
          </dl>
        ) : (
          <p className="text-sm text-inkSoft">No health data yet.</p>
        )}
      </Panel>

      <Panel title="Runtime Snapshot" subtitle="Container and store statistics">
        {runtime ? (
          <dl className="grid gap-2 text-sm">
            <Field label="Observed at" value={formatDate(runtime.observed_at)} />
            <Field label="Store writes" value={formatNumber(runtime.store_statistics.write_count)} />
            <Field label="Store queries" value={formatNumber(runtime.store_statistics.query_count)} />
            <Field label="Estimated memory" value={formatNumber(runtime.store_statistics.estimated_memory_bytes)} />
            <Field label="Startup warnings" value={String(runtime.startup_warnings.length)} />
          </dl>
        ) : (
          <p className="text-sm text-inkSoft">No runtime data yet.</p>
        )}
      </Panel>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
      <dt className="text-inkSoft">{label}</dt>
      <dd className="font-semibold text-ink">{value}</dd>
    </div>
  );
}

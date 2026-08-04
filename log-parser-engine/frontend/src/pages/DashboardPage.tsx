import { useQuery } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { Panel } from "../components/Panel";
import { aggregateEvents, queryEvents } from "../lib/api/endpoints";
import type { EventFilter, LogSeverity } from "../lib/api/types";
import { formatNumber } from "../lib/utils/format";

export function DashboardPage() {
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [severity, setSeverity] = useState<LogSeverity | "">("");
  const [appliedFilter, setAppliedFilter] = useState(() => ({
    startTime: "",
    endTime: "",
    severity: "" as LogSeverity | ""
  }));

  const baseFilter = useMemo<EventFilter | undefined>(() => {
    const filter: EventFilter = {
      ...(appliedFilter.startTime
        ? { start_time: new Date(appliedFilter.startTime).toISOString() }
        : {}),
      ...(appliedFilter.endTime ? { end_time: new Date(appliedFilter.endTime).toISOString() } : {}),
      ...(appliedFilter.severity ? { severities: [appliedFilter.severity] } : {})
    };
    return Object.keys(filter).length > 0 ? filter : undefined;
  }, [appliedFilter.endTime, appliedFilter.severity, appliedFilter.startTime]);

  const severityAgg = useQuery({
    queryKey: ["dashboard", "severity", baseFilter],
    queryFn: ({ signal }) =>
      aggregateEvents(
        { group_by: "severity", metric: "count", limit: 10 },
        {
          filter: baseFilter,
          include_events: false,
          include_total: false,
          offset: 0,
          limit: 1
        },
        signal
      )
  });

  const parserFacet = useQuery({
    queryKey: ["dashboard", "parser-facets", baseFilter],
    queryFn: ({ signal }) =>
      queryEvents(
        {
          filter: baseFilter,
          include_events: false,
          include_total: true,
          include_facets: true,
          facet_fields: ["parser_name"],
          limit: 1,
          offset: 0
        },
        signal
      )
  });

  const severityData =
    severityAgg.data?.buckets?.map((bucket) => ({
      group: String(bucket.group_value),
      count: bucket.event_count
    })) ?? [];

  const facetData = parserFacet.data?.facets?.parser_name ?? [];

  function handleFilterSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setAppliedFilter({ startTime, endTime, severity });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Global filtre" subtitle="Dashboard ve drill-down için ortak filtre">
        <form className="grid gap-3 md:grid-cols-4" onSubmit={handleFilterSubmit}>
          <div className="grid gap-1">
            <label htmlFor="dashboard-start-time" className="text-xs text-inkSoft">
              Başlangıç (lokal)
            </label>
            <input
              id="dashboard-start-time"
              type="datetime-local"
              value={startTime}
              onChange={(event) => setStartTime(event.target.value)}
              className="rounded-xl border-white/20 bg-black/20"
            />
          </div>
          <div className="grid gap-1">
            <label htmlFor="dashboard-end-time" className="text-xs text-inkSoft">
              Bitiş (lokal)
            </label>
            <input
              id="dashboard-end-time"
              type="datetime-local"
              value={endTime}
              onChange={(event) => setEndTime(event.target.value)}
              className="rounded-xl border-white/20 bg-black/20"
            />
          </div>
          <div className="grid gap-1">
            <label htmlFor="dashboard-severity" className="text-xs text-inkSoft">
              Severity
            </label>
            <select
              id="dashboard-severity"
              value={severity}
              onChange={(event) => setSeverity(event.target.value as LogSeverity | "")}
              className="rounded-xl border-white/20 bg-black/20"
            >
              <option value="">all</option>
              <option value="debug">debug</option>
              <option value="info">info</option>
              <option value="warning">warning</option>
              <option value="error">error</option>
              <option value="critical">critical</option>
            </select>
          </div>
          <div className="flex items-end justify-start">
            <button
              type="submit"
              className="rounded-xl bg-accent px-4 py-2 font-semibold text-black"
            >
              Filtreyi uygula
            </button>
          </div>
        </form>
      </Panel>

      <Panel title="Severity Distribution" subtitle="Aggregate endpoint based">
        {severityAgg.isPending ? <p className="text-sm text-inkSoft">Loading chart...</p> : null}
        {severityAgg.error ? <p className="text-sm text-err">{severityAgg.error.message}</p> : null}
        <div className="h-80 w-full">
          <ResponsiveContainer>
            <BarChart data={severityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.2)" />
              <XAxis dataKey="group" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#21d4fd" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <ul className="mt-3 grid gap-2 text-sm">
          {severityData.map((row) => (
            <li key={row.group}>
              <Link
                to={buildEventsDrilldownUrl({
                  severity: row.group,
                  startTime: appliedFilter.startTime,
                  endTime: appliedFilter.endTime
                })}
                className="inline-flex items-center gap-2 text-accent hover:underline"
              >
                <span>{row.group}</span>
                <span className="text-inkSoft">{formatNumber(row.count)} event</span>
              </Link>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel title="Parser Facets" subtitle="Facet counts from query endpoint">
        <ul className="grid gap-2">
          {facetData.length ? (
            facetData.map((item) => (
              <li
                key={item.value}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm"
              >
                <Link
                  to={buildEventsDrilldownUrl({
                    parserName: item.value,
                    severity: appliedFilter.severity,
                    startTime: appliedFilter.startTime,
                    endTime: appliedFilter.endTime
                  })}
                  className="font-medium text-accent hover:underline"
                >
                  {item.value || "(empty)"}
                </Link>
                <span className="ml-2 text-inkSoft">{formatNumber(item.count)}</span>
              </li>
            ))
          ) : (
            <li className="text-sm text-inkSoft">No facet data available.</li>
          )}
        </ul>
        <Link
          to={buildEventsDrilldownUrl({
            severity: appliedFilter.severity,
            startTime: appliedFilter.startTime,
            endTime: appliedFilter.endTime
          })}
          className="mt-3 inline-flex text-sm text-accent hover:underline"
        >
          Event Explorer'da filtreli sonuçları aç
        </Link>
      </Panel>
    </div>
  );
}

function buildEventsDrilldownUrl(input: {
  severity?: string;
  parserName?: string;
  startTime?: string;
  endTime?: string;
}): string {
  const params = new URLSearchParams();
  if (input.severity) {
    params.set("severity", input.severity);
  }
  if (input.parserName) {
    params.set("parser", input.parserName);
  }
  if (input.startTime) {
    params.set("start", input.startTime);
  }
  if (input.endTime) {
    params.set("end", input.endTime);
  }
  const query = params.toString();
  return query ? `/events?${query}` : "/events";
}

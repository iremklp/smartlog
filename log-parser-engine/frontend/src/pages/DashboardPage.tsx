import { useQuery } from "@tanstack/react-query";
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
import { formatNumber } from "../lib/utils/format";

export function DashboardPage() {
  const severityAgg = useQuery({
    queryKey: ["dashboard", "severity"],
    queryFn: ({ signal }) =>
      aggregateEvents({ group_by: "severity", metric: "count", limit: 10 }, undefined, signal)
  });

  const parserFacet = useQuery({
    queryKey: ["dashboard", "parser-facets"],
    queryFn: ({ signal }) =>
      queryEvents(
        {
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

  return (
    <div className="grid gap-4 lg:grid-cols-2">
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
      </Panel>

      <Panel title="Parser Facets" subtitle="Facet counts from query endpoint">
        <ul className="grid gap-2">
          {facetData.length ? (
            facetData.map((item) => (
              <li
                key={item.value}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm"
              >
                <span className="font-medium text-ink">{item.value || "(empty)"}</span>
                <span className="ml-2 text-inkSoft">{formatNumber(item.count)}</span>
              </li>
            ))
          ) : (
            <li className="text-sm text-inkSoft">No facet data available.</li>
          )}
        </ul>
      </Panel>
    </div>
  );
}

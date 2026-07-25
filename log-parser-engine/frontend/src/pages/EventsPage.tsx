import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { EventsTable } from "../components/EventsTable";
import { Panel } from "../components/Panel";
import { queryEvents } from "../lib/api/endpoints";
import type { EventQuery, EventQueryResult } from "../lib/api/types";
import { formatNumber } from "../lib/utils/format";

export function EventsPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [severity, setSeverity] = useState("");

  const mutation = useMutation({
    mutationFn: async (query: EventQuery) => queryEvents(query),
    onMutate: () => undefined
  });

  const queryInput = useMemo<EventQuery>(
    () => ({
      filter: {
        message_contains: message || undefined,
        severities: severity ? [severity] : undefined
      },
      sort: [{ field: "timestamp", direction: "desc" }],
      limit,
      offset,
      include_events: true,
      include_total: true
    }),
    [message, severity, limit, offset]
  );

  const result: EventQueryResult | undefined = mutation.data;

  return (
    <div className="grid gap-4">
      <Panel title="Event Explorer" subtitle="Server-side query, pagination and filters">
        <form
          className="grid gap-3 md:grid-cols-[1fr_150px_120px_120px_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate(queryInput);
          }}
        >
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="message contains"
            className="rounded-xl border-white/20 bg-black/20"
          />
          <select
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
            className="rounded-xl border-white/20 bg-black/20"
          >
            <option value="">any severity</option>
            <option value="debug">debug</option>
            <option value="info">info</option>
            <option value="warning">warning</option>
            <option value="error">error</option>
            <option value="critical">critical</option>
          </select>
          <input
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value) || 50)}
            className="rounded-xl border-white/20 bg-black/20"
          />
          <input
            type="number"
            min={0}
            value={offset}
            onChange={(event) => setOffset(Number(event.target.value) || 0)}
            className="rounded-xl border-white/20 bg-black/20"
          />
          <button type="submit" className="rounded-xl bg-accent px-4 py-2 font-semibold text-black">
            {mutation.isPending ? "Querying..." : "Run Query"}
          </button>
        </form>
      </Panel>

      <Panel
        title="Results"
        subtitle={
          result
            ? `Snapshot ${formatNumber(result.snapshot_size)} | Query ${result.query_duration_ms.toFixed(2)} ms`
            : "Run a query to load events"
        }
      >
        {mutation.error ? <p className="mb-3 text-sm text-err">{mutation.error.message}</p> : null}
        {result ? (
          <>
            <div className="mb-3 text-sm text-inkSoft">
              Total: {result.page.total ?? "n/a"} | Has next: {String(result.page.has_next)}
            </div>
            <EventsTable rows={result.events} onSelect={(id) => navigate(`/events/${id}`)} />
          </>
        ) : (
          <p className="text-sm text-inkSoft">No query result yet.</p>
        )}
      </Panel>
    </div>
  );
}

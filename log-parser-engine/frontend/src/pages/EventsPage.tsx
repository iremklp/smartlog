import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { EventsTable } from "../components/EventsTable";
import { Panel } from "../components/Panel";
import { eventPageHasMore } from "../lib/api/contracts";
import { queryEvents } from "../lib/api/endpoints";
import type { EventQuery, EventQueryResult, LogSeverity } from "../lib/api/types";
import { formatNumber } from "../lib/utils/format";

export function EventsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [message, setMessage] = useState(() => searchParams.get("message") ?? "");
  const [limit, setLimit] = useState(() => parseInteger(searchParams.get("limit"), 50));
  const [offset, setOffset] = useState(() => parseInteger(searchParams.get("offset"), 0));
  const [severity, setSeverity] = useState<LogSeverity | "">(
    () => (searchParams.get("severity") as LogSeverity | "") ?? ""
  );
  const [parserName, setParserName] = useState(() => searchParams.get("parser") ?? "");
  const [startTime, setStartTime] = useState(() => searchParams.get("start") ?? "");
  const [endTime, setEndTime] = useState(() => searchParams.get("end") ?? "");

  const mutation = useMutation({
    mutationFn: async (query: EventQuery) => queryEvents(query),
    onMutate: () => undefined
  });

  const queryInput = useMemo<EventQuery>(
    () => ({
      filter: {
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
        message_contains: message || undefined,
        severities: severity ? [severity] : undefined,
        parser_names: parserName ? [parserName] : undefined
      },
      sort: [{ field: "timestamp", direction: "desc" }],
      limit,
      offset,
      include_events: true,
      include_total: true
    }),
    [endTime, limit, message, offset, parserName, severity, startTime]
  );

  const hasPresetFilters = Boolean(
    searchParams.get("message") ||
    searchParams.get("severity") ||
    searchParams.get("parser") ||
    searchParams.get("start") ||
    searchParams.get("end") ||
    searchParams.get("offset") ||
    searchParams.get("limit")
  );

  const autoRunCompletedRef = useRef(false);

  useEffect(() => {
    if (hasPresetFilters && !autoRunCompletedRef.current) {
      autoRunCompletedRef.current = true;
      mutation.mutate(queryInput);
    }
  }, [hasPresetFilters, mutation, queryInput]);

  const result: EventQueryResult | undefined = mutation.data;

  return (
    <div className="grid gap-4">
      <Panel title="Event Explorer" subtitle="Server-side query, pagination and filters">
        <form
          className="grid gap-3 md:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault();
            setSearchParams(
              buildEventsSearchParams({
                message,
                severity,
                parserName,
                startTime,
                endTime,
                limit,
                offset
              })
            );
            mutation.mutate(queryInput);
          }}
        >
          <label className="grid gap-1 text-xs text-inkSoft" htmlFor="events-message-filter">
            Message contains
          </label>
          <input
            id="events-message-filter"
            aria-label="Message contains"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="message contains"
            className="rounded-xl border-white/20 bg-black/20"
          />

          <label className="grid gap-1 text-xs text-inkSoft" htmlFor="events-severity-filter">
            Severity
          </label>
          <select
            id="events-severity-filter"
            aria-label="Severity"
            value={severity}
            onChange={(event) => setSeverity(event.target.value as LogSeverity | "")}
            className="rounded-xl border-white/20 bg-black/20"
          >
            <option value="">any severity</option>
            <option value="debug">debug</option>
            <option value="info">info</option>
            <option value="warning">warning</option>
            <option value="error">error</option>
            <option value="critical">critical</option>
          </select>

          <label className="grid gap-1 text-xs text-inkSoft" htmlFor="events-parser-filter">
            Parser name
          </label>
          <input
            id="events-parser-filter"
            aria-label="Parser name"
            value={parserName}
            onChange={(event) => setParserName(event.target.value)}
            placeholder="parser name"
            className="rounded-xl border-white/20 bg-black/20"
          />

          <label className="grid gap-1 text-xs text-inkSoft" htmlFor="events-start-time-filter">
            Start (local)
          </label>
          <input
            id="events-start-time-filter"
            aria-label="Start"
            type="datetime-local"
            value={startTime}
            onChange={(event) => setStartTime(event.target.value)}
            className="rounded-xl border-white/20 bg-black/20"
          />

          <label className="grid gap-1 text-xs text-inkSoft" htmlFor="events-end-time-filter">
            End (local)
          </label>
          <input
            id="events-end-time-filter"
            aria-label="End"
            type="datetime-local"
            value={endTime}
            onChange={(event) => setEndTime(event.target.value)}
            className="rounded-xl border-white/20 bg-black/20"
          />

          <label className="grid gap-1 text-xs text-inkSoft" htmlFor="events-limit-filter">
            Limit
          </label>
          <input
            id="events-limit-filter"
            aria-label="Limit"
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value) || 50)}
            className="rounded-xl border-white/20 bg-black/20"
          />

          <label className="grid gap-1 text-xs text-inkSoft" htmlFor="events-offset-filter">
            Offset
          </label>
          <input
            id="events-offset-filter"
            aria-label="Offset"
            type="number"
            min={0}
            value={offset}
            onChange={(event) => setOffset(Number(event.target.value) || 0)}
            className="rounded-xl border-white/20 bg-black/20"
          />

          <div className="flex items-end">
            <button
              type="submit"
              className="rounded-xl bg-accent px-4 py-2 font-semibold text-black"
            >
              {mutation.isPending ? "Querying..." : "Run Query"}
            </button>
          </div>
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
        {mutation.isPending ? (
          <p className="mb-3 text-sm text-inkSoft">Query calisiyor...</p>
        ) : null}
        {mutation.error ? <p className="mb-3 text-sm text-err">{mutation.error.message}</p> : null}
        {result ? (
          <>
            <div className="mb-3 text-sm text-inkSoft">
              Total: {result.page.total ?? "n/a"} | Has more:{" "}
              {String(eventPageHasMore(result.page))}
            </div>
            {result.events.length > 0 ? (
              <EventsTable rows={result.events} onSelect={(id) => navigate(`/events/${id}`)} />
            ) : (
              <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-6 text-sm text-inkSoft">
                Sorgu tamamlandi ancak event bulunamadi. Analysis ekraninda Store secenegiyle veri
                yazip tekrar deneyin.
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-inkSoft">No query result yet.</p>
        )}
      </Panel>
    </div>
  );
}

function parseInteger(value: string | null, fallback: number): number {
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0, Math.trunc(parsed));
}

function buildEventsSearchParams(input: {
  message: string;
  severity: LogSeverity | "";
  parserName: string;
  startTime: string;
  endTime: string;
  limit: number;
  offset: number;
}): URLSearchParams {
  const params = new URLSearchParams();
  if (input.message) {
    params.set("message", input.message);
  }
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
  if (input.limit !== 50) {
    params.set("limit", String(input.limit));
  }
  if (input.offset > 0) {
    params.set("offset", String(input.offset));
  }
  return params;
}

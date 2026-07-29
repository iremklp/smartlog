import { useQuery } from "@tanstack/react-query";

import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { listParsers } from "../lib/api/endpoints";
import { formatDate } from "../lib/utils/format";

export function ParsersPage() {
  const parsersQuery = useQuery({
    queryKey: ["parsers"],
    queryFn: ({ signal }) => listParsers(signal)
  });

  return (
    <Panel title="Parser Registry" subtitle="Enabled parsers and metadata">
      {parsersQuery.isPending ? <p className="text-sm text-inkSoft">Loading...</p> : null}
      {parsersQuery.error ? <p className="text-sm text-err">{parsersQuery.error.message}</p> : null}
      <div className="grid gap-2">
        {(parsersQuery.data ?? []).map((parser) => (
          <article
            key={`${parser.parser_name}-${parser.parser_version}`}
            className="rounded-xl border border-white/10 bg-black/20 p-3"
          >
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-semibold text-ink">{parser.parser_name}</h3>
              <StatusBadge
                label={parser.enabled ? "enabled" : "disabled"}
                tone={parser.enabled ? "ok" : "warn"}
              />
            </div>
            <p className="text-xs text-inkSoft">Version: {parser.parser_version}</p>
            <p className="text-xs text-inkSoft">Source type: {parser.source_type}</p>
            <p className="text-xs text-inkSoft">Registered: {formatDate(parser.registered_at)}</p>
          </article>
        ))}
      </div>
    </Panel>
  );
}

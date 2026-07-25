import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { JsonView } from "../components/JsonView";
import { Panel } from "../components/Panel";
import { getEventById } from "../lib/api/endpoints";

export function EventDetailPage() {
  const { eventId = "" } = useParams();
  const eventQuery = useQuery({
    queryKey: ["event", eventId],
    queryFn: ({ signal }) => getEventById(eventId, signal),
    enabled: Boolean(eventId)
  });

  return (
    <Panel title="Event Detail" subtitle={eventId || "Unknown event id"}>
      {eventQuery.isPending ? <p className="text-sm text-inkSoft">Loading...</p> : null}
      {eventQuery.error ? <p className="text-sm text-err">{eventQuery.error.message}</p> : null}
      {eventQuery.data ? <JsonView value={eventQuery.data} /> : null}
    </Panel>
  );
}

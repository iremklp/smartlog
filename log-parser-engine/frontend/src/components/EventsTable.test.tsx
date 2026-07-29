import { fireEvent, render, screen } from "@testing-library/react";

import type { StoredEvent } from "../lib/api/types";
import { EventsTable } from "./EventsTable";

const backendStoredEvent: StoredEvent = {
  id: "evt_01",
  event: {
    schema_version: "1.0",
    event_id: "2d854e83-638b-40cb-b774-94fc1c806bde",
    timestamp: "2026-07-29T08:30:00+00:00",
    ingested_at: "2026-07-29T08:30:01+00:00",
    source_type: "application",
    severity: "error",
    event_type: "request_failed",
    message: "Checkout request failed",
    raw_message: "2026-07-29 ERROR Checkout request failed",
    service: "checkout",
    application: "storefront",
    environment: "test",
    host: "node-01",
    source: "application.log",
    trace_id: "trace-01",
    correlation_id: "correlation-01",
    user_id: null,
    client_ip: "192.0.2.10",
    server_ip: "192.0.2.20",
    http_method: "POST",
    http_path: "/checkout",
    http_status: 500,
    duration_ms: 125.5,
    attributes: {
      parser_name: "json",
      parser_version: "1.0.0"
    },
    tags: ["checkout", "http"]
  },
  inserted_at: "2026-07-29T08:30:02+00:00",
  sequence: 1,
  content_hash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  estimated_size_bytes: 512,
  source_batch_id: "batch-01",
  metadata: {}
};

describe("EventsTable", () => {
  it("renders a backend-shaped canonical event without invented fields", () => {
    const onSelect = vi.fn();

    render(<EventsTable rows={[backendStoredEvent]} onSelect={onSelect} />);

    expect(screen.getByText("evt_01")).toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
    expect(screen.getByText("json")).toBeInTheDocument();
    expect(screen.getByText("Checkout request failed")).toBeInTheDocument();

    fireEvent.click(screen.getByText("evt_01"));
    expect(onSelect).toHaveBeenCalledWith("evt_01");
  });
});

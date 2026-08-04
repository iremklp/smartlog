import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { queryEvents } from "../lib/api/endpoints";
import type { EventQueryResult } from "../lib/api/types";
import { EventsPage } from "./EventsPage";

vi.mock("../lib/api/endpoints", () => ({
  queryEvents: vi.fn()
}));

const queryEventsMock = vi.mocked(queryEvents);

beforeEach(() => {
  queryEventsMock.mockReset();
  queryEventsMock.mockResolvedValue(emptyResult());
});

describe("EventsPage", () => {
  it("auto-runs query from dashboard drill-down URL filters", async () => {
    renderPage(
      "/events?severity=error&parser=iis&start=2026-08-03T10:00&end=2026-08-03T12:00&limit=25&offset=10"
    );

    await waitFor(() => expect(queryEventsMock).toHaveBeenCalledTimes(1));

    expect(queryEventsMock.mock.calls[0]?.[0]).toMatchObject({
      filter: {
        severities: ["error"],
        parser_names: ["iis"],
        start_time: new Date("2026-08-03T10:00").toISOString(),
        end_time: new Date("2026-08-03T12:00").toISOString()
      },
      limit: 25,
      offset: 10
    });
  });

  it("prefills form fields from URL and submits updated filters", async () => {
    const user = userEvent.setup();

    renderPage("/events?severity=warning&parser=nginx");
    await waitFor(() => expect(queryEventsMock).toHaveBeenCalledTimes(1));

    expect(screen.getByLabelText("Severity")).toHaveValue("warning");
    expect(screen.getByLabelText("Parser name")).toHaveValue("nginx");

    await user.clear(screen.getByLabelText("Message contains"));
    await user.type(screen.getByLabelText("Message contains"), "timeout");
    await user.click(screen.getByRole("button", { name: "Run Query" }));

    await waitFor(() => expect(queryEventsMock).toHaveBeenCalledTimes(2));
    expect(queryEventsMock.mock.calls[1]?.[0]).toMatchObject({
      filter: {
        message_contains: "timeout",
        severities: ["warning"],
        parser_names: ["nginx"]
      }
    });
  });
});

function renderPage(initialEntry: string): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/events" element={<EventsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function emptyResult(): EventQueryResult {
  return {
    events: [],
    page: {
      offset: 0,
      limit: 50,
      returned: 0,
      total: 0
    },
    facets: {},
    aggregation: null,
    query_duration_ms: 1,
    snapshot_size: 0,
    index_used: false,
    candidate_count: 0,
    warnings: []
  };
}

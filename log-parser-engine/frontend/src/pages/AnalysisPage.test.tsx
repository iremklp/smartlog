import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import {
  addEvent,
  batchParseAndStoreText,
  batchParseText,
  getPublicConfig,
  listParsers,
  parseFile,
  parseText,
  parseWithParser
} from "../lib/api/endpoints";
import type { EventWriteResult, LogEvent, PipelineResult } from "../lib/api/types";
import { AnalysisPage } from "./AnalysisPage";

vi.mock("../lib/api/endpoints", () => ({
  addEvent: vi.fn(),
  batchParseAndStoreText: vi.fn(),
  batchParseText: vi.fn(),
  getPublicConfig: vi.fn(),
  listParsers: vi.fn(),
  parseFile: vi.fn(),
  parseText: vi.fn(),
  parseWithParser: vi.fn()
}));

const addEventMock = vi.mocked(addEvent);
const batchParseAndStoreTextMock = vi.mocked(batchParseAndStoreText);
const batchParseTextMock = vi.mocked(batchParseText);
const getPublicConfigMock = vi.mocked(getPublicConfig);
const listParsersMock = vi.mocked(listParsers);
const parseFileMock = vi.mocked(parseFile);
const parseTextMock = vi.mocked(parseText);
const parseWithParserMock = vi.mocked(parseWithParser);

beforeEach(() => {
  addEventMock.mockReset();
  batchParseAndStoreTextMock.mockReset();
  batchParseTextMock.mockReset();
  getPublicConfigMock.mockReset();
  listParsersMock.mockReset();
  parseFileMock.mockReset();
  parseTextMock.mockReset();
  parseWithParserMock.mockReset();

  getPublicConfigMock.mockResolvedValue({
    app: { name: "log-parser-engine", version: "0.1.0", environment: "development" },
    limits: {
      max_upload_bytes: 50 * 1024 * 1024,
      max_text_characters: 1024 * 1024,
      max_page_size: 200,
      max_response_items: 1000
    },
    capabilities: {
      can_clear_store: true,
      can_delete_events: true,
      includes_raw_message_in_event_detail: true,
      includes_runtime_metrics: true,
      supports_file_upload: true,
      requires_authentication: false,
      uses_persistent_storage: false
    }
  });

  listParsersMock.mockResolvedValue([
    {
      parser_name: "json_log",
      parser_version: "1.0.0",
      source_type: "json",
      enabled: true,
      registered_at: "2026-08-04T00:00:00Z",
      registration_order: 1,
      metadata: {
        name: "json_log",
        display_name: "JSON parser",
        version: "1.0.0",
        source_type: "json",
        description: null,
        author: null,
        homepage: null,
        supported_extensions: [".json", ".jsonl"],
        supported_content_types: ["application/json", "text/plain"],
        priority: 90,
        enabled_by_default: true,
        supports_multiline: true,
        supports_batch: false,
        thread_safe: true,
        experimental: false,
        tags: ["json"]
      },
      origin: "manual",
      notes: null
    }
  ]);
});

describe("AnalysisPage store fallback", () => {
  it("stores via json_log fallback when auto detection parse fails but JSON parse succeeds", async () => {
    const user = userEvent.setup();
    parseTextMock.mockResolvedValue(pipelineFailureNoParser());
    parseWithParserMock.mockResolvedValue({ status: "success", events: [logEvent()], errors: [] });
    addEventMock.mockResolvedValue(writeResultFixture());

    renderPage();

    fireEvent.change(screen.getByPlaceholderText("Ornek log satiri"), {
      target: { value: '{"message":"hello"}' }
    });
    await user.click(screen.getByRole("checkbox", { name: "Store" }));
    await user.click(screen.getByRole("button", { name: "Run Analysis" }));

    await waitFor(() => expect(parseTextMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(parseWithParserMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(addEventMock).toHaveBeenCalledTimes(1));

    expect(parseWithParserMock).toHaveBeenCalledWith("json_log", {
      raw_log: '{"message":"hello"}'
    });
    expect(screen.getByText(/Auto fallback parser/)).toBeInTheDocument();
  });

  it("shows store-skipped guidance when parse fails and fallback cannot produce event", async () => {
    const user = userEvent.setup();
    parseTextMock.mockResolvedValue(pipelineFailureNoParser());
    parseWithParserMock.mockResolvedValue({ status: "failed", events: [], errors: [] });

    renderPage();

    fireEvent.change(screen.getByPlaceholderText("Ornek log satiri"), {
      target: { value: '{"message":"hello"}' }
    });
    await user.click(screen.getByRole("checkbox", { name: "Store" }));
    await user.click(screen.getByRole("button", { name: "Run Analysis" }));

    await waitFor(() => expect(parseTextMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(parseWithParserMock).toHaveBeenCalledTimes(1));

    expect(addEventMock).not.toHaveBeenCalled();
    expect(
      screen.getByText("Store seçiliydi ancak canonical event üretilemediği için kayıt yapılmadı.")
    ).toBeInTheDocument();
    expect(screen.getByText(/No parser matched the input\./)).toBeInTheDocument();
  });
});

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AnalysisPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function pipelineFailureNoParser(): PipelineResult {
  return {
    success: false,
    event: null,
    parse_result: null,
    normalization_result: null,
    selection: null,
    errors: [
      {
        message: "No parser matched the input.",
        status: "failed",
        error_type: "internal_error",
        details: { stage: "parser_selection", error_type: "detection_failed" }
      }
    ],
    warnings: [],
    stages: [
      {
        stage: "parser_selection",
        success: false,
        skipped: false,
        duration_ms: 0,
        message: "No parser matched the input.",
        error_type: "detection_failed",
        metadata: {}
      }
    ],
    duration_ms: 1,
    parser_name: null,
    parser_version: null,
    source_type: null,
    ambiguous: false,
    normalized: false
  };
}

function logEvent(): LogEvent {
  return {
    schema_version: "1.0",
    event_id: "evt-1",
    timestamp: "2026-08-04T09:15:21Z",
    ingested_at: "2026-08-04T09:15:22Z",
    source_type: "json",
    severity: "info",
    event_type: "test",
    message: "hello",
    raw_message: '{"message":"hello"}',
    service: "checkout",
    application: null,
    environment: null,
    host: null,
    source: null,
    trace_id: null,
    correlation_id: null,
    user_id: null,
    client_ip: null,
    server_ip: null,
    http_method: null,
    http_path: null,
    http_status: null,
    duration_ms: null,
    attributes: {},
    tags: []
  };
}

function writeResultFixture(): EventWriteResult {
  return {
    status: "inserted",
    stored_event: {
      id: "evt-1",
      event: logEvent(),
      inserted_at: "2026-08-04T09:15:22Z",
      sequence: 1,
      content_hash: "hash",
      estimated_size_bytes: 256,
      source_batch_id: null,
      metadata: {}
    },
    evicted_event_ids: []
  };
}

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { JsonView } from "../components/JsonView";
import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
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
import type { LogEvent, PipelineResult } from "../lib/api/types";

const textSchema = z.object({
  rawLog: z.string().min(1, "Log satiri bos olamaz"),
  parserName: z.string().optional(),
  storeResult: z.boolean().default(false),
  batchMode: z.boolean().default(false)
});

type TextFormValues = z.infer<typeof textSchema>;

export function AnalysisPage() {
  const [activeTab, setActiveTab] = useState<"text" | "file">("text");
  const [output, setOutput] = useState<unknown>(null);
  const configQuery = useQuery({
    queryKey: ["public-config"],
    queryFn: ({ signal }) => getPublicConfig(signal)
  });
  const supportsFileUpload = configQuery.data?.capabilities.supports_file_upload ?? true;
  const maxUploadBytes = configQuery.data?.limits.max_upload_bytes ?? 50 * 1024 * 1024;

  const parsersQuery = useQuery({
    queryKey: ["parsers"],
    queryFn: ({ signal }) => listParsers(signal)
  });
  const parserCount = (parsersQuery.data ?? []).length;

  const textForm = useForm<TextFormValues>({
    resolver: zodResolver(textSchema),
    defaultValues: {
      rawLog: "",
      parserName: "",
      storeResult: false,
      batchMode: false
    }
  });

  const textMutation = useMutation({
    mutationFn: async (values: TextFormValues) => {
      const parserName = values.parserName?.trim();
      if (values.storeResult && parserCount === 0) {
        throw new Error("Store secenegi icin parser gerekli. Su an parser registry bos.");
      }
      if (values.batchMode) {
        if (values.storeResult) {
          return batchParseAndStoreText({ text: values.rawLog });
        }
        return batchParseText({ text: values.rawLog });
      }
      if (parserName) {
        const result = await parseWithParser(parserName, { raw_log: values.rawLog });
        if (values.storeResult) {
          const event = result.events?.[0];
          if (!event) {
            throw new Error("Parser event uretmedi, bu nedenle store yazilamadi.");
          }
          const writeResult = await addEvent(event);
          return {
            result,
            write_result: writeResult
          };
        }
        return result;
      }
      if (values.storeResult) {
        // First parse without storing so parse failures surface as structured output
        // instead of a generic canonical-event store error.
        const pipelineResult = await parseText({ raw_log: values.rawLog });
        if (!pipelineResult.success || !pipelineResult.event) {
          const fallbackEvent = await tryJsonStoreFallback(values.rawLog);
          if (fallbackEvent) {
            const writeResult = await addEvent(fallbackEvent);
            return {
              result: pipelineResult,
              write_result: writeResult,
              store_skipped: false,
              store_fallback_parser: "json_log"
            };
          }
          return {
            result: pipelineResult,
            write_result: null,
            store_skipped: true,
            store_fallback_parser: null
          };
        }

        const writeResult = await addEvent(pipelineResult.event);
        return {
          result: pipelineResult,
          write_result: writeResult,
          store_skipped: false
        };
      }
      return parseText({ raw_log: values.rawLog });
    },
    onSuccess: (data) => setOutput(data)
  });

  const fileMutation = useMutation({
    mutationFn: async (payload: {
      file: File;
      sourceName?: string;
      parserName?: string;
      storeResult: boolean;
      batchMode: boolean;
    }) => {
      return parseFile(payload.file, {
        sourceName: payload.sourceName,
        parserName: payload.parserName,
        storeResult: payload.storeResult,
        batchMode: payload.batchMode
      });
    },
    onSuccess: (data) => setOutput(data)
  });

  const textErrorMessage = textMutation.error ? formatErrorMessage(textMutation.error) : null;
  const fileErrorMessage = fileMutation.error ? formatErrorMessage(fileMutation.error) : null;
  const showStoreParseHint =
    textForm.watch("storeResult") &&
    (isCanonicalStoreFailure(textErrorMessage) || isNoParserMatchedFailure(output));

  return (
    <div className="grid gap-4 lg:grid-cols-[1.05fr_1fr]">
      <Panel
        title="Log Analysis"
        subtitle="Text veya dosya kaynagi uzerinden parse ve opsiyonel store islemi"
        rightSlot={
          <div className="flex gap-2">
            <button
              className={`rounded-full px-3 py-1 text-sm ${activeTab === "text" ? "bg-accent text-black" : "bg-white/10 text-inkSoft"}`}
              onClick={() => setActiveTab("text")}
            >
              Text
            </button>
            <button
              className={`rounded-full px-3 py-1 text-sm ${activeTab === "file" ? "bg-accent text-black" : "bg-white/10 text-inkSoft"}`}
              disabled={!supportsFileUpload}
              onClick={() => setActiveTab("file")}
            >
              File
            </button>
          </div>
        }
      >
        {activeTab === "text" ? (
          <form
            className="grid gap-3"
            onSubmit={textForm.handleSubmit((values) => textMutation.mutate(values))}
          >
            {parsersQuery.isSuccess && parserCount === 0 ? (
              <p className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">
                Hic parser bulunamadi. Parse islemi sonuc vermeyebilir; once parser registry
                yukleyin.
              </p>
            ) : null}
            <textarea
              rows={8}
              placeholder="Ornek log satiri"
              className="w-full rounded-xl border-white/20 bg-black/20 text-sm"
              {...textForm.register("rawLog")}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <select
                className="rounded-xl border-white/20 bg-black/20"
                {...textForm.register("parserName")}
              >
                <option value="">Auto parser detection</option>
                {(parsersQuery.data ?? []).map((parser) => (
                  <option
                    key={`${parser.parser_name}-${parser.parser_version}`}
                    value={parser.parser_name}
                  >
                    {parser.parser_name}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <label className="inline-flex items-center gap-2 text-sm">
                  <input
                    className="ui-checkbox"
                    type="checkbox"
                    {...textForm.register("storeResult")}
                  />{" "}
                  Store
                </label>
                <label className="inline-flex items-center gap-2 text-sm">
                  <input
                    className="ui-checkbox"
                    type="checkbox"
                    {...textForm.register("batchMode")}
                  />{" "}
                  Batch
                </label>
              </div>
            </div>
            {textForm.formState.errors.rawLog ? (
              <p className="text-sm text-err">{textForm.formState.errors.rawLog.message}</p>
            ) : null}
            <button
              type="submit"
              disabled={textMutation.isPending}
              className="rounded-xl bg-accent px-4 py-2 font-semibold text-black disabled:opacity-60"
            >
              {textMutation.isPending ? "Parsing..." : "Run Analysis"}
            </button>
          </form>
        ) : (
          <FileParseForm
            parsers={parsersQuery.data ?? []}
            pending={fileMutation.isPending}
            maxUploadBytes={maxUploadBytes}
            supportsFileUpload={supportsFileUpload}
            onSubmit={(payload) => fileMutation.mutate(payload)}
          />
        )}
      </Panel>

      <Panel title="Execution Output" subtitle="API cevabi ve parse durumu">
        <div className="mb-3 flex gap-2">
          {textMutation.isSuccess || fileMutation.isSuccess ? (
            <StatusBadge label="completed" tone="ok" />
          ) : null}
          {textMutation.isPending || fileMutation.isPending ? (
            <StatusBadge label="running" tone="warn" />
          ) : null}
          {textMutation.isError || fileMutation.isError ? (
            <StatusBadge label="error" tone="err" />
          ) : null}
        </div>
        {textMutation.error ? <p className="mb-3 text-sm text-err">{textErrorMessage}</p> : null}
        {fileMutation.error ? <p className="mb-3 text-sm text-err">{fileErrorMessage}</p> : null}
        {showStoreParseHint ? (
          <div className="mb-3 rounded-xl border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
            <p className="font-semibold">Store için parser eşleşmesi gerekli.</p>
            <ul className="mt-1 list-disc space-y-1 pl-4">
              <li>Tek satır JSON gönderin (kod bloğu işaretleri eklemeyin).</li>
              <li>Çok satırlı JSON/JSONL için Batch seçeneğini açın.</li>
              <li>Auto detection yerine parser olarak json_log seçip tekrar deneyin.</li>
            </ul>
          </div>
        ) : null}
        {isStoreSkippedResult(output) ? (
          <p className="mb-3 text-xs text-warn">
            Store seçiliydi ancak canonical event üretilemediği için kayıt yapılmadı.
          </p>
        ) : null}
        {isStoreFallbackResult(output) ? (
          <p className="mb-3 text-xs text-info">
            Auto fallback parser `json_log` ile store edildi.
          </p>
        ) : null}
        {output ? (
          <JsonView value={output} />
        ) : (
          <p className="text-sm text-inkSoft">Henuz bir output yok.</p>
        )}
      </Panel>
    </div>
  );
}

function FileParseForm({
  parsers,
  pending,
  maxUploadBytes,
  supportsFileUpload,
  onSubmit
}: {
  parsers: Array<{ parser_name: string; parser_version: string }>;
  pending: boolean;
  maxUploadBytes: number;
  supportsFileUpload: boolean;
  onSubmit: (payload: {
    file: File;
    sourceName?: string;
    parserName?: string;
    storeResult: boolean;
    batchMode: boolean;
  }) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [sourceName, setSourceName] = useState("");
  const [parserName, setParserName] = useState("");
  const [storeResult, setStoreResult] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [sizeError, setSizeError] = useState<string | null>(null);
  const maxUploadMiB = maxUploadBytes / (1024 * 1024);

  if (!supportsFileUpload) {
    return (
      <div className="rounded-xl border border-warn/40 bg-warn/10 px-3 py-3 text-sm text-warn">
        Dosya upload capability devre dışı.
      </div>
    );
  }

  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!file) {
          return;
        }
        if (file.size > maxUploadBytes) {
          setSizeError(
            `Dosya boyutu limiti aşıldı. Maksimum ${maxUploadMiB.toFixed(1)} MiB.`
          );
          return;
        }
        setSizeError(null);
        onSubmit({ file, sourceName, parserName, storeResult, batchMode });
      }}
    >
      <input
        type="file"
        className="rounded-xl border-white/20 bg-black/20"
        onChange={(event) => {
          const selected = event.target.files?.[0] ?? null;
          setFile(selected);
          setSizeError(null);
        }}
      />
      <p className="text-xs text-inkSoft">Maksimum upload: {maxUploadMiB.toFixed(1)} MiB</p>
      <input
        value={sourceName}
        onChange={(event) => setSourceName(event.target.value)}
        placeholder="Optional source name"
        className="rounded-xl border-white/20 bg-black/20"
      />
      <select
        value={parserName}
        onChange={(event) => setParserName(event.target.value)}
        className="rounded-xl border-white/20 bg-black/20"
      >
        <option value="">Auto parser detection</option>
        {parsers.map((parser) => (
          <option key={`${parser.parser_name}-${parser.parser_version}`} value={parser.parser_name}>
            {parser.parser_name}
          </option>
        ))}
      </select>
      <div className="flex gap-4">
        <label className="inline-flex items-center gap-2 text-sm">
          <input
            className="ui-checkbox"
            type="checkbox"
            checked={storeResult}
            onChange={(event) => setStoreResult(event.target.checked)}
          />
          Store
        </label>
        <label className="inline-flex items-center gap-2 text-sm">
          <input
            className="ui-checkbox"
            type="checkbox"
            checked={batchMode}
            onChange={(event) => setBatchMode(event.target.checked)}
          />
          Batch
        </label>
      </div>
      {sizeError ? <p className="text-sm text-err">{sizeError}</p> : null}
      <button
        type="submit"
        disabled={pending || !file}
        className="rounded-xl bg-accent px-4 py-2 font-semibold text-black disabled:opacity-60"
      >
        {pending ? "Uploading..." : "Upload & Parse"}
      </button>
    </form>
  );
}

function formatErrorMessage(error: unknown): string {
  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    const directMessage = error.message?.trim();
    if (directMessage && directMessage !== "[object Object]") {
      return directMessage;
    }
    const nestedMessage = extractErrorMessage(error as unknown as Record<string, unknown>);
    if (nestedMessage) {
      return nestedMessage;
    }
    return "Beklenmeyen bir hata oluştu.";
  }

  if (typeof error === "object" && error !== null) {
    const extracted = extractErrorMessage(error as Record<string, unknown>);
    if (extracted) {
      return extracted;
    }
    try {
      return JSON.stringify(error);
    } catch {
      return String(error);
    }
  }

  return "Beklenmeyen bir hata oluştu.";
}

function extractErrorMessage(input: Record<string, unknown>): string | null {
  const direct = readStringValue(input.message) ?? readStringValue(input.detail);
  if (direct) {
    return direct;
  }

  const nestedError = input.error;
  if (typeof nestedError === "object" && nestedError !== null) {
    const nested = nestedError as Record<string, unknown>;
    const message = readStringValue(nested.message) ?? readStringValue(nested.detail);
    if (message) {
      return message;
    }
  }

  const detailList = input.detail;
  if (Array.isArray(detailList)) {
    const messages = detailList
      .map((item) => {
        if (typeof item !== "object" || item === null) {
          return null;
        }
        const record = item as Record<string, unknown>;
        return readStringValue(record.message) ?? readStringValue(record.msg);
      })
      .filter((value): value is string => Boolean(value));
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }

  return null;
}

function readStringValue(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function isCanonicalStoreFailure(message: string | null): boolean {
  if (!message) {
    return false;
  }
  const lowered = message.toLowerCase();
  return (
    lowered.includes("canonical event") ||
    lowered.includes("no parser matched") ||
    lowered.includes("parser did not produce")
  );
}

function isNoParserMatchedFailure(output: unknown): boolean {
  if (typeof output !== "object" || output === null) {
    return false;
  }

  const candidate = output as {
    success?: unknown;
    errors?: Array<{ message?: unknown }>;
  };

  if (candidate.success !== false || !Array.isArray(candidate.errors)) {
    return false;
  }

  return candidate.errors.some((error) => {
    const message = readStringValue(error.message);
    return Boolean(message && message.toLowerCase().includes("no parser matched"));
  });
}

function isStoreSkippedResult(output: unknown): output is {
  result: PipelineResult;
  write_result: null;
  store_skipped: true;
} {
  if (typeof output !== "object" || output === null) {
    return false;
  }

  const candidate = output as {
    store_skipped?: unknown;
    result?: unknown;
    write_result?: unknown;
  };

  return (
    candidate.store_skipped === true &&
    typeof candidate.result === "object" &&
    candidate.result !== null &&
    candidate.write_result === null
  );
}

function isStoreFallbackResult(output: unknown): output is {
  result: PipelineResult;
  write_result: unknown;
  store_skipped: false;
  store_fallback_parser: "json_log";
} {
  if (typeof output !== "object" || output === null) {
    return false;
  }
  const candidate = output as {
    store_skipped?: unknown;
    store_fallback_parser?: unknown;
    write_result?: unknown;
  };
  return (
    candidate.store_skipped === false &&
    candidate.store_fallback_parser === "json_log" &&
    candidate.write_result !== null &&
    candidate.write_result !== undefined
  );
}

async function tryJsonStoreFallback(rawLog: string): Promise<LogEvent | null> {
  const trimmed = rawLog.trim();
  if (!looksLikeJson(trimmed)) {
    return null;
  }

  try {
    const parsed = await parseWithParser("json_log", { raw_log: rawLog });
    return parsed.events?.[0] ?? null;
  } catch {
    return null;
  }
}

function looksLikeJson(value: string): boolean {
  return (
    value.startsWith("{") ||
    value.startsWith("[") ||
    value.startsWith("{\n") ||
    value.startsWith("[\n")
  );
}

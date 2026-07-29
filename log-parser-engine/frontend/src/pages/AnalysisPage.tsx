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
  listParsers,
  parseAndStoreText,
  parseFile,
  parseText,
  parseWithParser
} from "../lib/api/endpoints";

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
        return parseAndStoreText({ raw_log: values.rawLog });
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
        {textMutation.error ? (
          <p className="mb-3 text-sm text-err">{textMutation.error.message}</p>
        ) : null}
        {fileMutation.error ? (
          <p className="mb-3 text-sm text-err">{fileMutation.error.message}</p>
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
  onSubmit
}: {
  parsers: Array<{ parser_name: string; parser_version: string }>;
  pending: boolean;
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

  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!file) {
          return;
        }
        onSubmit({ file, sourceName, parserName, storeResult, batchMode });
      }}
    >
      <input
        type="file"
        className="rounded-xl border-white/20 bg-black/20"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
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

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  ANALYSIS_GROUP_OPTIONS,
  analysisRequestStateSchema,
  type AnalysisRequestState
} from "./request-state";

interface AnalysisRequestFormProps {
  defaultValues: AnalysisRequestState;
  pending: boolean;
  onSubmit: (values: AnalysisRequestState) => void;
}

export function AnalysisRequestForm({
  defaultValues,
  pending,
  onSubmit
}: AnalysisRequestFormProps) {
  const form = useForm<AnalysisRequestState>({
    resolver: zodResolver(analysisRequestStateSchema),
    defaultValues
  });

  return (
    <form className="grid gap-5" aria-busy={pending} onSubmit={form.handleSubmit(onSubmit)}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="grid gap-1.5 text-sm">
          <label className="font-medium text-ink" htmlFor="analysis-start-time">
            Başlangıç
          </label>
          <input
            id="analysis-start-time"
            type="datetime-local"
            className="rounded-xl border-white/20 bg-black/20"
            aria-describedby="analysis-start-help"
            {...form.register("startTime")}
          />
          {form.formState.errors.startTime ? (
            <span id="analysis-start-help" className="text-xs text-err">
              {form.formState.errors.startTime.message}
            </span>
          ) : (
            <span id="analysis-start-help" className="text-xs text-inkSoft">
              Dahil; boşsa en eski event.
            </span>
          )}
        </div>

        <div className="grid gap-1.5 text-sm">
          <label className="font-medium text-ink" htmlFor="analysis-end-time">
            Bitiş
          </label>
          <input
            id="analysis-end-time"
            type="datetime-local"
            className="rounded-xl border-white/20 bg-black/20"
            aria-describedby="analysis-end-help"
            {...form.register("endTime")}
          />
          {form.formState.errors.endTime ? (
            <span id="analysis-end-help" className="text-xs text-err">
              {form.formState.errors.endTime.message}
            </span>
          ) : (
            <span id="analysis-end-help" className="text-xs text-inkSoft">
              Hariç; boşsa en yeni event.
            </span>
          )}
        </div>

        <div className="grid gap-1.5 text-sm">
          <label className="font-medium text-ink" htmlFor="analysis-bucket-size">
            Zaman aralığı
          </label>
          <select
            id="analysis-bucket-size"
            className="rounded-xl border-white/20 bg-black/20"
            aria-describedby="analysis-bucket-help"
            {...form.register("timeBucketSeconds")}
          >
            <option value="auto">Otomatik</option>
            <option value={60}>1 dakika</option>
            <option value={300}>5 dakika</option>
            <option value={900}>15 dakika</option>
            <option value={3600}>1 saat</option>
            <option value={21600}>6 saat</option>
            <option value={86400}>1 gün</option>
          </select>
          {form.formState.errors.timeBucketSeconds ? (
            <span id="analysis-bucket-help" className="text-xs text-err">
              {form.formState.errors.timeBucketSeconds.message}
            </span>
          ) : (
            <span id="analysis-bucket-help" className="text-xs text-inkSoft">
              Otomatik seçim geniş dönemlerde backend sınırlarına uyum sağlar.
            </span>
          )}
        </div>

        <div className="grid gap-1.5 text-sm">
          <label className="font-medium text-ink" htmlFor="analysis-top-n">
            Her boyutta Top N
          </label>
          <input
            id="analysis-top-n"
            type="number"
            min={1}
            max={20}
            className="rounded-xl border-white/20 bg-black/20"
            aria-describedby="analysis-top-n-help"
            {...form.register("topN", { valueAsNumber: true })}
          />
          {form.formState.errors.topN ? (
            <span id="analysis-top-n-help" className="text-xs text-err">
              {form.formState.errors.topN.message}
            </span>
          ) : (
            <span id="analysis-top-n-help" className="text-xs text-inkSoft">
              Arayüz sınırı: 20.
            </span>
          )}
        </div>
      </div>

      <fieldset className="grid gap-2">
        <legend className="text-sm font-medium text-ink">Dağılım boyutları</legend>
        <p className="text-xs text-inkSoft">En az bir, en fazla dört boyut seçin.</p>
        <div className="flex flex-wrap gap-2">
          {ANALYSIS_GROUP_OPTIONS.map((option) => (
            <label
              key={option.value}
              className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-2 text-sm transition hover:border-white/25"
            >
              <input
                type="checkbox"
                value={option.value}
                className="ui-checkbox"
                {...form.register("groupFields")}
              />
              {option.label}
            </label>
          ))}
        </div>
        {form.formState.errors.groupFields ? (
          <p className="text-xs text-err">{form.formState.errors.groupFields.message}</p>
        ) : null}
      </fieldset>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-xl bg-accent px-5 py-2.5 font-semibold text-black transition hover:brightness-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Analiz çalışıyor…" : "Analizi uygula"}
        </button>
        <button
          type="button"
          disabled={pending}
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-medium text-inkSoft transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
          onClick={() => form.reset(defaultValues)}
        >
          Formu sıfırla
        </button>
        <p className="text-xs text-inkSoft">
          Yalnız bu podun geçici InMemoryEventStore snapshotı analiz edilir.
        </p>
      </div>
    </form>
  );
}

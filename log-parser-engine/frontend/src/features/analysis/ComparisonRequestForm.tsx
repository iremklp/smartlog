import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import type { UseFormRegisterReturn } from "react-hook-form";

import {
  COMPARISON_GROUP_OPTIONS,
  COMPARISON_METRIC_OPTIONS,
  COMPARISON_PERIOD_PRESET_OPTIONS,
  applyComparisonPeriodPreset,
  comparisonRequestStateSchema,
  type ComparisonPeriodPreset,
  type ComparisonRequestState
} from "./request-state";

interface ComparisonRequestFormProps {
  defaultValues: ComparisonRequestState;
  pending: boolean;
  onSubmit: (values: ComparisonRequestState) => void;
  getNow?: () => Date;
}

const currentDate = (): Date => new Date();

export function ComparisonRequestForm({
  defaultValues,
  pending,
  onSubmit,
  getNow = currentDate
}: ComparisonRequestFormProps) {
  const [preset, setPreset] = useState<ComparisonPeriodPreset>("last_hour");
  const form = useForm<ComparisonRequestState>({
    resolver: zodResolver(comparisonRequestStateSchema),
    defaultValues
  });

  const applyPreset = (): void => {
    form.reset(applyComparisonPeriodPreset(form.getValues(), preset, getNow()));
  };

  return (
    <form
      className="grid gap-6"
      aria-busy={pending}
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <fieldset disabled={pending} className="grid gap-6 border-0 p-0">
        <legend className="sr-only">Dönem karşılaştırması ayarları</legend>

        <div className="grid gap-3 rounded-2xl border border-white/10 bg-black/20 p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <div className="grid gap-1.5 text-sm">
            <label className="font-medium text-ink" htmlFor="comparison-period-preset">
              Dönem preseti
            </label>
            <select
              id="comparison-period-preset"
              className="rounded-xl border-white/20 bg-black/20"
              aria-describedby="comparison-period-preset-help"
              value={preset}
              onChange={(event) => setPreset(event.target.value as ComparisonPeriodPreset)}
            >
              {COMPARISON_PERIOD_PRESET_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <span id="comparison-period-preset-help" className="text-xs text-inkSoft">
              Bitiş zamanı şu an alınır; iki eşit ve bitişik dönem oluşturulur.
            </span>
          </div>
          <button
            type="button"
            className="rounded-xl border border-accent/40 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent transition hover:bg-accent/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            onClick={applyPreset}
          >
            Preseti uygula
          </button>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <PeriodFields
            kind="baseline"
            title="Referans dönemi"
            label="Referans etiketi"
            labelRegistration={form.register("baselineLabel")}
            labelError={form.formState.errors.baselineLabel?.message}
            startRegistration={form.register("baselineStartTime")}
            startError={form.formState.errors.baselineStartTime?.message}
            endRegistration={form.register("baselineEndTime")}
            endError={form.formState.errors.baselineEndTime?.message}
          />
          <PeriodFields
            kind="comparison"
            title="Karşılaştırma dönemi"
            label="Karşılaştırma etiketi"
            labelRegistration={form.register("comparisonLabel")}
            labelError={form.formState.errors.comparisonLabel?.message}
            startRegistration={form.register("comparisonStartTime")}
            startError={form.formState.errors.comparisonStartTime?.message}
            endRegistration={form.register("comparisonEndTime")}
            endError={form.formState.errors.comparisonEndTime?.message}
          />
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <fieldset
            className="grid gap-2 rounded-2xl border border-white/10 bg-black/10 p-4"
            aria-describedby="comparison-metrics-help comparison-metrics-error"
            aria-invalid={Boolean(form.formState.errors.metrics)}
          >
            <legend className="px-1 text-sm font-medium text-ink">Karşılaştırma metrikleri</legend>
            <p id="comparison-metrics-help" className="text-xs text-inkSoft">
              Event hacmi, kalite, gecikme ve throughput değişimlerinden en fazla 10 tanesini seçin.
            </p>
            <div className="flex flex-wrap gap-2">
              {COMPARISON_METRIC_OPTIONS.map((option) => (
                <CheckboxPill
                  key={option.value}
                  label={option.label}
                  value={option.value}
                  registration={form.register("metrics")}
                />
              ))}
            </div>
            <FieldError id="comparison-metrics-error">
              {form.formState.errors.metrics?.message}
            </FieldError>
          </fieldset>

          <fieldset
            className="grid gap-2 rounded-2xl border border-white/10 bg-black/10 p-4"
            aria-describedby="comparison-groups-help comparison-groups-error"
            aria-invalid={Boolean(form.formState.errors.groupBy)}
          >
            <legend className="px-1 text-sm font-medium text-ink">Grup boyutları</legend>
            <p id="comparison-groups-help" className="text-xs text-inkSoft">
              Yeni ve kaybolan grupları görmek için en fazla dört boyut seçin.
            </p>
            <div className="flex flex-wrap gap-2">
              {COMPARISON_GROUP_OPTIONS.map((option) => (
                <CheckboxPill
                  key={option.value}
                  label={option.label}
                  value={option.value}
                  registration={form.register("groupBy")}
                />
              ))}
            </div>
            <FieldError id="comparison-groups-error">
              {form.formState.errors.groupBy?.message}
            </FieldError>
          </fieldset>
        </div>

        <div className="grid gap-1.5 text-sm sm:max-w-xs">
          <label className="font-medium text-ink" htmlFor="comparison-top-n">
            Boyut başına Top N
          </label>
          <input
            id="comparison-top-n"
            type="number"
            min={1}
            max={20}
            className="rounded-xl border-white/20 bg-black/20"
            aria-describedby="comparison-top-n-help comparison-top-n-error"
            aria-invalid={Boolean(form.formState.errors.topN)}
            {...form.register("topN", { valueAsNumber: true })}
          />
          <span id="comparison-top-n-help" className="text-xs text-inkSoft">
            Her grup boyutu için arayüz sınırı: 20.
          </span>
          <FieldError id="comparison-top-n-error">{form.formState.errors.topN?.message}</FieldError>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            className="rounded-xl bg-accent px-5 py-2.5 font-semibold text-black transition hover:brightness-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-wait disabled:opacity-60"
          >
            {pending ? "Karşılaştırılıyor…" : "Karşılaştırmayı uygula"}
          </button>
          <button
            type="button"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-medium text-inkSoft transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
            onClick={() => {
              setPreset("last_hour");
              form.reset(applyComparisonPeriodPreset(defaultValues, "last_hour", getNow()));
            }}
          >
            Formu sıfırla
          </button>
          <p className="text-xs text-inkSoft">
            Dönemler yalnız bu podun geçici InMemoryEventStore snapshotında değerlendirilir.
          </p>
        </div>
      </fieldset>
    </form>
  );
}

interface PeriodFieldsProps {
  kind: "baseline" | "comparison";
  title: string;
  label: string;
  labelRegistration: UseFormRegisterReturn;
  labelError?: string;
  startRegistration: UseFormRegisterReturn;
  startError?: string;
  endRegistration: UseFormRegisterReturn;
  endError?: string;
}

function PeriodFields({
  kind,
  title,
  label,
  labelRegistration,
  labelError,
  startRegistration,
  startError,
  endRegistration,
  endError
}: PeriodFieldsProps) {
  const accessiblePeriodName = kind === "baseline" ? "Referans" : "Karşılaştırma";
  return (
    <fieldset className="grid gap-4 rounded-2xl border border-white/10 bg-black/10 p-4">
      <legend className="px-1 text-sm font-semibold text-ink">{title}</legend>
      <div className="grid gap-1.5 text-sm">
        <label className="font-medium text-ink" htmlFor={`${kind}-label`}>
          {label}
        </label>
        <input
          id={`${kind}-label`}
          type="text"
          maxLength={100}
          className="rounded-xl border-white/20 bg-black/20"
          aria-describedby={`${kind}-label-error`}
          aria-invalid={Boolean(labelError)}
          {...labelRegistration}
        />
        <FieldError id={`${kind}-label-error`}>{labelError}</FieldError>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-1.5 text-sm">
          <label className="font-medium text-ink" htmlFor={`${kind}-start-time`}>
            {accessiblePeriodName} başlangıcı
          </label>
          <input
            id={`${kind}-start-time`}
            type="datetime-local"
            className="rounded-xl border-white/20 bg-black/20"
            aria-describedby={`${kind}-start-help ${kind}-start-error`}
            aria-invalid={Boolean(startError)}
            {...startRegistration}
          />
          <span id={`${kind}-start-help`} className="text-xs text-inkSoft">
            Dahil; bu sınır zorunludur.
          </span>
          <FieldError id={`${kind}-start-error`}>{startError}</FieldError>
        </div>
        <div className="grid gap-1.5 text-sm">
          <label className="font-medium text-ink" htmlFor={`${kind}-end-time`}>
            {accessiblePeriodName} bitişi
          </label>
          <input
            id={`${kind}-end-time`}
            type="datetime-local"
            className="rounded-xl border-white/20 bg-black/20"
            aria-describedby={`${kind}-end-help ${kind}-end-error`}
            aria-invalid={Boolean(endError)}
            {...endRegistration}
          />
          <span id={`${kind}-end-help`} className="text-xs text-inkSoft">
            Hariç; bu sınır zorunludur.
          </span>
          <FieldError id={`${kind}-end-error`}>{endError}</FieldError>
        </div>
      </div>
    </fieldset>
  );
}

interface CheckboxPillProps {
  label: string;
  value: string;
  registration: UseFormRegisterReturn;
}

function CheckboxPill({ label, value, registration }: CheckboxPillProps) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-2 text-sm transition hover:border-white/25">
      <input type="checkbox" value={value} className="ui-checkbox" {...registration} />
      {label}
    </label>
  );
}

interface FieldErrorProps {
  id: string;
  children?: string;
}

function FieldError({ id, children }: FieldErrorProps) {
  if (!children) {
    return null;
  }
  return (
    <span id={id} className="text-xs text-err" role="alert">
      {children}
    </span>
  );
}

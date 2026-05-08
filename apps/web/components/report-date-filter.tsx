"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarDays, Check, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ReportAvailablePeriods = {
  minDate: string | null;
  maxDate: string | null;
  latestReferenceDate: string | null;
  latestReportDate: string | null;
  defaultStartDate: string | null;
  defaultEndDate: string | null;
  activeUploadBatches: {
    batchId: string;
    jobId: string;
    idChargement: string;
    originalFilename?: string | null;
    dateRapport: string | null;
    debutPeriode: string | null;
    finPeriode: string | null;
    dateReferenceDonnees: string | null;
    createdAt: string;
  }[];
};

export function ReportDateFilter({
  periods,
  selectedStartDate,
  selectedEndDate,
}: {
  periods: ReportAvailablePeriods | null;
  selectedStartDate?: string;
  selectedEndDate?: string;
}): React.ReactElement | null {
  const router = useRouter();
  const startValue = selectedStartDate ?? periods?.defaultStartDate ?? periods?.minDate ?? "";
  const endValue = selectedEndDate ?? periods?.defaultEndDate ?? periods?.maxDate ?? "";
  const dayValue = selectedStartDate === selectedEndDate ? selectedStartDate ?? "" : endValue;
  const initialMode = selectedStartDate && selectedStartDate === selectedEndDate ? "day" : "range";
  const [mode, setMode] = useState<"day" | "range">(initialMode);
  const [startDate, setStartDate] = useState(startValue);
  const [endDate, setEndDate] = useState(endValue);
  const [dayDate, setDayDate] = useState(dayValue);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMode(initialMode);
    setStartDate(startValue);
    setEndDate(endValue);
    setDayDate(dayValue);
    setError(null);
  }, [dayValue, endValue, initialMode, startValue]);

  if (!periods) return null;

  const selectedLabel =
    mode === "day"
      ? formatDate(dayDate)
      : `${formatDate(startDate)} - ${formatDate(endDate)}`;

  function apply(formData: FormData): void {
    setError(null);
    const params = new URLSearchParams();
    const selectedMode = String(formData.get("mode") ?? mode);

    if (selectedMode === "day") {
      const day = String(formData.get("dayDate") ?? "");
      if (day) {
        params.set("startDate", day);
        params.set("endDate", day);
      }
      pushFilter(params);
      return;
    }

    const submittedStartDate = String(formData.get("startDate") ?? "");
    const submittedEndDate = String(formData.get("endDate") ?? "");
    const resolvedStartDate = submittedStartDate || submittedEndDate;
    const resolvedEndDate = submittedEndDate || submittedStartDate;
    if (resolvedStartDate && resolvedEndDate && resolvedStartDate > resolvedEndDate) {
      setError("La date de début doit être antérieure ou égale à la date de fin.");
      return;
    }
    if (resolvedStartDate) params.set("startDate", resolvedStartDate);
    if (resolvedEndDate) params.set("endDate", resolvedEndDate);
    pushFilter(params);
  }

  function pushFilter(params: URLSearchParams): void {
    const query = params.toString();
    router.push(`/dashboard/macro-national${query ? `?${query}` : ""}`);
    router.refresh();
  }

  return (
    <form
      action={apply}
      className="w-full rounded-lg border border-brand-border bg-white shadow-[0_1px_2px_rgba(20,20,15,0.04)] sm:w-auto"
    >
      <input type="hidden" name="mode" value={mode} />
      <div className="flex flex-col gap-3 p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
              <CalendarDays className="h-4 w-4" aria-hidden />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.06em] text-brand-muted">
                Période
              </p>
              <p className="truncate text-sm font-medium text-brand-ink">
                {selectedLabel}
              </p>
            </div>
          </div>

          <div className="flex rounded-md bg-brand-bg p-1 text-xs">
            <ModeButton active={mode === "day"} onClick={() => setMode("day")}>
              Jour
            </ModeButton>
            <ModeButton active={mode === "range"} onClick={() => setMode("range")}>
              Période
            </ModeButton>
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-2">
          {mode === "day" ? (
            <DateField
              label="Date"
              name="dayDate"
              value={dayDate}
              min={periods.minDate ?? undefined}
              max={periods.maxDate ?? undefined}
              onChange={setDayDate}
            />
          ) : (
            <>
              <DateField
                label="Début"
                name="startDate"
                value={startDate}
                min={periods.minDate ?? undefined}
                max={periods.maxDate ?? undefined}
                onChange={setStartDate}
              />
              <DateField
                label="Fin"
                name="endDate"
                value={endDate}
                min={periods.minDate ?? undefined}
                max={periods.maxDate ?? undefined}
                onChange={setEndDate}
              />
            </>
          )}

          <Button type="submit" size="sm" className="h-9 gap-2 px-3 text-xs">
            <Check className="h-3.5 w-3.5" aria-hidden />
            Appliquer
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-9 gap-2 px-3 text-xs"
            onClick={() => {
              router.push("/dashboard/macro-national");
              router.refresh();
            }}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden />
            Dernière
          </Button>
        </div>

        {error ? (
          <p className="rounded-md bg-red-50 px-3 py-2 text-xs text-brand-danger">
            {error}
          </p>
        ) : null}
      </div>
    </form>
  );
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <button
      type="button"
      className={cn(
        "h-7 rounded px-3 font-medium transition",
        active
          ? "bg-white text-brand-ink shadow-sm"
          : "text-brand-muted hover:text-brand-ink",
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function DateField({
  label,
  name,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  name: string;
  value: string;
  min?: string;
  max?: string;
  onChange: (value: string) => void;
}): React.ReactElement {
  return (
    <label className="grid min-w-[152px] flex-1 gap-1 text-[11px] font-medium uppercase tracking-[0.05em] text-brand-muted sm:flex-none">
      {label}
      <input
        type="date"
        name={name}
        value={value}
        min={min}
        max={max}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 rounded-md border border-brand-border bg-white px-3 text-sm font-medium text-brand-ink outline-none transition focus:border-brand-primary focus:ring-2 focus:ring-emerald-100"
      />
    </label>
  );
}

function formatDate(value: string): string {
  if (!value) return "-";
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(year, month - 1, day));
}

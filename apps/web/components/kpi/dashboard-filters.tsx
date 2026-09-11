"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { KpiFilterOptions } from "@/lib/kpi-types";

const SELECT_CLASS =
  "h-9 w-full rounded-md border border-brand-border bg-white px-2.5 text-sm text-brand-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50";

function lastDayOfMonth(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  if (!y || !m) return ym;
  const day = new Date(y, m, 0).getDate();
  return `${ym}-${String(day).padStart(2, "0")}`;
}

export function DashboardFilters({
  options,
}: {
  options: KpiFilterOptions;
}): React.ReactElement {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const region = searchParams.get("region") ?? "";
  const province = searchParams.get("province") ?? "";
  const milieu = searchParams.get("milieu") ?? "";
  const startDate = searchParams.get("start_date") ?? "";
  const endDate = searchParams.get("end_date") ?? "";
  const provinces = region ? (options.provinces_by_region[region] ?? []) : [];
  const hasFilters = Boolean(region || province || milieu || startDate || endDate);

  function update(patch: Record<string, string | null>): void {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(patch)) {
      if (!value) params.delete(key);
      else params.set(key, value);
    }
    startTransition(() => {
      router.replace(params.toString() ? `${pathname}?${params.toString()}` : pathname);
    });
  }

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-brand-border bg-brand-surface p-4">
      <Field label="Période (début)">
        <input
          type="month"
          value={startDate.slice(0, 7)}
          min={options.period.min?.slice(0, 7)}
          max={options.period.max?.slice(0, 7)}
          onChange={(e) => update({ start_date: e.target.value ? `${e.target.value}-01` : null })}
          className={SELECT_CLASS}
        />
      </Field>
      <Field label="Période (fin)">
        <input
          type="month"
          value={endDate.slice(0, 7)}
          min={options.period.min?.slice(0, 7)}
          max={options.period.max?.slice(0, 7)}
          onChange={(e) =>
            update({ end_date: e.target.value ? lastDayOfMonth(e.target.value) : null })
          }
          className={SELECT_CLASS}
        />
      </Field>
      <Field label="Région">
        <select
          value={region}
          onChange={(e) => update({ region: e.target.value || null, province: null })}
          className={cn(SELECT_CLASS, "min-w-[10rem]")}
        >
          <option value="">Toutes</option>
          {options.regions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Province / Préfecture">
        <select
          value={province}
          disabled={!region}
          onChange={(e) => update({ province: e.target.value || null })}
          className={cn(SELECT_CLASS, "min-w-[10rem]")}
        >
          <option value="">Toutes</option>
          {provinces.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Milieu">
        <select
          value={milieu}
          onChange={(e) => update({ milieu: e.target.value || null })}
          className={cn(SELECT_CLASS, "min-w-[8rem]")}
        >
          <option value="">Tous</option>
          {options.milieux.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </Field>
      {hasFilters ? (
        <button
          type="button"
          onClick={() => router.replace(pathname)}
          className="h-9 shrink-0 rounded-md border border-brand-border bg-white px-3 text-xs font-medium text-brand-muted hover:bg-brand-bg"
        >
          Réinitialiser
        </button>
      ) : null}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-[11px] font-medium uppercase tracking-wide text-brand-muted">
        {label}
      </Label>
      {children}
    </div>
  );
}

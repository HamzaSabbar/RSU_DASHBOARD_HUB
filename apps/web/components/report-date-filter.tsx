"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

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
  if (!periods) return null;

  const startValue =
    selectedStartDate ?? periods.defaultStartDate ?? periods.minDate ?? "";
  const endValue = selectedEndDate ?? periods.defaultEndDate ?? periods.maxDate ?? "";

  function apply(formData: FormData): void {
    const params = new URLSearchParams();
    const startDate = String(formData.get("startDate") ?? "");
    const endDate = String(formData.get("endDate") ?? "");
    const resolvedStartDate = startDate || endDate;
    const resolvedEndDate = endDate || startDate;
    if (resolvedStartDate) params.set("startDate", resolvedStartDate);
    if (resolvedEndDate) params.set("endDate", resolvedEndDate);
    const query = params.toString();
    router.push(`/dashboard/macro-national${query ? `?${query}` : ""}`);
    router.refresh();
  }

  return (
    <form action={apply} className="flex flex-wrap items-end gap-3 rounded-md border border-brand-border bg-white px-3 py-2">
      <label className="grid gap-1 text-xs font-medium text-brand-muted">
        Début
        <input
          type="date"
          name="startDate"
          defaultValue={startValue}
          className="h-9 rounded-md border border-brand-border px-3 text-sm text-brand-dark"
        />
      </label>
      <label className="grid gap-1 text-xs font-medium text-brand-muted">
        Fin
        <input
          type="date"
          name="endDate"
          defaultValue={endValue}
          className="h-9 rounded-md border border-brand-border px-3 text-sm text-brand-dark"
        />
      </label>
      <Button type="submit" size="sm">
        Filtrer
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={() => {
          router.push("/dashboard/macro-national");
          router.refresh();
        }}
      >
        Dernière période
      </Button>
    </form>
  );
}

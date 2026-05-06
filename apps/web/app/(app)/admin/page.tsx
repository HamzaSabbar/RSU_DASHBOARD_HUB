import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { auth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

type ClearResponse = {
  status: string;
  deleted: {
    reportJobs: number;
    uploadBatches: number;
    legacyUploads: number;
    boardSnapshots: number;
    factRows: number;
  };
};

async function clearReportData(formData: FormData): Promise<void> {
  "use server";

  const confirmation = String(formData.get("confirmation") ?? "");
  if (confirmation !== "CLEAR") {
    redirect("/admin?error=confirmation");
  }

  const result = await apiFetch<ClearResponse>("/api/reports/admin/data", {
    method: "DELETE",
  });
  const deleted = result.deleted;
  redirect(
    `/admin?cleared=1&jobs=${deleted.reportJobs}&batches=${deleted.uploadBatches}&facts=${deleted.factRows}`,
  );
}

export default async function AdminPage({
  searchParams,
}: {
  searchParams?: {
    cleared?: string;
    jobs?: string;
    batches?: string;
    facts?: string;
    error?: string;
  };
}): Promise<React.ReactElement> {
  const session = await auth();
  const role = (session?.user as { role?: string } | undefined)?.role;
  if (role !== "admin") redirect("/dashboard");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-brand-dark">Administration</h1>
        <p className="mt-1 text-sm text-brand-muted">
          Clear loaded report data before testing a new workbook.
        </p>
      </div>

      {searchParams?.cleared === "1" ? (
        <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          Data cleared: {searchParams.facts ?? "0"} fact rows,{" "}
          {searchParams.batches ?? "0"} batches, {searchParams.jobs ?? "0"} jobs.
        </div>
      ) : null}

      {searchParams?.error === "confirmation" ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Type CLEAR exactly before clearing data.
        </div>
      ) : null}

      <section className="max-w-2xl rounded-md border border-brand-border bg-brand-surface p-5">
        <h2 className="text-base font-semibold text-brand-dark">Clear report data</h2>
        <p className="mt-2 text-sm leading-6 text-brand-muted">
          This removes report jobs, active upload batches, dashboard snapshots, and all
          report fact rows from the database. Users and board configuration are kept.
        </p>

        <form action={clearReportData} className="mt-5 space-y-4">
          <label className="block text-sm font-medium text-brand-dark">
            Confirmation
            <input
              name="confirmation"
              placeholder="Type CLEAR"
              className="mt-2 w-full rounded-md border border-brand-border px-3 py-2 text-sm outline-none focus:border-brand-primary"
            />
          </label>
          <Button type="submit" variant="destructive">
            Clear data
          </Button>
        </form>
      </section>
    </div>
  );
}

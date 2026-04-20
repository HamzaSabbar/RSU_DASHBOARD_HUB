import { cn } from "@/lib/utils";

export function NoData({
  className,
  label = "Données non disponibles",
}: {
  className?: string;
  label?: string;
}): React.ReactElement {
  return (
    <div
      className={cn(
        "flex min-h-[6rem] items-center justify-center rounded-md border border-dashed border-brand-border bg-slate-50 p-4 text-sm text-brand-muted",
        className,
      )}
    >
      {label}
    </div>
  );
}

import { Card } from "@/components/ui/card";
import { formatBigNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

export type KpiCardProps = {
  label: string;
  value: number | null | undefined;
  sublabel?: string;
  tone?: "neutral" | "positive" | "danger";
  className?: string;
};

const toneMap = {
  neutral: "text-brand-dark",
  positive: "text-brand-positive",
  danger: "text-brand-danger",
} as const;

export function KpiCard({
  label,
  value,
  sublabel,
  tone = "neutral",
  className,
}: KpiCardProps): React.ReactElement {
  return (
    <Card className={cn("p-5", className)}>
      <p className="text-xs font-medium uppercase tracking-wider text-brand-muted">
        {label}
      </p>
      <p
        className={cn(
          "mt-2 text-3xl font-bold tracking-tightest",
          toneMap[tone],
          value == null && "text-slate-300",
        )}
      >
        {value == null ? "--" : formatBigNumber(value)}
      </p>
      {sublabel ? (
        <p className="mt-1 text-xs text-brand-muted">{sublabel}</p>
      ) : null}
    </Card>
  );
}

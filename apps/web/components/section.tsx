import { cn } from "@/lib/utils";

export function Section({
  title,
  className,
  children,
}: {
  title: string;
  className?: string;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <section className={cn("space-y-3", className)}>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-brand-primary">
        {title}
      </h2>
      {children}
    </section>
  );
}

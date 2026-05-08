import { cn } from "@/lib/utils";

export function BrandMark({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}): React.ReactElement {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg
        aria-hidden
        className={cn("shrink-0", compact ? "h-6 w-6" : "h-8 w-8")}
        viewBox="0 0 32 32"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="32" height="32" rx="16" fill="#0a3d2a" />
        <rect x="8" y="8" width="3" height="16" fill="#fff" />
        <path
          d="M11 8 L18 8 A4 4 0 0 1 22 12 L22 14 A4 4 0 0 1 18 18 L11 18 Z"
          fill="#fff"
        />
        <path
          d="M13 11 L18 11 A1 1 0 0 1 19 12 L19 14 A1 1 0 0 1 18 15 L13 15 Z"
          fill="#0a3d2a"
        />
        <path d="M14 18 L17 18 L22 24 L19 24 Z" fill="#fff" />
        <rect x="22" y="22" width="3" height="3" rx="0.5" fill="#1f8a5b" />
      </svg>
      <span className="grid leading-none">
        <span className="text-sm font-bold text-brand-ink">
          rsu-hub<span className="text-[#1f8a5b]">.</span>
        </span>
        {!compact ? (
          <span className="mt-1 text-[10px] font-medium uppercase tracking-[0.08em] text-brand-muted">
            ANCS · prod
          </span>
        ) : null}
      </span>
    </span>
  );
}

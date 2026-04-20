import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        ready: "bg-emerald-50 text-brand-dark ring-1 ring-inset ring-emerald-200",
        empty: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200",
        danger: "bg-red-50 text-brand-danger ring-1 ring-inset ring-red-200",
      },
    },
    defaultVariants: { variant: "empty" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps): React.ReactElement {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

import type { Severity } from "@/lib/types";

const colors: Record<Severity | string, string> = {
  critical: "border-danger bg-red-50 text-danger",
  high: "border-danger bg-red-50 text-danger",
  medium: "border-amber bg-amber-50 text-amber",
  low: "border-sea bg-teal-50 text-sea"
};

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  return (
    <span
      className={`inline-flex min-w-16 items-center justify-center rounded border px-2 py-1 text-xs font-semibold uppercase ${colors[severity] ?? colors.low}`}
    >
      {severity}
    </span>
  );
}

import type { LucideIcon } from "lucide-react";

type StatCardProps = {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  tone?: "sea" | "amber" | "danger" | "ink";
};

const tones = {
  sea: "bg-teal-50 text-sea",
  amber: "bg-amber-50 text-amber",
  danger: "bg-red-50 text-danger",
  ink: "bg-zinc-100 text-ink"
};

export function StatCard({ label, value, detail, icon: Icon, tone = "sea" }: StatCardProps) {
  return (
    <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-600">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-normal text-ink">{value}</p>
        </div>
        <span className={`rounded-md p-2 ${tones[tone]}`}>
          <Icon aria-hidden="true" size={20} />
        </span>
      </div>
      <p className="mt-3 text-sm text-zinc-600">{detail}</p>
    </section>
  );
}

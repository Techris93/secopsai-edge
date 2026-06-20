import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, action }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? <p className="text-sm font-semibold uppercase tracking-normal text-sea">{eyebrow}</p> : null}
        <h1 className="mt-1 text-3xl font-semibold tracking-normal text-ink">{title}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-600">{description}</p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

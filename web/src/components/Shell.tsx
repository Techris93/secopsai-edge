"use client";

import {
  Activity,
  FileText,
  LayoutDashboard,
  Radar,
  Server,
  Settings,
  ShieldAlert,
  Wifi
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/assets", label: "Assets", icon: Server },
  { href: "/wifi", label: "Wi-Fi", icon: Wifi },
  { href: "/findings", label: "Findings", icon: ShieldAlert },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-paper">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-white px-4 py-5 lg:block">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-lg bg-sea text-white">
            <Radar size={22} aria-hidden="true" />
          </span>
          <span>
            <span className="block text-sm font-semibold uppercase tracking-normal text-sea">
              SecOpsAI
            </span>
            <span className="block text-lg font-semibold text-ink">Edge Sensor</span>
          </span>
        </Link>
        <nav className="mt-8 space-y-1">
          {navItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-teal-50 text-sea"
                    : "text-zinc-600 hover:bg-zinc-100 hover:text-ink"
                }`}
              >
                <Icon size={18} aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-5 left-4 right-4 rounded-lg border border-line bg-paper p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-ink">
            <Activity size={16} className="text-sea" aria-hidden="true" />
            Local pilot mode
          </div>
          <p className="mt-1 text-xs leading-5 text-zinc-600">
            Raw telemetry stays local. AI receives minimized findings.
          </p>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-semibold text-ink">
              <Radar size={20} className="text-sea" aria-hidden="true" />
              SecOpsAI Edge
            </Link>
          </div>
          <nav className="mt-3 flex gap-1 overflow-x-auto pb-1">
            {navItems.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex min-w-fit items-center gap-2 rounded-md px-3 py-2 text-sm ${
                    active ? "bg-teal-50 text-sea" : "text-zinc-600"
                  }`}
                >
                  <Icon size={16} aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}

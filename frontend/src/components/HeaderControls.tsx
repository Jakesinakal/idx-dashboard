"use client";

// Header nav + latest-data date. Client component only for the active-link
// highlight (usePathname). The universe filter now lives on the Screener page.
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Beranda" },
  { href: "/screener", label: "Screener" },
];

export function HeaderControls({ dateLabel }: { dateLabel: string | null }) {
  const pathname = usePathname();

  return (
    <>
      <nav className="flex items-center gap-6">
        {NAV.map((n) => {
          const active = pathname === n.href;
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`relative px-1 py-4 text-sm font-medium transition-colors ${
                active ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {n.label}
              {active ? <span className="absolute inset-x-0 -bottom-px h-px bg-violet-400" /> : null}
            </Link>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-3">
        {dateLabel ? (
          <span className="hidden font-mono text-xs text-zinc-500 sm:block">{dateLabel}</span>
        ) : null}
      </div>
    </>
  );
}

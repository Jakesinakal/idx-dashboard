"use client";

// Interactive header cluster: nav + universe filter + date + theme toggle.
// Split out of AppShell because it reads the `?u=` search param (which requires
// a <Suspense> boundary). The universe lives in the URL so the server pages can
// read it and fetch the right data.
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Check, ChevronDown, Moon } from "lucide-react";
import { UNIVERSES, type Universe } from "@/lib/types";

const NAV = [
  { href: "/", label: "Beranda" },
  { href: "/screener", label: "Screener" },
];

function navClass(active: boolean) {
  return `relative px-1 py-4 text-sm font-medium transition-colors ${
    active ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
  }`;
}

export function HeaderControls() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [uniOpen, setUniOpen] = useState(false);

  const raw = searchParams.get("u");
  const universe: Universe = raw === "JII70" || raw === "Semua" ? raw : "LQ45";

  // Carry the active universe across nav so switching pages keeps the filter.
  const withUniverse = (path: string) => (universe === "LQ45" ? path : `${path}?u=${universe}`);

  function selectUniverse(u: Universe) {
    setUniOpen(false);
    router.push(u === "LQ45" ? pathname : `${pathname}?u=${u}`);
  }

  return (
    <>
      <nav className="flex items-center gap-6">
        {NAV.map((n) => {
          const active = pathname === n.href;
          return (
            <Link key={n.href} href={withUniverse(n.href)} className={navClass(active)}>
              {n.label}
              {active ? <span className="absolute inset-x-0 -bottom-px h-px bg-violet-400" /> : null}
            </Link>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-3">
        {/* universe dropdown */}
        <div className="relative">
          <button
            onClick={() => setUniOpen((o) => !o)}
            onBlur={() => setTimeout(() => setUniOpen(false), 120)}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 font-mono text-xs text-zinc-200 transition-colors hover:border-zinc-700"
          >
            {universe}
            <ChevronDown size={14} className="text-zinc-500" />
          </button>
          {uniOpen ? (
            <div className="absolute right-0 top-full z-30 mt-1.5 w-32 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900 py-1 shadow-xl shadow-black/40">
              {UNIVERSES.map((u) => (
                <button
                  key={u}
                  onMouseDown={() => selectUniverse(u)}
                  className={`flex w-full items-center justify-between px-3 py-1.5 text-left font-mono text-xs transition-colors hover:bg-zinc-800 ${
                    universe === u ? "text-violet-300" : "text-zinc-300"
                  }`}
                >
                  {u}
                  {universe === u ? <Check size={13} /> : null}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        {/* date */}
        <span className="hidden font-mono text-xs text-zinc-500 sm:block">Selasa, 2 Jun 2026</span>

        {/* theme toggle (decorative — dark only) */}
        <button
          title="Tema gelap"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/60 text-zinc-400 transition-colors hover:text-zinc-200"
        >
          <Moon size={15} />
        </button>
      </div>
    </>
  );
}

// Static stand-in shown during prerender, before the search-param hook resolves.
export function HeaderControlsFallback() {
  return (
    <>
      <nav className="flex items-center gap-6">
        {NAV.map((n) => (
          <span key={n.href} className={navClass(false)}>
            {n.label}
          </span>
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <span className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 font-mono text-xs text-zinc-200">
          LQ45
          <ChevronDown size={14} className="text-zinc-500" />
        </span>
        <span className="hidden font-mono text-xs text-zinc-500 sm:block">Selasa, 2 Jun 2026</span>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/60 text-zinc-400">
          <Moon size={15} />
        </span>
      </div>
    </>
  );
}

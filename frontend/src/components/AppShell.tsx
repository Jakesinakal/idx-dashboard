// App shell: sticky top bar (wordmark + nav + latest-data date) and footer.
// Wraps every page so the chrome persists across navigation. The date is read
// from the warehouse so it always reflects the latest data.
import { HeaderControls } from "./HeaderControls";
import { getHeaderDate } from "@/lib/api";

export default async function AppShell({ children }: { children: React.ReactNode }) {
  const dateLabel = await getHeaderDate();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="sticky top-0 z-20 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1180px] items-center gap-6 px-6 sm:px-10">
          {/* wordmark */}
          <div className="flex items-center py-4">
            <span className="text-[15px] font-semibold tracking-tight text-zinc-50">
              Van<span className="text-zinc-400">Stocks</span>
            </span>
          </div>

          <HeaderControls dateLabel={dateLabel} />
        </div>
      </header>

      {children}

      <footer className="mx-auto max-w-[1180px] px-6 pb-10 pt-6 sm:px-10">
        <p className="border-t border-zinc-800/60 pt-5 text-xs text-zinc-600">
          VanStocks · Hanya untuk tujuan informasi, bukan rekomendasi investasi.
        </p>
      </footer>
    </div>
  );
}

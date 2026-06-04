import Screener from "@/components/Screener";
import { DataError } from "@/components/DataError";
import { getScreenerData, normalizeUniverse } from "@/lib/api";
import type { ScreenerRow } from "@/lib/types";

export default async function Page({ searchParams }: { searchParams: Promise<{ u?: string }> }) {
  const { u } = await searchParams;
  const universe = normalizeUniverse(u);

  let rows: ScreenerRow[] | null = null;
  try {
    rows = await getScreenerData(universe);
  } catch {
    rows = null;
  }
  if (!rows) return <DataError />;
  return <Screener rows={rows} universe={universe} />;
}

import Beranda from "@/components/Beranda";
import { DataError } from "@/components/DataError";
import { getBerandaData, normalizeUniverse } from "@/lib/api";
import type { BerandaData } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: Promise<{ u?: string }> }) {
  const { u } = await searchParams;
  const universe = normalizeUniverse(u);

  let data: BerandaData | null = null;
  try {
    data = await getBerandaData(universe);
  } catch {
    data = null;
  }
  if (!data) return <DataError />;
  return <Beranda data={data} />;
}

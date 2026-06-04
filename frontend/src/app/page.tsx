import Beranda from "@/components/Beranda";
import { DataError } from "@/components/DataError";
import { getBerandaData } from "@/lib/api";
import type { BerandaData } from "@/lib/types";

export default async function Page() {
  let data: BerandaData | null = null;
  try {
    data = await getBerandaData();
  } catch {
    data = null;
  }
  if (!data) return <DataError />;
  return <Beranda data={data} />;
}

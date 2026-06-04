export function DataError() {
  return (
    <div className="mx-auto max-w-[1180px] px-6 py-24 text-center sm:px-10">
      <p className="text-sm text-zinc-400">Gagal memuat data dari server.</p>
      <p className="mt-1 text-xs text-zinc-600">
        Pastikan backend API aktif (<span className="font-mono">uvicorn main:app</span>), lalu muat ulang halaman.
      </p>
    </div>
  );
}

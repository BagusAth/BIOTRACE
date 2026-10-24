export function SimulationBanner({ area }: { area: string }) {
  return (
    <div
      role="note"
      className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2.5 border border-dashed border-sim-line rounded-lg bg-sim-bg text-sim-ink text-[13px]"
    >
      <strong className="font-mono font-medium tracking-[0.06em]">SIMULASI</strong>
      <span>
        Data demo sintetis untuk {area}. Bukan hasil pemantauan nyata; sekuens buatan dibuat dengan benih acak tetap.
      </span>
    </div>
  );
}

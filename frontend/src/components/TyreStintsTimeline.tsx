import { useMemo } from "react";
import { normalizeCompound, tyreGradient } from "../theme/tyres";

type Stint = {
  compound: string;
  lap_start: number;
  lap_end: number;
  pit_lap?: number | null;
};

type DriverStints = {
  driver: string;
  total_laps: number;
  stints: Stint[];
};

export default function TyreStintsTimeline({ drivers }: { drivers: DriverStints[] }) {
  const maxLaps = useMemo(() => {
    if (!drivers?.length) return 0;
    return Math.max(...drivers.map((d) => d.total_laps || 0));
  }, [drivers]);

  if (!drivers?.length) {
    return (
      <div style={{ padding: 12, border: "1px dashed #444", borderRadius: 12 }}>
        No tyre stint data for this session.
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 10 }}>
      {drivers.map((d) => (
        <div
          key={d.driver}
          style={{
            display: "grid",
            gridTemplateColumns: "70px 1fr 60px",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div style={{ fontWeight: 700 }}>{d.driver}</div>

          <div
            style={{
              height: 18,
              borderRadius: 999,
              overflow: "hidden",
              border: "1px solid #333",
              display: "flex",
              background: "#0b0b0b",
            }}
          >
            {d.stints.map((s, idx) => {
              const widthPct =
                maxLaps > 0 ? ((s.lap_end - s.lap_start + 1) / maxLaps) * 100 : 0;

              const comp = normalizeCompound(s.compound);
              const bg = tyreGradient(comp);

              return (
                <div
                  key={`${d.driver}-${idx}`}
                  style={{
                    width: `${widthPct}%`,
                    background: bg,
                    position: "relative",
                  }}
                  title={`${comp} L${s.lap_start}-${s.lap_end}`}
                >
                  {s.pit_lap ? (
                    <div
                      style={{
                        position: "absolute",
                        right: 0,
                        top: 0,
                        bottom: 0,
                        width: 2,
                        background: "#000",
                        opacity: 0.75,
                      }}
                      title={`Pit lap ${s.pit_lap}`}
                    />
                  ) : null}
                </div>
              );
            })}
          </div>

          <div style={{ opacity: 0.85, fontSize: 13, textAlign: "right" }}>
            {d.total_laps} L
          </div>
        </div>
      ))}
    </div>
  );
}

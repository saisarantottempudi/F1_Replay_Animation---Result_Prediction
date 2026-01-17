import { TYRE_COLORS, tyreGradient } from "../theme/tyres";
import type { TyreCompound } from "../theme/tyres";

const ITEMS: { label: string; key: TyreCompound }[] = [
  { label: "Soft", key: "SOFT" },
  { label: "Medium", key: "MEDIUM" },
  { label: "Hard", key: "HARD" },
  { label: "Intermediate", key: "INTERMEDIATE" },
  { label: "Wet", key: "WET" },
];

export default function TyreLegend() {
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
      {ITEMS.map((it) => (
        <div
          key={it.key}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 10px",
            borderRadius: 999,
            border: "1px solid #333",
          }}
        >
          <span
            style={{
              width: 14,
              height: 14,
              borderRadius: 999,
              background: tyreGradient(it.key),
              border:
                it.key === "HARD"
                  ? "1px solid #999"
                  : `1px solid ${TYRE_COLORS[it.key]}`,
              display: "inline-block",
            }}
          />
          <span style={{ fontSize: 13, opacity: 0.9 }}>{it.label}</span>
        </div>
      ))}
    </div>
  );
}

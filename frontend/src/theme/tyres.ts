export type TyreCompound =
  | "SOFT"
  | "MEDIUM"
  | "HARD"
  | "INTERMEDIATE"
  | "WET"
  | "UNKNOWN";

export const TYRE_COLORS: Record<TyreCompound, string> = {
  SOFT: "#FF1E1E",         // Red
  MEDIUM: "#FF9F1A",       // Orangish
  HARD: "#FFFFFF",         // White
  INTERMEDIATE: "#39D353", // Green
  WET: "#2F81F7",          // Blue
  UNKNOWN: "#9CA3AF",      // Gray
};

export function normalizeCompound(raw: string): TyreCompound {
  const s = (raw || "").toUpperCase().trim();
  if (s.includes("SOFT")) return "SOFT";
  if (s.includes("MED")) return "MEDIUM";
  if (s.includes("HARD")) return "HARD";
  if (s.includes("INTER")) return "INTERMEDIATE";
  if (s.includes("WET")) return "WET";
  return "UNKNOWN";
}

export function tyreGradient(compound: TyreCompound): string {
  const c = TYRE_COLORS[compound] ?? TYRE_COLORS.UNKNOWN;
  // simple glossy gradient effect
  return `linear-gradient(135deg, ${c} 0%, rgba(0,0,0,0.25) 100%)`;
}

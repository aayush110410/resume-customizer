/** Film grain over the shell — the terminal's single cached noise tile, never a live filter. */
const NOISE = `<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.78" numOctaves="4" stitchTiles="stitch"/></filter><rect width="180" height="180" filter="url(#n)"/></svg>`;
const NOISE_URI = `url("data:image/svg+xml;utf8,${encodeURIComponent(NOISE)}")`;

export function Grain() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-[9] opacity-[0.09] mix-blend-overlay [transform:translateZ(0)]"
      style={{ backgroundImage: NOISE_URI, backgroundRepeat: "repeat" }}
    />
  );
}

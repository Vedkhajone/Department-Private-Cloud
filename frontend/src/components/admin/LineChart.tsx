/**
 * A small, dependency-free SVG line chart. Built by hand rather than
 * pulling in a charting library -- the brief explicitly asks for
 * something lightweight, and a handful of trend lines don't need
 * more than this.
 */
interface LineChartProps {
  points: { x: number; y: number }[];
  height?: number;
  color?: string;
  unit?: string;
  maxY?: number;
}

export function LineChart({ points, height = 120, color = "#2563eb", unit = "%", maxY = 100 }: LineChartProps) {
  const width = 600;
  const padding = 8;

  if (points.length === 0) {
    return (
      <div className="chart-empty" style={{ height }}>
        Not enough data yet
      </div>
    );
  }

  const xs = points.map((p) => p.x);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const spanX = maxX - minX || 1;

  const effectiveMaxY = maxY ?? Math.max(...points.map((p) => p.y), 1);

  const toX = (x: number) => padding + ((x - minX) / spanX) * (width - padding * 2);
  const toY = (y: number) =>
    height - padding - (Math.min(y, effectiveMaxY) / effectiveMaxY) * (height - padding * 2);

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${toX(p.x)} ${toY(p.y)}`).join(" ");
  const areaPath = `${linePath} L ${toX(points[points.length - 1].x)} ${height - padding} L ${toX(points[0].x)} ${height - padding} Z`;

  const latest = points[points.length - 1];

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="chart-svg">
        {/* Muted horizontal grid lines */}
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={padding}
            x2={width - padding}
            y1={padding + f * (height - padding * 2)}
            y2={padding + f * (height - padding * 2)}
            className="chart-grid-line"
          />
        ))}
        <path d={areaPath} fill={color} opacity={0.08} stroke="none" />
        <path d={linePath} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="chart-latest">
        {latest.y.toFixed(1)}
        {unit}
      </div>
    </div>
  );
}

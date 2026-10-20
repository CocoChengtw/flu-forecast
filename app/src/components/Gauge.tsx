import { motion, useReducedMotion } from "motion/react";
import { arc } from "d3-shape";
import { LEVELS, type Dashboard } from "../data";

// Where the needle sits, from 0 (left) to 4 (right): one unit per level,
// with the position inside a level set by how close the next level is.
export function needlePosition(d: Dashboard): number {
  const { level, value, chance } = d.now;
  const p = chance ? chance[chance.length - 1] : 1;
  const within =
    level === 0 ? value / d.lines.season
    : level === 1 ? p / 0.5
    : level === 2 ? (p - 0.5) / 0.5
    : (value - d.lines.surge) / Math.max(d.stats.medianPeak - d.lines.surge, 1);
  return level + Math.min(Math.max(within, 0.08), 0.92);
}

const W = 320;
const R = 140;
const THICK = 38;

/** Half-circle danger gauge, like a fire-danger sign: four bands and a needle. */
export function Gauge({ data }: { data: Dashboard }) {
  const reduce = useReducedMotion();
  const pos = needlePosition(data);
  const angle = -90 + (180 * pos) / 4;
  const cx = W / 2;
  const cy = R + 6;
  const seg = Math.PI / 4;
  const band = arc<{ i: number }>()
    .innerRadius(R - THICK).outerRadius(R).padAngle(0.025).cornerRadius(4)
    .startAngle(({ i }) => -Math.PI / 2 + i * seg).endAngle(({ i }) => -Math.PI / 2 + (i + 1) * seg);
  // Text runs left to right along the middle of each band
  const rm = R - THICK / 2;
  const at = (a: number) => [rm * Math.sin(a), -rm * Math.cos(a)].map((v) => v.toFixed(2)).join(" ");
  const labelPath = (i: number) => {
    const a0 = -Math.PI / 2 + i * seg + 0.02;
    const a1 = a0 + seg - 0.04;
    return `M ${at(a0)} A ${rm} ${rm} 0 0 1 ${at(a1)}`;
  };

  return (
    <svg viewBox={`0 0 ${W} ${cy + 18}`} className="w-full max-w-[340px]" role="img"
         aria-label={`Flu signal gauge pointing to ${LEVELS[data.now.level].name}`}>
      <defs>
        {LEVELS.map((_, i) => (
          <path key={i} id={`gauge-label-${i}`} d={labelPath(i)} />
        ))}
      </defs>
      <g transform={`translate(${cx},${cy})`}>
        {LEVELS.map((l, i) => (
          <motion.path key={l.name} d={band({ i }) ?? ""} fill={l.color}
                       initial={reduce ? false : { opacity: 0 }}
                       animate={{ opacity: i === data.now.level ? 1 : 0.28 }}
                       transition={{ delay: reduce ? 0 : i * 0.08, duration: 0.4 }} />
        ))}
        {LEVELS.map((l, i) => (
          <text key={l.name} fontSize={11.5} fontWeight={700} fill={i === data.now.level ? "#fff" : "var(--ink)"} dy={4}>
            <textPath href={`#gauge-label-${i}`} startOffset="50%" textAnchor="middle">{l.name}</textPath>
          </text>
        ))}
        <motion.g initial={{ rotate: reduce ? angle : -90 }} animate={{ rotate: angle }}
                  style={{ originX: 0.5, originY: 1 }}
                  transition={{ type: "spring", stiffness: 60, damping: 11, delay: reduce ? 0 : 0.3 }}>
          <path d={`M -6 0 L 0 ${-(R - THICK - 8)} L 6 0 Z`} fill="var(--ink)" />
        </motion.g>
        <circle r={11} fill="var(--ink)" />
        <circle r={4} fill="var(--surface)" />
      </g>
    </svg>
  );
}

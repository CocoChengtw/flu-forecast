import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { buildAudiences, NEXT_STEP } from "../content";
import { LEVELS, type Dashboard } from "../data";

export function Actions({ data }: { data: Dashboard }) {
  const reduce = useReducedMotion();
  const audiences = useMemo(() => buildAudiences(data), [data]);
  const [audience, setAudience] = useState(audiences[0].id);
  const current = audiences.find((a) => a.id === audience)!;
  const color = LEVELS[data.now.level].color;

  return (
    <section className="bg-sky">
      <div className="mx-auto max-w-7xl px-4 py-16 md:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Recommended now</h2>
            <p className="mt-2 text-muted">For an {LEVELS[data.now.level].name.toLowerCase()} week, with the number behind each step.</p>
          </div>
          <div role="tablist" aria-label="Who are you planning for?"
               className="flex max-w-full gap-1 overflow-x-auto rounded-full bg-surface p-1 shadow-[0_1px_2px_rgb(19_37_58/0.08)] [scrollbar-width:none]">
            {audiences.map((a) => (
              <button key={a.id} role="tab" aria-selected={a.id === audience} onClick={() => setAudience(a.id)}
                      className="relative flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap transition-colors"
                      style={{ color: a.id === audience ? "#fff" : "var(--muted)" }}>
                {a.id === audience && (
                  <motion.span layoutId="audience-pill" className="absolute inset-0 rounded-full bg-accent"
                               transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 400, damping: 34 }} />
                )}
                <a.icon size={17} weight="bold" className="relative" aria-hidden />
                <span className="relative">{a.label}</span>
              </button>
            ))}
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.ul key={audience} role="tabpanel" className="mt-8 grid gap-4 md:grid-cols-3"
                     initial={reduce ? false : "hidden"} animate="show" exit={reduce ? undefined : "hidden"}
                     variants={{ hidden: {}, show: { transition: { staggerChildren: 0.06 } } }}>
            {current.actions.map((a) => (
              <motion.li key={a.title} className="flex flex-col rounded-2xl bg-surface p-6 shadow-[0_1px_2px_rgb(19_37_58/0.06)]"
                         variants={{ hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }}
                         transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
                <div className="flex items-center gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-full" style={{ background: color, color: "#fff" }}>
                    <a.icon size={20} weight="bold" aria-hidden />
                  </span>
                  <h3 className="text-lg font-semibold leading-tight">{a.title}</h3>
                </div>
                <p className="mt-5 text-4xl font-bold tracking-tight text-accent tabular">{a.figure}</p>
                <p className="mt-1 text-sm font-medium text-muted">{a.figureLabel}</p>
                <p className="mt-4 border-t border-line pt-4 leading-snug">{a.detail}</p>
              </motion.li>
            ))}
          </motion.ul>
        </AnimatePresence>

        <p className="mt-6 text-sm text-muted">{NEXT_STEP[data.now.level]} Fixed figures (2 weeks for a flu shot, 48 hours for antivirals) are CDC guidance.</p>
      </div>
    </section>
  );
}

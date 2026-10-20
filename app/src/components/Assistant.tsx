import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { PaperPlaneRight, Sparkle, X } from "@phosphor-icons/react";
import { fmtDay, LEVELS, pct, type Dashboard } from "../data";

type Msg = { role: "user" | "assistant"; content: string; note?: string };

// Answers written from the page's own numbers, used when the AI service is not running.
function localAnswers(d: Dashboard): Record<string, string> {
  const chance = d.now.chance?.[d.now.chance.length - 1];
  const crossed = d.surges.filter((s) => s.startWeek !== null);
  const naive = d.models.find((m) => m.id === "naive")?.folds[d.mainFold];
  return {
    [`What does "${d.now.levelName}" mean?`]:
      `${LEVELS[d.now.level].name} is level ${d.now.level + 1} of 4. ` +
      (d.now.level === 1
        ? `Flu is above summer levels, but the chance of crossing the surge line in the next 4 weeks is ${chance !== undefined ? pct(chance) : "low"}. It moves to Surge watch at 50%.`
        : d.now.level === 0 ? "Flu is at summer levels."
        : d.now.level === 2 ? "There is at least a 50% chance flu crosses the surge line within 4 weeks."
        : "Flu is above the surge line now."),
    "When could the surge start?":
      `In ${crossed.length} of the last ${d.surges.length} seasons flu crossed the surge line, usually between mid-November and late January. The typical date this season would be around ${fmtDay(d.typicalCrossing, { month: "long", day: "numeric" })}.`,
    "How sure is this forecast?":
      `Today's forecast comes from the seasonal baseline, which copies last year's timing. In the 2025-26 test it was off by about ${naive?.mae[3].toFixed(1) ?? "?"} per 1,000 visits on average 4 weeks ahead. The shaded band shows the likely range.`,
    'What does "per 1,000 visits" mean?':
      `Out of every 1,000 doctor visits, about ${d.now.value.toFixed(1)} are for flu this week. The surge line is ${d.lines.surge} per 1,000. The highest peak since 2016 was about ${Math.max(...d.surges.map((s) => s.peakValue)).toFixed(0)}.`,
  };
}

export function Assistant({ data }: { data: Dashboard }) {
  const reduce = useReducedMotion();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const local = localAnswers(data);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: reduce ? "auto" : "smooth" });
  }, [msgs, busy, reduce]);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    const history = msgs.map(({ role, content }) => ({ role, content }));
    setMsgs((m) => [...m, { role: "user", content: q }]);
    setInput("");
    setBusy(true);
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, history }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error ?? "The assistant is not available.");
      setMsgs((m) => [...m, { role: "assistant", content: body.answer }]);
    } catch (err) {
      const fallback = local[q];
      setMsgs((m) => [...m, fallback
        ? { role: "assistant", content: fallback, note: "Answered from the page. The AI assistant is offline." }
        : { role: "assistant", content: (err as Error).message.includes("fetch") ? "The AI assistant is offline. Try one of the suggested questions." : (err as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button onClick={() => setOpen(true)} aria-haspopup="dialog"
                         className="fixed right-4 bottom-4 z-30 flex items-center gap-2 rounded-full bg-ink px-5 py-3 font-semibold text-bg shadow-[0_10px_30px_-10px_rgb(20_32_48/0.5)] active:scale-[0.97] md:right-8 md:bottom-8"
                         initial={reduce ? false : { y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 20, opacity: 0 }}
                         transition={{ type: "spring", stiffness: 300, damping: 26, delay: reduce ? 0 : 1.6 }}>
            <Sparkle size={18} weight="fill" aria-hidden /> Ask about this forecast
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div role="dialog" aria-modal="false" aria-label="Forecast assistant"
                      className="fixed inset-x-0 bottom-0 z-40 flex max-h-[85dvh] flex-col rounded-t-2xl bg-surface shadow-[0_-10px_40px_-12px_rgb(20_32_48/0.35)] md:inset-x-auto md:right-8 md:bottom-8 md:h-[560px] md:w-[400px] md:rounded-2xl"
                      initial={reduce ? false : { y: 40, opacity: 0, scale: 0.98 }} animate={{ y: 0, opacity: 1, scale: 1 }}
                      exit={reduce ? { opacity: 0 } : { y: 40, opacity: 0, scale: 0.98 }}
                      transition={{ type: "spring", stiffness: 320, damping: 30 }}>
            <header className="flex items-center justify-between px-5 pt-4 pb-3">
              <div className="flex items-center gap-2 font-semibold">
                <Sparkle size={18} weight="fill" className="text-accent" aria-hidden /> Forecast assistant
              </div>
              <button onClick={() => setOpen(false)} aria-label="Close assistant"
                      className="grid size-9 place-items-center rounded-full text-muted hover:bg-sunken hover:text-ink">
                <X size={18} weight="bold" />
              </button>
            </header>

            <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-5 pb-3">
              {msgs.length === 0 && (
                <div>
                  <p className="text-muted">Ask anything about this week's outlook. Answers use only the numbers on this page.</p>
                  <div className="mt-4 flex flex-col items-start gap-2">
                    {Object.keys(local).map((q) => (
                      <button key={q} onClick={() => send(q)}
                              className="rounded-full border border-line px-3.5 py-2 text-left text-sm font-medium hover:border-accent hover:text-accent">
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {msgs.map((m, i) => (
                <motion.div key={i} initial={reduce ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                            className={m.role === "user" ? "ml-10 rounded-2xl bg-ink px-4 py-2.5 text-bg" : "mr-6 rounded-2xl bg-sunken px-4 py-2.5"}>
                  <p className="leading-relaxed whitespace-pre-wrap">{m.content}</p>
                  {m.note && <p className="mt-1.5 text-xs text-muted">{m.note}</p>}
                </motion.div>
              ))}
              {busy && (
                <div className="mr-6 flex w-16 gap-1 rounded-2xl bg-sunken px-4 py-3" aria-label="Thinking">
                  {[0, 1, 2].map((k) => (
                    <motion.span key={k} className="size-1.5 rounded-full bg-muted"
                                 animate={reduce ? undefined : { opacity: [0.3, 1, 0.3] }}
                                 transition={{ repeat: Infinity, duration: 1, delay: k * 0.15 }} />
                  ))}
                </div>
              )}
            </div>

            <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-end gap-2 border-t border-line p-3">
              <label htmlFor="ask" className="sr-only">Your question</label>
              <textarea id="ask" ref={inputRef} rows={1} value={input} onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
                        placeholder="Ask a question"
                        className="max-h-28 flex-1 resize-none rounded-2xl bg-sunken px-4 py-2.5 text-ink placeholder:text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent" />
              <button type="submit" disabled={!input.trim() || busy} aria-label="Send"
                      className="grid size-10 place-items-center rounded-full bg-accent text-surface disabled:opacity-40 active:scale-[0.96]">
                <PaperPlaneRight size={18} weight="fill" />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

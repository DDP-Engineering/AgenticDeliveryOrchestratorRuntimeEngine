export type PollEnv = {
  document: { visibilityState: string; addEventListener(type: string, listener: () => void): void; removeEventListener(type: string, listener: () => void): void };
  setInterval(handler: () => void, ms: number): number;
  clearInterval(id: number): void;
};

const browserEnv = (): PollEnv => ({
  document,
  setInterval: (handler, ms) => window.setInterval(handler, ms),
  clearInterval: id => window.clearInterval(id),
});

/**
 * Repeat `tick` every `intervalMs` while the page is visible.
 * Hiding the page stops the timer; showing it again runs `tick` at once and
 * restarts the interval. Returns a function that stops polling.
 */
export function startVisiblePolling(tick: () => void, intervalMs: number, env: PollEnv = browserEnv()): () => void {
  let timer: number | null = null;
  const start = () => { if (timer === null) timer = env.setInterval(tick, intervalMs); };
  const halt = () => { if (timer !== null) { env.clearInterval(timer); timer = null; } };
  const onVisibility = () => {
    if (env.document.visibilityState === "visible") { tick(); start(); }
    else halt();
  };
  env.document.addEventListener("visibilitychange", onVisibility);
  if (env.document.visibilityState === "visible") start();
  return () => { env.document.removeEventListener("visibilitychange", onVisibility); halt(); };
}

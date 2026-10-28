// A busy research endpoint must not open the paper desk's circuit. Keep the
// same timeout/cooldown protections, and share concurrent admin status reads.
export function createPaperDashboardReader(engineFetch) {
  const circuit = { failures: 0, openUntil: 0, lastError: null };
  let pending = null;
  return function readPaperDashboard() {
    if (pending) return pending;
    pending = Promise.resolve().then(() => engineFetch('/v1/options-lab/paper-agents', {
      timeoutMs: 15000, circuit,
    })).then(result => {
      if (result.ok && (!result.data?.ok || !result.data?.live?.agents)) {
        throw new Error('Invalid paper dashboard response');
      }
      return result;
    }).finally(() => { pending = null; });
    return pending;
  };
}

export function scopeQueueToLiveUniverse(queue, universe) {
  const allowed = new Set(
    (universe?.members || [])
      .map((member) => String(member?.symbol || '').trim().toUpperCase())
      .filter(Boolean),
  );
  const items = (queue?.items || []).filter((item) => {
    const symbol = String(item?.symbol || '').trim().toUpperCase();
    return allowed.has(symbol) && Boolean(item?.anchors?.captured_at);
  });
  return {
    ...queue,
    completeness: {
      ...(queue?.completeness || {}),
      validation_candidates: items.length,
      excluded_without_live_identity_or_anchors: Math.max(
        0,
        (queue?.items?.length || 0) - items.length,
      ),
    },
    items,
  };
}

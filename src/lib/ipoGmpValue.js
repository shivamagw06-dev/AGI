// GMP is a rupee premium, not a bounded 0–100 intelligence score.
export function hasGmpNumber(value) {
  return value !== null && value !== undefined && String(value).trim() !== '' && Number.isFinite(Number(value));
}

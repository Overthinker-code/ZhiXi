export const DEFAULT_CHAT_BOTTOM_INSET = 210;

export function computeChatBottomInset(composerHeight: unknown) {
  const height = Number(composerHeight);
  if (!Number.isFinite(height) || height <= 0) return DEFAULT_CHAT_BOTTOM_INSET;
  return Math.max(DEFAULT_CHAT_BOTTOM_INSET, Math.ceil(height) + 44);
}

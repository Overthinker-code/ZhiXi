export function shouldPrepareRecommendation(
  previousId: string | null | undefined,
  nextId: string | null | undefined
) {
  return Boolean(nextId && nextId !== previousId);
}

export function isRecommendationPreviewCurrent(
  requestVersion: number,
  currentVersion: number,
  activeRecommendationId: string | null | undefined,
  requestRecommendationId: string
) {
  return (
    requestVersion === currentVersion &&
    activeRecommendationId === requestRecommendationId
  );
}

export function resolveTrustedApiAssetUrl(
  assetUrl: string,
  pageOrigin: string,
  apiBaseUrl?: string
) {
  const normalizedPageOrigin = new URL(pageOrigin).origin;
  const resolvedUrl = new URL(assetUrl, `${normalizedPageOrigin}/`);
  if (!['http:', 'https:'].includes(resolvedUrl.protocol)) {
    throw new Error('API asset URL must use HTTP(S)');
  }
  const trustedOrigins = new Set([normalizedPageOrigin]);
  if (apiBaseUrl) {
    trustedOrigins.add(new URL(apiBaseUrl, `${normalizedPageOrigin}/`).origin);
  }
  if (!trustedOrigins.has(resolvedUrl.origin)) {
    throw new Error('API asset URL uses an untrusted origin');
  }
  return resolvedUrl.toString();
}

export function resolveTrustedResourceRunStreamUrl(
  streamUrl: string,
  pageOrigin: string,
  apiBaseUrl?: string
) {
  return resolveTrustedApiAssetUrl(streamUrl, pageOrigin, apiBaseUrl);
}

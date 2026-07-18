import type { ResourceRecord } from '@/api/resources';

const BLOB_CACHE_LIMIT = 8;
const previewBlobCache = new Map<string, Blob>();

function cacheKey(accountId: string, resource: ResourceRecord) {
  return `${accountId}:${resource.id}:${resource.file_name}:${resource.file_size}:${resource.uploader_id}:${resource.upload_time}`;
}

/**
 * Preview blobs are private response bodies.  Never reuse one before a user
 * identity is known, and keep the account in every cache key as a defence in
 * depth against a fast account switch.
 */
export function getCachedPreviewBlob(accountId: string | undefined, resource: ResourceRecord) {
  if (!accountId) return undefined;
  const key = cacheKey(accountId, resource);
  const blob = previewBlobCache.get(key);
  if (blob) {
    previewBlobCache.delete(key);
    previewBlobCache.set(key, blob);
  }
  return blob;
}

export function cachePreviewBlob(accountId: string | undefined, resource: ResourceRecord, blob: Blob) {
  if (!accountId) return;
  const key = cacheKey(accountId, resource);
  previewBlobCache.delete(key);
  previewBlobCache.set(key, blob);
  while (previewBlobCache.size > BLOB_CACHE_LIMIT) {
    const oldestKey = previewBlobCache.keys().next().value;
    if (!oldestKey) break;
    previewBlobCache.delete(oldestKey);
  }
}

export function clearPreviewBlobCache() {
  previewBlobCache.clear();
}

// Exported only for the lightweight contract test; it is not UI state.
export function previewBlobCacheSize() {
  return previewBlobCache.size;
}

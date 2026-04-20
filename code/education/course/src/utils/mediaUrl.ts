import axios from 'axios';

function ensureLeadingSlash(path: string) {
  return path.startsWith('/') ? path : `/${path}`;
}

function isAbsoluteUrl(path: string) {
  return /^(https?:)?\/\//i.test(path);
}

export function resolveMediaUrl(rawPath?: string) {
  if (!rawPath) return '';
  if (isAbsoluteUrl(rawPath)) return rawPath;

  const path = ensureLeadingSlash(rawPath);
  const base = axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';

  // Dev mode usually relies on Vite's /api proxy rewrite to /api/v1.
  if (!base) {
    return path.replace(/^\/api\/v1(?=\/)/, '/api');
  }

  const normalizedBase = base.replace(/\/+$/, '');

  // Relative base such as /api/v1.
  if (!isAbsoluteUrl(normalizedBase)) {
    if (normalizedBase.endsWith('/api/v1')) {
      if (path.startsWith('/api/v1/')) return path;
      if (path.startsWith('/api/')) {
        return `${normalizedBase}${path.slice('/api'.length)}`;
      }
    }
    return path;
  }

  const baseUrl = new URL(normalizedBase);
  const basePath = baseUrl.pathname.replace(/\/+$/, '');

  let resolvedPath = path;
  if (basePath.endsWith('/api/v1')) {
    if (path.startsWith('/api/')) {
      resolvedPath = `${basePath}${path.slice('/api'.length)}`;
    } else if (!path.startsWith('/api/v1/')) {
      resolvedPath = `${basePath}${path}`;
    }
  }

  return `${baseUrl.origin}${resolvedPath}`;
}

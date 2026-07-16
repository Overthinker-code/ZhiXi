import axios from 'axios';

function detailToString(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail;
  }
  if (!Array.isArray(detail)) {
    return '';
  }
  return detail
    .map((d: unknown) => {
      if (typeof d === 'object' && d !== null && 'msg' in d) {
        return String((d as { msg: string }).msg);
      }
      return JSON.stringify(d);
    })
    .join('; ');
}

/**
 * 会话失效：需重新登录。FastAPI JWT 校验失败常为 403 + "Could not validate credentials"。
 * 非此类 403（如权限不足）不应整站登出。
 */
export default function isSessionInvalidError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    return false;
  }
  const { response } = error;
  if (!response) {
    return false;
  }
  const { status, data: resData } = response;
  const data = resData as Record<string, unknown> | undefined;
  const detail =
    data && typeof data === 'object' && 'detail' in data
      ? detailToString((data as { detail: unknown }).detail)
      : '';
  const low = detail.toLowerCase();
  const path = (error.config?.url || '').toLowerCase();

  // 裸 401（无 body、网关误报）不误踢；/users/me 的 401 视为会话失效
  if (status === 401) {
    if (path.includes('/users/me')) {
      return true;
    }
    if (!low) {
      return false;
    }
    return (
      low.includes('not authenticated') ||
      low.includes('could not validate') ||
      low.includes('credentials') ||
      low.includes('invalid token') ||
      low.includes('token expired') ||
      low.includes('unauthorized')
    );
  }
  if (status === 403) {
    return (
      low.includes('could not validate credentials') ||
      low.includes('not authenticated')
    );
  }
  return false;
}

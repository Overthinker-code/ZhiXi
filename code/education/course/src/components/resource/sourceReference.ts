export type SourceKind = 'book' | 'paper' | 'video' | '';

export interface SourceReference {
  provider: string;
  kind: SourceKind;
  summary: string;
  authors: string;
  year: string;
  language: string;
  accessLabel: string;
  thumbnailUrl: string;
  canonicalUrl: string;
  previewUrl: string;
  verifiedAt: string;
  domain: string;
}

export interface SourceReferenceFallback {
  provider?: string | null;
  url?: string | null;
  domain?: string | null;
  summary?: string | null;
}

type UnknownRecord = Record<string, unknown>;

const COPY_BLOCKLIST = /即时预览|模型|爬取|生成后|未物化|内部|agent\s*trace|agent|trace|完整版本会在|资料暂时没有可预览内容/iu;

function record(value: unknown): UnknownRecord | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as UnknownRecord
    : null;
}

function text(value: unknown, maximum = 600) {
  const raw = typeof value === 'string' || typeof value === 'number' ? String(value) : '';
  return raw.replace(/\s+/g, ' ').trim().slice(0, maximum);
}

function valueFrom(recordValue: UnknownRecord | null, snakeName: string, camelName: string) {
  return text(recordValue?.[snakeName] ?? recordValue?.[camelName]);
}

function textList(value: unknown, maximum = 320) {
  if (!Array.isArray(value)) return text(value, maximum);
  return value
    .filter((entry) => typeof entry === 'string' || typeof entry === 'number')
    .map((entry) => text(entry, 120))
    .filter(Boolean)
    .join(' · ')
    .slice(0, maximum);
}

/** Only allow ordinary web URLs; never return credentials, scripts, or data URLs. */
export function safeWebUrl(value: unknown) {
  const raw = text(value, 2_000);
  if (!raw) return '';
  try {
    const url = new URL(raw);
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password) {
      return '';
    }
    return url.toString();
  } catch {
    return '';
  }
}

export function webDomain(value: unknown) {
  const safeUrl = safeWebUrl(value);
  if (!safeUrl) return '';
  try {
    return new URL(safeUrl).hostname;
  } catch {
    return '';
  }
}

function metadataRecord(value: unknown) {
  const item = record(value);
  const content = record(item?.content);
  const metadata = record(item?.metadata);
  return record(item?.source_metadata)
    || record(item?.sourceMetadata)
    || record(content?.source_metadata)
    || record(content?.sourceMetadata)
    || record(metadata?.source_metadata)
    || record(metadata?.sourceMetadata)
    || null;
}

export function sourceReferenceFrom(value: unknown, fallback: SourceReferenceFallback = {}): SourceReference {
  const metadata = metadataRecord(value);
  const rawKind = (valueFrom(metadata, 'kind', 'kind') || valueFrom(metadata, 'resource_kind', 'resourceKind')).toLowerCase();
  const kind: SourceKind = ['book', 'paper', 'video'].includes(rawKind)
    ? rawKind as SourceKind
    : '';
  const canonicalUrl = safeWebUrl(valueFrom(metadata, 'canonical_url', 'canonicalUrl') || fallback.url);
  const previewUrl = safeWebUrl(valueFrom(metadata, 'preview_url', 'previewUrl'));
  const domain = text(fallback.domain, 200) || webDomain(canonicalUrl) || webDomain(previewUrl);

  return {
    provider: valueFrom(metadata, 'provider_name', 'providerName')
      || valueFrom(metadata, 'provider', 'provider')
      || text(fallback.provider, 200)
      || domain
      || '开放学习来源',
    kind,
    summary: valueFrom(metadata, 'summary', 'summary') || text(fallback.summary),
    authors: textList(metadata?.authors),
    year: valueFrom(metadata, 'year', 'year'),
    language: valueFrom(metadata, 'language', 'language'),
    accessLabel: valueFrom(metadata, 'license_access_label', 'licenseAccessLabel')
      || valueFrom(metadata, 'license_status', 'licenseStatus')
      || valueFrom(metadata, 'license', 'license')
      || valueFrom(metadata, 'access_label', 'accessLabel'),
    thumbnailUrl: safeWebUrl(valueFrom(metadata, 'thumbnail_url', 'thumbnailUrl') || valueFrom(metadata, 'cover_url', 'coverUrl')),
    canonicalUrl,
    previewUrl,
    verifiedAt: valueFrom(metadata, 'verified_at', 'verifiedAt'),
    domain,
  };
}

export function sourceCategory(kind: SourceKind, generated = false) {
  if (generated) return '个性化学习方案';
  if (kind === 'video') return '开放课程视频';
  if (kind === 'book') return '开放图书';
  if (kind === 'paper') return '开放论文';
  return '开放学习资源';
}

export function sourceActionLabel(kind: SourceKind) {
  if (kind === 'video') return '在原站观看';
  if (kind === 'book' || kind === 'paper') return '在原站阅读';
  return '访问来源';
}

/** Keep recommendation reasoning short and student-facing even on legacy records. */
export function studentFacingReason(...values: unknown[]) {
  for (const value of values) {
    const candidate = text(value, 180);
    if (candidate && !COPY_BLOCKLIST.test(candidate)) return candidate;
  }
  return '围绕当前学习主题，安排下一步学习。';
}

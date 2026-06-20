const INLINE_CITATION_RE = /\s*\[(?:citation|doc):(\d+)\]/gi;

export const stripInlineCitationMarkers = (value: unknown) =>
  String(value || '')
    .replace(INLINE_CITATION_RE, '')
    .replace(/[ \t]+\n/g, '\n')
    .trim();

export const renderInlineCitationMarkers = (value: unknown) =>
  String(value || '')
    .replace(INLINE_CITATION_RE, (_match, id) => ` [${id}](#citation-${id})`)
    .replace(/[ \t]+\n/g, '\n')
    .trim();

export const normalizeCitationScope = (value: unknown) => {
  const raw = String(value || '').trim().toLowerCase();
  if (
    [
      'uploaded_document',
      'current_file',
      'thread_file',
      'mounted_file',
      'personal',
      'document',
    ].includes(raw)
  ) {
    return 'uploaded_document';
  }
  if (
    [
      'knowledge_base',
      'course',
      'course_library',
      'system',
      'resource',
      'course_resource',
    ].includes(raw)
  ) {
    return 'knowledge_base';
  }
  return raw;
};

export const isRagBindableReference = (file?: Record<string, any> | null) =>
  Boolean(file?.file_id && file?.rag_bindable !== false && !file?.is_virtual);

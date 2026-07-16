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
      'resource',
      'course_resource',
      'route_resource',
      'resource_hint',
    ].includes(raw)
  ) {
    return raw === 'resource_hint' ? 'resource_hint' : 'course_resource';
  }
  if (
    [
      'course',
      'course_context',
      'route_context',
    ].includes(raw)
  ) {
    return raw === 'route_context' ? 'route_context' : 'course';
  }
  if (
    [
      'knowledge_base',
      'course_library',
      'system',
    ].includes(raw)
  ) {
    return 'knowledge_base';
  }
  return raw;
};

export const isCitationHintScope = (value: unknown) =>
  ['resource_hint', 'route_context', 'route_file_hint'].includes(
    normalizeCitationScope(value)
  );

export const isRagBindableReference = (file?: Record<string, any> | null) =>
  Boolean(file?.file_id && file?.rag_bindable !== false && !file?.is_virtual);

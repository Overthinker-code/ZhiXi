import axios from 'axios';
import type {
  CourseKnowledgeLink,
  CourseKnowledgeMap,
  CourseKnowledgeMapType,
  CourseKnowledgeNode,
} from '@/data/courseWorkspace';

export interface CourseKnowledgeGraphSummary {
  nodeCount: number;
  linkCount: number;
  resourceCount: number;
  evidenceBackedNodeCount: number;
  updatedAt?: string;
}

export interface CourseKnowledgeGraphResponse {
  courseId: string;
  summary: CourseKnowledgeGraphSummary;
  maps: CourseKnowledgeMap[];
}

export interface CourseKnowledgeNeighborsResponse {
  courseId: string;
  centerNodeId: string;
  depth: number;
  nodes: CourseKnowledgeNode[];
  links: CourseKnowledgeLink[];
}

export type CourseKnowledgeNodeActionType =
  | 'evidence_read'
  | 'review_queued'
  | 'resource_requested';

export interface CourseKnowledgeNodeActionState {
  evidenceRead: boolean;
  reviewQueued: boolean;
  resourceRequested: boolean;
  updatedAt?: string;
}

export interface CourseKnowledgeNodeActionsResponse {
  courseId: string;
  mapType: CourseKnowledgeMapType;
  states: Record<string, CourseKnowledgeNodeActionState>;
}

const allowedMapTypes = new Set<CourseKnowledgeMapType>([
  'knowledge',
  'problem',
  'ability',
  'target',
  'tutor',
]);

const allowedNodeTypes = new Set<CourseKnowledgeNode['type']>([
  'chapter',
  'concept',
  'resource',
  'task',
  'ability',
]);

const allowedRelations = new Set<CourseKnowledgeLink['relation']>([
  '父子关系',
  '前后置关系',
  '关联关系',
  '资料支撑',
  '任务驱动',
]);

function text(value: unknown) {
  return typeof value === 'string' ? value.trim() : '';
}

function textList(value: unknown) {
  return Array.isArray(value)
    ? value.map((item) => text(item)).filter(Boolean)
    : [];
}

function finiteNumber(value: unknown, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizeNode(value: unknown): CourseKnowledgeNode | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  const id = text(item.id);
  const label = text(item.label);
  if (!id || !label) return null;
  const rawType = text(item.type) as CourseKnowledgeNode['type'];
  const type = allowedNodeTypes.has(rawType) ? rawType : 'concept';
  const masteryValue =
    item.mastery === null || item.mastery === undefined || item.mastery === ''
      ? Number.NaN
      : Number(item.mastery);
  return {
    id,
    label,
    type,
    x: finiteNumber(item.x),
    y: finiteNumber(item.y),
    weight: Math.max(1, finiteNumber(item.weight, 1)),
    detail: text(item.detail) || undefined,
    mastery: Number.isFinite(masteryValue)
      ? Math.max(0, Math.min(100, masteryValue))
      : undefined,
    evidence: textList(item.evidence),
    outcomes: textList(item.outcomes),
    misconceptions: textList(item.misconceptions),
    activities: textList(item.activities),
    resources: textList(item.resources),
    checks: textList(item.checks),
    recommendedAction: text(item.recommendedAction ?? item.recommended_action) || undefined,
  };
}

function normalizeLink(value: unknown, nodeIds?: Set<string>): CourseKnowledgeLink | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  const source = text(item.source);
  const target = text(item.target);
  const rawRelation = text(item.relation) as CourseKnowledgeLink['relation'];
  if (
    !source ||
    !target ||
    !allowedRelations.has(rawRelation) ||
    (nodeIds && (!nodeIds.has(source) || !nodeIds.has(target)))
  ) {
    return null;
  }
  const rawStrength = finiteNumber(item.strength, 0);
  return {
    source,
    target,
    relation: rawRelation,
    strength: Math.round(
      Math.max(0, Math.min(100, rawStrength <= 1 ? rawStrength * 100 : rawStrength))
    ),
  };
}

function normalizeMap(value: unknown): CourseKnowledgeMap | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  const rawType = text(item.type) as CourseKnowledgeMapType;
  if (!allowedMapTypes.has(rawType)) return null;
  const nodes = (Array.isArray(item.nodes) ? item.nodes : [])
    .map(normalizeNode)
    .filter(Boolean) as CourseKnowledgeNode[];
  const nodeIds = new Set(nodes.map((node) => node.id));
  const links = (Array.isArray(item.links) ? item.links : [])
    .map((link) => normalizeLink(link, nodeIds))
    .filter(Boolean) as CourseKnowledgeLink[];
  return {
    type: rawType,
    title: text(item.title) || '课程知识图谱',
    description: text(item.description) || '该图谱来自课程知识库与学习资源关系。',
    focusTags: textList(item.focusTags ?? item.focus_tags),
    nodes,
    links,
  };
}

export function normalizeCourseKnowledgeGraph(value: unknown): CourseKnowledgeGraphResponse {
  if (!value || typeof value !== 'object') throw new Error('课程图谱响应格式无效');
  const item = value as Record<string, unknown>;
  const maps = (Array.isArray(item.maps) ? item.maps : [])
    .map(normalizeMap)
    .filter(Boolean) as CourseKnowledgeMap[];
  const summary = (item.summary && typeof item.summary === 'object'
    ? item.summary
    : {}) as Record<string, unknown>;
  return {
    courseId: text(item.courseId ?? item.course_id),
    summary: {
      nodeCount: finiteNumber(summary.nodeCount ?? summary.node_count, maps.reduce((sum, map) => sum + map.nodes.length, 0)),
      linkCount: finiteNumber(summary.linkCount ?? summary.link_count, maps.reduce((sum, map) => sum + map.links.length, 0)),
      resourceCount: finiteNumber(summary.resourceCount ?? summary.resource_count),
      evidenceBackedNodeCount: finiteNumber(
        summary.evidenceBackedNodeCount ?? summary.evidence_backed_node_count
      ),
      updatedAt: text(summary.updatedAt ?? summary.updated_at) || undefined,
    },
    maps,
  };
}

export function normalizeCourseKnowledgeNeighbors(
  value: unknown
): CourseKnowledgeNeighborsResponse {
  if (!value || typeof value !== 'object') throw new Error('相邻节点响应格式无效');
  const item = value as Record<string, unknown>;
  const nodes = (Array.isArray(item.nodes) ? item.nodes : [])
    .map(normalizeNode)
    .filter(Boolean) as CourseKnowledgeNode[];
  const nodeIds = new Set(nodes.map((node) => node.id));
  const links = (Array.isArray(item.links) ? item.links : [])
    .map((link) => normalizeLink(link, nodeIds))
    .filter(Boolean) as CourseKnowledgeLink[];
  return {
    courseId: text(item.courseId ?? item.course_id),
    centerNodeId: text(item.centerNodeId ?? item.center_node_id),
    depth: Math.max(1, finiteNumber(item.depth, 1)),
    nodes,
    links,
  };
}

export async function fetchCourseKnowledgeGraph(
  courseId: string,
  mapType?: CourseKnowledgeMapType
) {
  const response = await axios.get(`/api/knowledge-graph/courses/${encodeURIComponent(courseId)}`, {
    params: mapType ? { map_type: mapType } : undefined,
  });
  return normalizeCourseKnowledgeGraph(response.data);
}

export async function fetchCourseKnowledgeNeighbors(
  courseId: string,
  nodeId: string,
  mapType: CourseKnowledgeMapType,
  depth = 1
) {
  const response = await axios.get(
    `/api/knowledge-graph/courses/${encodeURIComponent(courseId)}/nodes/${encodeURIComponent(nodeId)}/neighbors`,
    { params: { depth, map_type: mapType } }
  );
  return normalizeCourseKnowledgeNeighbors(response.data);
}

export function normalizeNodeActions(value: unknown): CourseKnowledgeNodeActionsResponse {
  if (!value || typeof value !== 'object') throw new Error('节点动作响应格式无效');
  const item = value as Record<string, unknown>;
  const rawMapType = text(item.mapType ?? item.map_type) as CourseKnowledgeMapType;
  if (!allowedMapTypes.has(rawMapType)) throw new Error('节点动作图谱类型无效');
  const mapType = rawMapType;
  const rawStates = item.states && typeof item.states === 'object'
    ? item.states as Record<string, unknown>
    : {};
  const states = Object.fromEntries(
    Object.entries(rawStates).flatMap(([nodeId, value]) => {
      if (!nodeId || !value || typeof value !== 'object') return [];
      const state = value as Record<string, unknown>;
      return [[nodeId, {
        evidenceRead: Boolean(state.evidenceRead ?? state.evidence_read),
        reviewQueued: Boolean(state.reviewQueued ?? state.review_queued),
        resourceRequested: Boolean(state.resourceRequested ?? state.resource_requested),
        updatedAt: text(state.updatedAt ?? state.updated_at) || undefined,
      } satisfies CourseKnowledgeNodeActionState]];
    })
  );
  return {
    courseId: text(item.courseId ?? item.course_id),
    mapType,
    states,
  };
}

export async function fetchCourseKnowledgeNodeActions(
  courseId: string,
  mapType: CourseKnowledgeMapType,
  nodeId?: string
) {
  const response = await axios.get(
    `/api/knowledge-graph/courses/${encodeURIComponent(courseId)}/actions`,
    { params: { map_type: mapType, node_id: nodeId || undefined } }
  );
  return normalizeNodeActions(response.data);
}

export async function setCourseKnowledgeNodeAction(
  courseId: string,
  nodeId: string,
  mapType: CourseKnowledgeMapType,
  actionType: CourseKnowledgeNodeActionType,
  active: boolean
) {
  const response = await axios.put(
    `/api/knowledge-graph/courses/${encodeURIComponent(courseId)}/nodes/${encodeURIComponent(nodeId)}/actions/${actionType}`,
    { active },
    { params: { map_type: mapType } }
  );
  return normalizeNodeActions(response.data);
}

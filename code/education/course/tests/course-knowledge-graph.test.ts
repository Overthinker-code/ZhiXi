import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  normalizeCourseKnowledgeGraph,
  normalizeCourseKnowledgeNeighbors,
  normalizeNodeActions,
} from '../src/api/knowledge-graph';

const courseId = 'c1111111-1111-4111-9111-111111111101';
const rootId = '11111111-1111-4111-9111-111111111111';
const childId = '22222222-2222-4222-9222-222222222222';

const graph = normalizeCourseKnowledgeGraph({
  courseId,
  summary: {
    nodeCount: 2,
    linkCount: 1,
    resourceCount: 0,
    evidenceBackedNodeCount: 1,
  },
  maps: [
    {
      type: 'knowledge',
      title: '数据库系统知识图谱',
      description: '来自课程计划与真实学习证据。',
      nodes: [
        { id: rootId, label: '数据库系统', type: 'chapter', weight: 4, x: 10, y: 20 },
        {
          id: childId,
          label: '事务与并发控制',
          type: 'concept',
          weight: 2,
          x: 30,
          y: 40,
          mastery: 72,
        },
      ],
      links: [
        { source: rootId, target: childId, relation: '父子关系', strength: 0.9 },
        { source: rootId, target: 'missing', relation: '父子关系', strength: 1 },
      ],
      focusTags: ['事务'],
    },
    {
      type: 'not-supported',
      title: '伪图谱',
      nodes: [{ id: 'fake', label: 'fake' }],
      links: [],
    },
  ],
});

assert.equal(graph.courseId, courseId);
assert.equal(graph.maps.length, 1);
assert.equal(graph.maps[0].nodes[0].id, rootId);
assert.equal(graph.maps[0].nodes[0].mastery, undefined);
assert.equal(graph.maps[0].nodes[1].mastery, 72);
assert.deepEqual(graph.maps[0].links, [
  { source: rootId, target: childId, relation: '父子关系', strength: 90 },
]);

const neighbors = normalizeCourseKnowledgeNeighbors({
  courseId,
  centerNodeId: childId,
  depth: 1,
  nodes: [
    { id: rootId, label: '数据库系统', type: 'chapter' },
    { id: childId, label: '事务与并发控制', type: 'concept' },
  ],
  links: [{ source: rootId, target: childId, relation: '前后置关系', strength: 80 }],
});
assert.equal(neighbors.centerNodeId, childId);
assert.equal(neighbors.nodes.length, 2);
assert.equal(neighbors.links.length, 1);

const actions = normalizeNodeActions({
  courseId,
  mapType: 'knowledge',
  states: {
    [childId]: {
      evidenceRead: true,
      reviewQueued: false,
      resourceRequested: true,
      updatedAt: '2026-07-14T10:00:00Z',
    },
  },
});
assert.equal(actions.states[childId].evidenceRead, true);
assert.equal(actions.states[childId].reviewQueued, false);
assert.equal(actions.states[childId].resourceRequested, true);
assert.throws(
  () => normalizeNodeActions({ courseId, mapType: 'invented', states: {} }),
  /图谱类型无效/
);

const pageSource = readFileSync(
  resolve(__dirname, '../src/views/course/workspace/CourseKnowledgePage.vue'),
  'utf8'
);
assert.doesNotMatch(pageSource, /buildCourseKnowledgeMaps|knowledge-node-status/);
assert.match(pageSource, /fetchCourseKnowledgeGraph/);
assert.match(pageSource, /fetchCourseKnowledgeNeighbors/);
assert.match(pageSource, /fetchCourseKnowledgeNodeActions/);
assert.match(pageSource, /setCourseKnowledgeNodeAction/);
assert.match(pageSource, /学习状态保存失败，已恢复原状态/);

console.log('course knowledge graph contract tests passed');

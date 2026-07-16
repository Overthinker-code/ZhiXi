import assert from 'node:assert/strict';
import { buildLearningPortraitViewModel } from '../src/views/profile/learning-data/learningPortraitViewModel';

const emptyPortrait = buildLearningPortraitViewModel({
  diagnosis: null,
  practice: null,
  courses: [],
  learningPath: null,
  sampleCourses: [],
});

assert.equal(emptyPortrait.previewMode, true);
assert.equal(emptyPortrait.overallScore, null);
assert.deepEqual(emptyPortrait.dimensions, []);
assert.deepEqual(emptyPortrait.dimensionStatuses, []);
assert.deepEqual(emptyPortrait.trendSeries, []);
assert.deepEqual(emptyPortrait.trendLabels, []);
assert.deepEqual(emptyPortrait.rhythm, []);
assert.deepEqual(emptyPortrait.focusCurve, []);
assert.deepEqual(emptyPortrait.resourcePreferences, []);
assert.deepEqual(emptyPortrait.recommendations, []);

const practicePortrait = buildLearningPortraitViewModel({
  diagnosis: null,
  practice: {
    total_sessions: 2,
    total_questions: 10,
    correct_rate: 0.8,
    subjects: ['数据库系统'],
    topics: [],
    assignment_completed: 0,
    assignment_total: 0,
  },
  courses: [],
  learningPath: null,
});

assert.equal(practicePortrait.previewMode, false);
assert.equal(practicePortrait.overallScore, null);
assert.deepEqual(practicePortrait.dimensions, []);
assert.equal(practicePortrait.growthRate, null);
assert.deepEqual(practicePortrait.trendSeries, []);
assert.deepEqual(practicePortrait.rhythm, []);

const diagnosedPortrait = buildLearningPortraitViewModel({
  diagnosis: {
    mastery_map: { ACID: 0.72, 可串行化: 0.64 },
    weak_points: ['可串行化'],
    strengths: ['能准确说明事务原子性'],
    recommended_actions: ['先完成一组并发调度判断题'],
    recommended_resources: ['讲义', '练习'],
    learning_style: '图文与练习',
    current_goal: '事务与并发控制',
    classroom_behavior_summary: {},
    process_steps: [],
    portrait_dimensions: [
      ['knowledge_foundation', '知识基础', 72],
      ['problem_solving', '问题解决', 68],
      ['transfer_application', '迁移应用', 61],
      ['learning_engagement', '学习投入', 76],
      ['cognitive_engagement', '认知投入', 70],
      ['attention_stability', '注意稳定', 81],
    ].map(([key, label, value]) => ({
      key,
      label,
      value,
      state: 'steady',
      sample_size: 2,
      sources: ['test'],
      method_version: 'portrait_evidence_v1',
    })),
  } as any,
  practice: null,
  courses: [],
  learningPath: null,
});

assert.deepEqual(
  diagnosedPortrait.dimensions.map((item) => [item.key, item.value]),
  [
    ['knowledge_foundation', 72],
    ['problem_solving', 68],
    ['transfer_application', 61],
    ['learning_engagement', 76],
    ['cognitive_engagement', 70],
    ['attention_stability', 81],
  ]
);
assert.equal(diagnosedPortrait.dimensions.length, 6);
assert.equal(diagnosedPortrait.dimensionStatuses.length, 6);
assert.equal(diagnosedPortrait.engagement, 76);
assert.equal(diagnosedPortrait.trendEstimated, true);
assert.deepEqual(diagnosedPortrait.trendLabels, ['ACID', '可串行化']);
assert.deepEqual(diagnosedPortrait.trendSeries[0]?.values, [72, 64]);
assert.ok(diagnosedPortrait.resourcePreferences.length > 0);
assert.ok(diagnosedPortrait.resourcePreferences.every((item) => item.value === null));
assert.equal(diagnosedPortrait.recommendations[0]?.title, '优先学习：可串行化');
assert.ok(
  diagnosedPortrait.recommendations.every(
    (item) => !/\d+\s*条证据|可信度|当前画像\s*\d+\s*分/.test(item.evidence)
  )
);

const analyticsPortrait = buildLearningPortraitViewModel({
  diagnosis: diagnosedPortrait as any,
  practice: null,
  courses: [],
  learningPath: null,
  analytics: {
    profile_version: 18,
    generated_at: '2026-07-14T14:32:00+08:00',
    evidence_count: 368,
    confidence: 86,
    overall_score: 72,
    growth_30d: 8.4,
    engagement: 81,
    attention_count: 3,
    trend_labels: Array.from({ length: 12 }, (_, index) => `第${index + 1}周`),
    trend_series: [
      {
        key: 'knowledge_understanding',
        label: '知识理解',
        values: [50, 57, 60, 63, 67, 71, 74, 75, 73, 74, 76, 76],
      },
    ],
    capabilities: [
      {
        key: 'knowledge_understanding',
        label: '知识理解',
        value: 76,
        previous: 70,
        evidence_count: 12,
      },
      {
        key: 'problem_solving',
        label: '问题解决',
        value: 72,
        previous: 66,
        evidence_count: 8,
      },
      {
        key: 'practice_transfer',
        label: '实践迁移',
        value: 65,
        previous: 60,
        evidence_count: 4,
      },
    ],
    rhythm: {
      week_labels: ['第8周', '第9周', '第10周', '第11周', '第12周'],
      day_labels: ['一', '二', '三', '四', '五', '六', '日'],
      activity: [[0, 20, 40, 20, 0, 0, 0]],
      hour_labels: ['00', '04', '08', '12', '16', '20'],
      focus_hours: [0.2, 0.6, 1.1, 2.8, 1.4, 2.2],
      method_version: 'activity_session_gap_45m_v1',
    },
    resource_preferences: [
      { key: 'document', label: '文档阅读', value: 60, count: 6 },
      { key: 'quiz', label: '测验练习', value: 40, count: 4 },
    ],
    courses: [],
    method_version: 'portrait_analytics_v1',
  },
});

assert.equal(analyticsPortrait.previewMode, false);
assert.equal(analyticsPortrait.overallScore, 72);
assert.equal(analyticsPortrait.growthRate, 8.4);
assert.equal(analyticsPortrait.confidence, 86);
assert.equal(analyticsPortrait.evidenceCount, 368);
assert.equal(analyticsPortrait.trendEstimated, false);
assert.equal(analyticsPortrait.trendSeries[0]?.values.length, 12);
assert.equal(analyticsPortrait.dimensions[0]?.previous, 70);
assert.equal(analyticsPortrait.resourcePreferences[0]?.reason, '6 次真实记录');

const floatingPointPortrait = buildLearningPortraitViewModel({
  diagnosis: null,
  practice: null,
  courses: [],
  learningPath: null,
  analytics: {
    profile_version: 1,
    generated_at: '2026-07-14T15:00:00+08:00',
    evidence_count: 2,
    confidence: 60,
    overall_score: 70,
    growth_30d: 0.30000000000000004,
    engagement: 70,
    attention_count: 1,
    trend_labels: ['第1周', '第2周', '第3周', '第4周'],
    trend_series: [
      {
        key: 'knowledge_understanding',
        label: '知识理解',
        values: [
          60.10000000000001,
          70.29999999999998,
          Number.NaN,
          Number.POSITIVE_INFINITY,
          90,
        ],
      },
    ],
    capabilities: [],
    rhythm: {
      week_labels: ['第1周'],
      day_labels: ['一'],
      activity: [[33.333333333333336]],
      hour_labels: ['08:00', '12:00'],
      focus_hours: [0.30000000000000004, 1.7999999999999998],
      method_version: 'test',
    },
    resource_preferences: [
      { key: 'document', label: '文档阅读', value: 66.66666666666667, count: 2 },
    ],
    courses: [],
    method_version: 'test',
  },
});

assert.deepEqual(floatingPointPortrait.trendSeries[0]?.values, [60.1, 70.3, null, null]);
assert.equal(floatingPointPortrait.trendSeries[0]?.values.length, 4);
assert.deepEqual(floatingPointPortrait.rhythm, [[33.3]]);
assert.deepEqual(floatingPointPortrait.focusCurve, [0.3, 1.8]);
assert.equal(floatingPointPortrait.resourcePreferences[0]?.value, 66.7);

console.log('learning portrait truth tests passed');

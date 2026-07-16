import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  buildProductionResourceTypes,
  buildResourcePackageViewModel,
} from '../src/views/resource-workshop/resourcePackageViewModel';

const wordKinds = buildProductionResourceTypes('docx');
assert.ok(wordKinds.includes('lecture_docx'));
assert.ok(wordKinds.includes('practice_docx'));
assert.ok(!wordKinds.includes('lecture_pdf'));
assert.ok(!wordKinds.includes('practice_pdf'));

const pdfKinds = buildProductionResourceTypes('pdf');
assert.ok(pdfKinds.includes('lecture_pdf'));
assert.ok(pdfKinds.includes('practice_pdf'));
assert.ok(!pdfKinds.includes('lecture_docx'));
assert.ok(!pdfKinds.includes('practice_docx'));

const bothKinds = buildProductionResourceTypes('both');
assert.ok(bothKinds.includes('lecture_docx'));
assert.ok(bothKinds.includes('lecture_pdf'));
assert.ok(bothKinds.includes('practice_docx'));
assert.ok(bothKinds.includes('practice_pdf'));
for (const retained of [
  'mind_map',
  'reading_list',
  'case_project',
  'video_script',
  'quality_checklist',
] as const) {
  assert.ok(wordKinds.includes(retained));
  assert.ok(pdfKinds.includes(retained));
}

const viewModel = buildResourcePackageViewModel(
  {
    package_id: 'pkg-format-test',
    subject: '数据库系统原理',
    topic: '事务',
    generated_at: '2026-07-14T12:00:00Z',
    local_model_profile: {},
    agent_trace: [],
    quality_notes: [],
    persistence_status: 'resources_persisted',
    persisted_resource_ids: [],
    artifacts: [
      {
        kind: 'lecture_docx',
        title: '事务讲义',
        file_name: 'lecture.docx',
        download_url: '/lecture.docx',
        content_type:
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        file_size: 128,
        preview: '',
      },
      {
        kind: 'practice_docx',
        title: '事务练习',
        file_name: 'practice.docx',
        download_url: '/practice.docx',
        content_type:
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        file_size: 128,
        preview: '',
      },
    ],
  },
  {
    goal: '掌握事务隔离',
    difficulty: 'standard',
    targetMinutes: 45,
    personalizationBasis: [],
  }
);
assert.deepEqual(
  viewModel.resources.map((item) => item.type),
  ['lecture_doc', 'practice_set']
);

const workshopSource = readFileSync(
  resolve(__dirname, '../src/views/resource-workshop/index.vue'),
  'utf8'
);
assert.match(workshopSource, /generateResourcePackageCompatible as generateDownloadableResourcePackage/);
assert.match(workshopSource, /onEvidence:\s*\(evidence\)/);
assert.match(workshopSource, /cancelResourceRun/);
assert.match(workshopSource, /resumeResourceRun/);
assert.match(workshopSource, /buildProductionResourceTypes\(form\.documentFormat\)/);

const apiSource = readFileSync(
  resolve(__dirname, '../src/api/resource-generation.ts'),
  'utf8'
);
assert.match(apiSource, /transport: 'resource_run_polling'/);
assert.match(apiSource, /normalizeTopLevelRunEvidence\(\{/);
assert.match(apiSource, /'Idempotency-Key': idempotencyKey/);
assert.doesNotMatch(apiSource, /activeRunId/);
assert.doesNotMatch(apiSource, /response\?\.status !== 409/);
assert.match(workshopSource, /RESOURCE_RUN_ALREADY_ACTIVE/);
assert.match(workshopSource, /讲义与练习格式/);
assert.match(workshopSource, /conflictingRunId/);
assert.match(workshopSource, /查看正在生成的任务/);
assert.match(workshopSource, /originalRequest\?\.learning_goal/);

const interceptorSource = readFileSync(
  resolve(__dirname, '../src/api/interceptor.ts'),
  'utf8'
);
assert.match(interceptorSource, /return Promise\.reject\(error\)/);
assert.doesNotMatch(interceptorSource, /Promise\.reject\(new Error\(message\)\)/);
assert.match(
  interceptorSource,
  /if \(!isLogin && isSessionInvalidError\(error\)\)/
);
assert.doesNotMatch(
  interceptorSource,
  /!isEducationApi && isSessionInvalidError\(error\)/
);

const resourceHubSource = readFileSync(
  resolve(__dirname, '../src/views/course/ResourceHubPage.vue'),
  'utf8'
);
assert.match(resourceHubSource, /内容审查未通过，已阻止不合格资料入库/);

console.log('resource workshop ResourceRun contract tests passed');

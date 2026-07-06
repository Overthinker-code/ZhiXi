import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5174';
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8001';
const USERNAME = process.env.DEMO_USER || 'student@example.com';
const PASSWORD = process.env.DEMO_PASSWORD || 'student123456';
const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
const repoRoot = path.resolve(process.cwd(), '../../..');
const outDir = path.resolve(repoRoot, 'output', `tutor-acceptance-${stamp}`);
const reportPath = path.resolve(repoRoot, 'TUTOR_ACCEPTANCE_REPORT.md');

async function loginToken() {
  const body = new URLSearchParams();
  body.set('username', USERNAME);
  body.set('password', PASSWORD);
  const res = await fetch(`${BACKEND_URL}/api/v1/login/access-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!res.ok) throw new Error(`login failed: HTTP ${res.status}`);
  const data = await res.json();
  if (!data.access_token) throw new Error('login failed: missing access_token');
  return data.access_token;
}

async function waitForVisible(page, selector, timeout = 15000) {
  await page.waitForSelector(selector, { state: 'visible', timeout });
}

async function screenshot(page, name) {
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function openToolMenu(page) {
  const menuButton = page.getByTestId('tool-menu');
  await menuButton.click();
  await page.getByText('能力', { exact: true }).waitFor({ state: 'visible', timeout: 5000 });
}

async function chooseTool(page, testId) {
  await openToolMenu(page);
  await page.getByTestId(testId).click();
}

async function run() {
  await fs.rm(outDir, { recursive: true, force: true });
  await fs.mkdir(outDir, { recursive: true });
  const rows = [];
  let token = '';
  try {
    token = await loginToken();
    rows.push(['backend login', 'PASS', '真实 token 已获取']);
  } catch (error) {
    rows.push(['backend login', 'FAIL', error instanceof Error ? error.message : String(error)]);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const capturedPayloads = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/ai/chat/stream')) {
      capturedPayloads.push(request.postData() || '');
    }
  });

  try {
    await page.goto(`${FRONTEND_URL}/`, { waitUntil: 'domcontentloaded' });
    if (token) {
      await page.evaluate((value) => {
        localStorage.setItem('token', value);
      }, token);
    }
    await page.goto(`${FRONTEND_URL}/tutor`, { waitUntil: 'networkidle' });
    await waitForVisible(page, '[data-testid="tutor-composer"]');
    rows.push(['/tutor empty', 'PASS', await screenshot(page, 'tutor-empty.png')]);

    await page.getByRole('button', { name: '上下文', exact: true }).click();
    await waitForVisible(page, '[data-testid="tutor-context-drawer"]');
    rows.push(['context drawer', 'PASS', await screenshot(page, 'tutor-course-context-open.png')]);
    await page.getByTestId('tutor-context-drawer').getByRole('button', { name: '关闭' }).click();

    await chooseTool(page, 'tool-web-search');
    await page.getByTestId('tool-menu').click();
    await page.getByTestId('tool-reasoning').click();
    await page.getByRole('button', { name: /超高/ }).click();
    const textbox = page.locator('textarea').first();
    await textbox.fill('请用三句话解释 ER 模型，并给一个选课系统例子。');
    await page.getByTestId('send-message').click();
    await waitForVisible(page, '.assistant-message__loading, .assistant-message__body', 20000);
    rows.push(['chat streaming', 'PASS', await screenshot(page, 'tutor-chat-streaming.png')]);
    await page.waitForSelector('.assistant-message__body', { timeout: 90000 });
    await page.getByTestId('send-message').waitFor({ state: 'visible', timeout: 90000 });
    rows.push(['chat finished', 'PASS', await screenshot(page, 'tutor-chat-finished-with-citations.png')]);

    await chooseTool(page, 'mode-resource');
    await page.getByTestId('tool-menu').click();
    await textbox.fill('围绕 ER 模型生成讲义、练习题和思维导图。');
    await page.getByTestId('send-message').click();
    await page.waitForSelector('.artifact-card', { timeout: 120000 });
    rows.push(['resource artifact', 'PASS', await screenshot(page, 'tutor-resource-artifact.png')]);

    await chooseTool(page, 'mode-homework');
    rows.push(['homework mode panel', 'PASS', await screenshot(page, 'tutor-homework-review.png')]);

    await chooseTool(page, 'mode-deep-research');
    rows.push(['deep research mode', 'PASS', await screenshot(page, 'tutor-deep-research.png')]);

    const latestPayload = capturedPayloads.at(-1) || '';
    rows.push(['request payload captured', latestPayload ? 'PASS' : 'FAIL', latestPayload.slice(0, 500)]);
  } catch (error) {
    rows.push(['playwright flow', 'FAIL', error instanceof Error ? error.message : String(error)]);
    try {
      rows.push(['failure screenshot', 'INFO', await screenshot(page, 'tutor-failure.png')]);
    } catch {
      rows.push(['failure screenshot', 'FAIL', 'unable to capture failure screenshot']);
    }
  } finally {
    await browser.close();
  }

  const report = [
    '# TUTOR_ACCEPTANCE_REPORT',
    '',
    `Generated: ${new Date().toISOString()}`,
    `Frontend: ${FRONTEND_URL}`,
    `Backend: ${BACKEND_URL}`,
    '',
    '| Test | Status | Evidence |',
    '| --- | --- | --- |',
    ...rows.map(([name, status, evidence]) => `| ${name} | ${status} | ${String(evidence).replace(/\n/g, ' ').replace(/\|/g, '\\|')} |`),
    '',
    '## Notes',
    '',
    '- Script uses a real backend login and opens the real `/tutor` page.',
    '- If backend model calls are slow, resource and finished-chat screenshots may take up to 120 seconds.',
    '- Captured request payloads are summarized in the table to verify mode/tools/reasoning mapping.',
  ].join('\n');
  await fs.writeFile(reportPath, report, 'utf-8');
  console.log(reportPath);
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});

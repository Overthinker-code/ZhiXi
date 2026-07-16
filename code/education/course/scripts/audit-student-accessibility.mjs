import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import parser from 'vue-eslint-parser';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const files = [
  'src/components/top-nav/ZyTopNav.vue',
  'src/layout/default-layout.vue',
  'src/views/chat/HomePage.vue',
  'src/components/chat/ChatLayout.vue',
  'src/components/chat/ChatSidebar.vue',
  'src/components/chat/ChatComposer.vue',
  'src/components/chat/AssistantMessage.vue',
  'src/components/chat/LiveProcessPanel.vue',
  'src/views/course/courselist/index.vue',
  'src/views/course/workspace/CourseWorkspaceLayout.vue',
  'src/views/course/workspace/CourseAgentWorkbench.vue',
  'src/views/course/workspace/CourseAnalyticsPage.vue',
  'src/views/course/workspace/CourseKnowledgePage.vue',
  'src/views/course/workspace/CourseResourcesPage.vue',
  'src/views/course/workspace/CourseTasksPage.vue',
  'src/views/resource-workshop/index.vue',
  'src/views/profile/learning-data/index.vue',
  'src/views/profile/user-info/index.vue',
  'src/components/float-ai/ClassroomQuickChat.vue',
  'src/components/float-ai/AgentRealtimeChat.vue',
];

const nativeInteractive = new Set(['button', 'input', 'select', 'textarea', 'summary', 'details']);
const knownInteractive = new Set([
  'a-button',
  'a-link',
  'a-input',
  'a-input-search',
  'a-select',
  'a-checkbox',
  'a-radio',
  'a-switch',
  'a-tab-pane',
  'router-link',
]);

const clickParityAllowlist = [
  {
    file: 'src/components/top-nav/ZyTopNav.vue',
    tag: 'a-doption',
    reason: 'Arco Dropdown option provides its own keyboard interaction semantics.',
  },
  {
    file: 'src/components/top-nav/ZyTopNav.vue',
    classToken: 'zy-mega-overlay',
    reason: 'Dismissal backdrop; all menu actions remain native buttons.',
  },
  {
    file: 'src/components/top-nav/ZyTopNav.vue',
    classToken: 'zy-mega-overlay__panel',
    reason: 'Propagation boundary, not an independent control.',
  },
  {
    file: 'src/views/chat/HomePage.vue',
    classToken: 'search-dialog-overlay',
    reason: 'Dismissal backdrop; dialog controls are independently keyboard reachable.',
  },
  {
    file: 'src/views/chat/HomePage.vue',
    classToken: 'search-dialog-container',
    reason: 'Propagation boundary, not an independent control.',
  },
  {
    file: 'src/views/course/workspace/CourseAgentWorkbench.vue',
    classToken: 'detail-drawer-mask',
    reason: 'Dismissal backdrop; drawer actions are native controls.',
  },
  {
    file: 'src/views/course/workspace/CourseAgentWorkbench.vue',
    classToken: 'agent-chat-dialog-mask',
    reason: 'Dismissal backdrop; the modal has a named Close button, Escape handling, and a focus trap.',
  },
  {
    file: 'src/views/course/workspace/CourseKnowledgePage.vue',
    classToken: 'graph-link-hit',
    reason: 'Transparent pointer hit area mirrors the adjacent named keyboard path.',
  },
  {
    file: 'src/views/resource-workshop/index.vue',
    classToken: 'artifact-preview-modal__backdrop',
    reason: 'Dismissal backdrop; the modal provides a named Close button and Escape handling.',
  },
];

function attrsOf(node) {
  return node.startTag?.attributes || [];
}

function staticAttr(node, name) {
  const attr = attrsOf(node).find(
    (item) => !item.directive && item.key?.name === name
  );
  return attr?.value?.value ?? (attr ? '' : null);
}

function hasBoundAttr(node, name) {
  return attrsOf(node).some(
    (item) =>
      item.directive &&
      item.key?.name?.name === 'bind' &&
      item.key?.argument?.type === 'VIdentifier' &&
      item.key.argument.name === name
  );
}

function hasEvent(node, name) {
  return attrsOf(node).some(
    (item) =>
      item.directive &&
      item.key?.name?.name === 'on' &&
      item.key?.argument?.type === 'VIdentifier' &&
      item.key.argument.name === name
  );
}

function hasAccessibleName(node) {
  if (
    staticAttr(node, 'aria-label') !== null ||
    hasBoundAttr(node, 'aria-label') ||
    staticAttr(node, 'title') !== null ||
    hasBoundAttr(node, 'title')
  ) {
    return true;
  }
  return (node.children || []).some((child) => {
    if (child.type === 'VText') return child.value.trim().length > 0;
    if (child.type === 'VExpressionContainer') return Boolean(child.expression);
    if (child.type === 'VElement') return hasAccessibleName(child);
    return false;
  });
}

function isInteractive(node) {
  const tag = node.rawName;
  if (nativeInteractive.has(tag) || knownInteractive.has(tag)) return true;
  if (tag === 'a' && (staticAttr(node, 'href') !== null || hasBoundAttr(node, 'href'))) return true;
  const role = staticAttr(node, 'role');
  return ['button', 'link', 'tab', 'menuitem', 'option', 'checkbox', 'radio', 'switch'].includes(role);
}

function lineOf(node) {
  return node.loc?.start?.line || 1;
}

function hasClassToken(node, token) {
  return (staticAttr(node, 'class') || '').split(/\s+/).includes(token);
}

function clickParityException(file, node) {
  return clickParityAllowlist.find(
    (entry) =>
      entry.file === file &&
      (!entry.tag || entry.tag === node.rawName) &&
      (!entry.classToken || hasClassToken(node, entry.classToken))
  );
}

function isWrappedByLabel(node) {
  let parent = node.parent;
  while (parent) {
    if (parent.type === 'VElement' && parent.rawName === 'label') return true;
    parent = parent.parent;
  }
  return false;
}

function walk(node, visit) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'VElement') visit(node);
  for (const key of ['children']) {
    for (const child of node[key] || []) walk(child, visit);
  }
}

const findings = [];
const allowlisted = [];
for (const relativeFile of files) {
  const absoluteFile = path.join(root, relativeFile);
  const source = fs.readFileSync(absoluteFile, 'utf8');
  const ast = parser.parse(source, {
    sourceType: 'module',
    ecmaVersion: 2022,
    parser: '@typescript-eslint/parser',
  });
  walk(ast.templateBody, (node) => {
    const tag = node.rawName;
    const line = lineOf(node);
    if (hasEvent(node, 'click') && !isInteractive(node)) {
      const exception = clickParityException(relativeFile, node);
      if (exception) {
        allowlisted.push({
          rule: 'click-keyboard-parity',
          file: relativeFile,
          line,
          tag,
          reason: exception.reason,
        });
        return;
      }
      const keyboard = ['keydown', 'keyup', 'keypress'].some((event) => hasEvent(node, event));
      const tabindex = staticAttr(node, 'tabindex') !== null || hasBoundAttr(node, 'tabindex');
      if (!keyboard || !tabindex) {
        findings.push({
          rule: 'click-keyboard-parity',
          severity: 'high',
          file: relativeFile,
          line,
          tag,
          detail: '非原生交互元素绑定了点击事件，但没有完整的键盘事件与 tabindex。',
        });
      }
    }
    if (tag === 'img' && staticAttr(node, 'alt') === null && !hasBoundAttr(node, 'alt')) {
      findings.push({
        rule: 'image-alt',
        severity: 'medium',
        file: relativeFile,
        line,
        tag,
        detail: '图片缺少 alt；装饰图片应使用空 alt，信息图片应提供等价文本。',
      });
    }
    if (['button', 'a-button', 'a-link'].includes(tag) && !hasAccessibleName(node)) {
      findings.push({
        rule: 'control-name',
        severity: 'high',
        file: relativeFile,
        line,
        tag,
        detail: '控件没有可确认的可访问名称。',
      });
    }
    if (['input', 'textarea'].includes(tag)) {
      const named =
        staticAttr(node, 'aria-label') !== null ||
        hasBoundAttr(node, 'aria-label') ||
        staticAttr(node, 'aria-labelledby') !== null ||
        hasBoundAttr(node, 'aria-labelledby') ||
        staticAttr(node, 'id') !== null ||
        hasBoundAttr(node, 'id') ||
        staticAttr(node, 'title') !== null ||
        isWrappedByLabel(node);
      if (!named && staticAttr(node, 'type') !== 'hidden' && staticAttr(node, 'type') !== 'file') {
        findings.push({
          rule: 'form-label',
          severity: 'high',
          file: relativeFile,
          line,
          tag,
          detail: '文本输入控件缺少可关联标签或 aria-label。',
        });
      }
    }
  });
}

const summary = findings.reduce((acc, item) => {
  acc[item.rule] = (acc[item.rule] || 0) + 1;
  return acc;
}, {});

console.log(
  JSON.stringify(
    {
      files: files.length,
      findings: findings.length,
      summary,
      items: findings,
      allowlisted: {
        count: allowlisted.length,
        items: allowlisted,
      },
    },
    null,
    2
  )
);

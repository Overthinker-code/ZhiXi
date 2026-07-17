<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import { Download, LoaderCircle, X } from 'lucide-vue-next';
  import { previewResource, type ResourceRecord } from '@/api/resources';

  const props = defineProps<{
    resource: ResourceRecord | null;
  }>();
  const emit = defineEmits<{
    close: [];
    download: [resource: ResourceRecord];
  }>();

  const panel = ref<HTMLElement | null>(null);
  const previewFrame = ref<HTMLIFrameElement | null>(null);
  const objectUrl = ref('');
  const state = ref<'loading' | 'ready' | 'error'>('loading');
  const mode = ref<'pdf' | 'image' | 'document'>('document');
  let previouslyFocused: HTMLElement | null = null;
  let requestVersion = 0;
  let previousBodyOverflow = '';
  let iframeWindow: Window | null = null;
  let windowKeyListenerActive = false;

  const title = computed(() => props.resource?.title || '资料预览');
  const fileName = computed(() => props.resource?.file_name || title.value);

  function revokePreviewUrl() {
    if (objectUrl.value) URL.revokeObjectURL(objectUrl.value);
    objectUrl.value = '';
  }

  function focusableElements() {
    if (!panel.value) return [];
    return Array.from(
      panel.value.querySelectorAll<HTMLElement>(
        'iframe, button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hasAttribute('hidden'));
  }

  function close() {
    emit('close');
  }

  function onWindowKeydown(event: KeyboardEvent) {
    if (event.key !== 'Escape') return;
    event.preventDefault();
    event.stopPropagation();
    close();
  }

  function addEscapeListeners() {
    if (!windowKeyListenerActive) {
      window.addEventListener('keydown', onWindowKeydown, true);
      windowKeyListenerActive = true;
    }
  }

  function removeEscapeListeners() {
    if (windowKeyListenerActive) {
      window.removeEventListener('keydown', onWindowKeydown, true);
      windowKeyListenerActive = false;
    }
    iframeWindow?.removeEventListener('keydown', onWindowKeydown, true);
    iframeWindow = null;
  }

  function bindFrameEscape() {
    iframeWindow?.removeEventListener('keydown', onWindowKeydown, true);
    try {
      iframeWindow = previewFrame.value?.contentWindow || null;
      iframeWindow?.addEventListener('keydown', onWindowKeydown, true);
    } catch {
      iframeWindow = null;
    }
  }

  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = focusableElements();
    if (!focusable.length) {
      event.preventDefault();
      panel.value?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  async function loadPreview(resource: ResourceRecord) {
    const currentVersion = ++requestVersion;
    revokePreviewUrl();
    state.value = 'loading';
    try {
      const response = await previewResource(resource.id);
      if (currentVersion !== requestVersion) return;
      const contentType = String(response.data.type || '').toLowerCase();
      mode.value = contentType.includes('pdf')
        ? 'pdf'
        : contentType.startsWith('image/')
        ? 'image'
        : 'document';
      objectUrl.value = URL.createObjectURL(response.data);
      state.value = 'ready';
    } catch {
      if (currentVersion === requestVersion) state.value = 'error';
    }
  }

  watch(
    () => props.resource,
    async (resource) => {
      requestVersion += 1;
      revokePreviewUrl();
      if (!resource) {
        removeEscapeListeners();
        document.body.style.overflow = previousBodyOverflow;
        const focusTarget = previouslyFocused;
        previouslyFocused = null;
        await nextTick();
        focusTarget?.focus();
        return;
      }
      previouslyFocused = document.activeElement as HTMLElement | null;
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      addEscapeListeners();
      await nextTick();
      const firstFocusable = focusableElements()[0];
      if (firstFocusable) firstFocusable.focus();
      else panel.value?.focus();
      void loadPreview(resource);
    }
  );

  onBeforeUnmount(() => {
    requestVersion += 1;
    revokePreviewUrl();
    removeEscapeListeners();
    document.body.style.overflow = previousBodyOverflow;
  });
</script>

<template>
  <Teleport to="body">
    <Transition name="resource-preview">
      <section
        v-if="resource"
        class="resource-preview"
        role="dialog"
        aria-modal="true"
        aria-labelledby="resource-preview-title"
        @keydown="onKeydown"
      >
        <button
          type="button"
          class="resource-preview__backdrop"
          aria-label="关闭资料预览"
          @click="close"
        />
        <article ref="panel" class="resource-preview__panel" tabindex="-1">
          <header>
            <div>
              <span>资料预览</span>
              <h2 id="resource-preview-title">{{ title }}</h2>
              <small>{{ fileName }}</small>
            </div>
            <button
              type="button"
              class="icon-button"
              aria-label="关闭资料预览"
              @click="close"
              ><X :size="19"
            /></button>
          </header>
          <div
            class="resource-preview__canvas"
            :class="`is-${mode}`"
            aria-live="polite"
          >
            <div v-if="state === 'loading'" class="resource-preview__state"
              ><LoaderCircle :size="22" class="spinning" /> 正在准备预览…</div
            >
            <div
              v-else-if="state === 'error'"
              class="resource-preview__state is-error"
            >
              <strong>暂时无法在线预览此资料</strong>
              <span>你仍可下载原文件后查看完整内容。</span>
            </div>
            <iframe
              v-else-if="mode === 'pdf' || mode === 'document'"
              ref="previewFrame"
              :src="objectUrl"
              :title="`${title}预览`"
              tabindex="0"
              :sandbox="mode === 'document' ? 'allow-same-origin' : undefined"
              @load="bindFrameEscape"
            />
            <img v-else :src="objectUrl" :alt="title" />
          </div>
          <footer>
            <button type="button" @click="close">关闭</button>
            <button
              type="button"
              class="primary"
              @click="emit('download', resource)"
              ><Download :size="15" /> 下载</button
            >
          </footer>
        </article>
      </section>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
  .resource-preview {
    position: fixed;
    inset: 0;
    z-index: 3200;
    display: grid;
    place-items: center;
    padding: 24px;
  }
  .resource-preview__backdrop {
    position: absolute;
    inset: 0;
    border: 0;
    background: rgba(15, 23, 42, 0.34);
    backdrop-filter: blur(2px);
  }
  .resource-preview__panel {
    position: relative;
    display: flex;
    width: min(1180px, calc(100vw - 32px));
    height: min(88vh, 940px);
    flex-direction: column;
    overflow: hidden;
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.28);
  }
  header,
  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 15px 20px;
    background: #fff;
  }
  header {
    border-bottom: 1px solid #eaecf0;
  }
  footer {
    border-top: 1px solid #eaecf0;
    justify-content: flex-end;
  }
  header span,
  header small {
    display: block;
    color: #667085;
    font-size: 12px;
  }
  header span {
    color: #4f46e5;
    font-weight: 750;
  }
  h2 {
    margin: 3px 0;
    color: #101828;
    font-size: 17px;
    line-height: 1.35;
  }
  .resource-preview__canvas {
    min-height: 0;
    flex: 1;
    overflow: hidden;
    padding: 24px;
    background: #edf0f4;
    scrollbar-gutter: stable;
  }
  .resource-preview__canvas iframe {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 0;
    margin: 0 auto;
    border: 0;
    background: #fff;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.12);
  }
  .resource-preview__canvas.is-pdf iframe {
    width: 100%;
    height: 100%;
    min-height: 0;
    box-shadow: none;
  }
  .resource-preview__canvas.is-image { overflow: auto; }
  .resource-preview__canvas img {
    display: block;
    max-width: 100%;
    max-height: calc(88vh - 150px);
    margin: 0 auto;
    object-fit: contain;
  }
  .resource-preview__state {
    display: grid;
    min-height: 100%;
    place-content: center;
    justify-items: center;
    gap: 10px;
    color: #667085;
    text-align: center;
  }
  .resource-preview__state.is-error strong {
    color: #344054;
  }
  .resource-preview__state.is-error span {
    font-size: 14px;
  }
  button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    min-height: 36px;
    padding: 0 14px;
    border: 1px solid #d0d5dd;
    border-radius: 9px;
    color: #344054;
    background: #fff;
    cursor: pointer;
  }
  .icon-button {
    width: 36px;
    padding: 0;
  }
  .primary {
    border-color: #4f46e5;
    color: #fff;
    background: #4f46e5;
  }
  .spinning {
    animation: spin 0.8s linear infinite;
  }
  .resource-preview-enter-active,
  .resource-preview-leave-active {
    transition: opacity 0.16s ease;
  }
  .resource-preview-enter-from,
  .resource-preview-leave-to {
    opacity: 0;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (max-width: 640px) {
    .resource-preview {
      padding: 10px;
    }
    .resource-preview__panel {
      width: 100%;
      height: 88vh;
    }
    .resource-preview__canvas {
      padding: 12px;
    }
    .resource-preview__canvas iframe {
      min-height: 500px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .spinning {
      animation: none;
    }
    .resource-preview-enter-active,
    .resource-preview-leave-active {
      transition: none;
    }
  }
</style>

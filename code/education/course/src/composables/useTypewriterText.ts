import { ref, onUnmounted } from 'vue';

/** 按字符逐步输出，用于课堂笔记等「文字动态生成」效果 */
export function useTypewriterText(charsPerSecond = 320) {
  const text = ref('');
  let timer: ReturnType<typeof setInterval> | null = null;

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function reset() {
    stop();
    text.value = '';
  }

  function start(full: string, onDone?: () => void) {
    reset();
    const ms = Math.max(6, Math.floor(1000 / Math.max(20, charsPerSecond)));
    let i = 0;
    timer = setInterval(() => {
      if (i >= full.length) {
        stop();
        onDone?.();
        return;
      }
      text.value += full[i];
      i += 1;
    }, ms);
  }

  onUnmounted(stop);

  return { text, start, reset, stop };
}

<script setup lang="ts">
  import { ref, watch } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useSettingStore } from '@/store/setting';
  import { fetchAiMetricsOverview, fetchLearningReport } from '@/api/rag';

  const props = defineProps<{
    visible: boolean;
  }>();

  const emit = defineEmits<{
    (e: 'update:visible', value: boolean): void;
  }>();

  const settingStore = useSettingStore();
  const metrics = ref<any | null>(null);
  const report = ref<any | null>(null);
  const loadingMetrics = ref(false);
  const loadingReport = ref(false);

  const close = () => emit('update:visible', false);

  async function loadMetrics() {
    loadingMetrics.value = true;
    try {
      metrics.value = await fetchAiMetricsOverview(7);
    } catch (error: any) {
      Message.warning(error?.message || '获取性能指标失败');
    } finally {
      loadingMetrics.value = false;
    }
  }

  async function loadReport() {
    loadingReport.value = true;
    try {
      report.value = await fetchLearningReport(true);
    } catch (error: any) {
      Message.warning(error?.message || '获取学习诊断失败');
    } finally {
      loadingReport.value = false;
    }
  }

  watch(
    () => props.visible,
    (visible) => {
      if (visible) {
        void loadMetrics();
      }
    }
  );
</script>

<template>
  <teleport to="body">
    <div v-if="visible" class="dev-overlay" @click.self="close">
      <aside class="dev-drawer">
        <div class="dev-header">
          <div>
            <h3>God Mode</h3>
            <p>开发者调试与演示控制面板</p>
          </div>
          <button type="button" class="close-btn" @click="close">×</button>
        </div>

        <section class="dev-section">
          <h4>链路控制</h4>
          <label class="dev-switch">
            <input v-model="settingStore.settings.debugMode" type="checkbox" />
            <span>启用调试模式</span>
          </label>
          <label class="dev-switch">
            <input v-model="settingStore.settings.forceCache" type="checkbox" />
            <span>强制走演示兜底回答</span>
          </label>
          <label class="dev-switch">
            <input
              v-model="settingStore.settings.simulateDigitalHumanSuccess"
              type="checkbox"
            />
            <span>模拟数字人成功（占位开关）</span>
          </label>
          <div class="dev-field">
            <span>强制路由专员</span>
            <select v-model="settingStore.settings.forceAgent">
              <option value="">自动路由</option>
              <option value="knowledge_mentor">学科讲师</option>
              <option value="planner">学习规划师</option>
              <option value="analyst">学习分析师</option>
              <option value="doc_researcher">文档研究员</option>
              <option value="quiz_master">测验官</option>
              <option value="code_tutor">代码导师</option>
            </select>
          </div>
        </section>

        <section class="dev-section">
          <div class="section-head">
            <h4>系统指标</h4>
            <button type="button" @click="loadMetrics">刷新</button>
          </div>
          <div v-if="loadingMetrics" class="dev-placeholder">加载中...</div>
          <div v-else-if="metrics" class="metrics-grid">
            <div class="metric-card">
              <span>请求数</span>
              <strong>{{ metrics.requests }}</strong>
            </div>
            <div class="metric-card">
              <span>平均 TTFT</span>
              <strong>{{ metrics.avg_ttft_ms }}ms</strong>
            </div>
            <div class="metric-card">
              <span>平均耗时</span>
              <strong>{{ metrics.avg_latency_ms }}ms</strong>
            </div>
            <div class="metric-card">
              <span>平均跳数</span>
              <strong>{{ metrics.avg_agent_hops }}</strong>
            </div>
          </div>
        </section>

        <section class="dev-section">
          <div class="section-head">
            <h4>学习诊断预览</h4>
            <button type="button" @click="loadReport">生成</button>
          </div>
          <div v-if="loadingReport" class="dev-placeholder">生成中...</div>
          <div v-else-if="report" class="report-card">
            <div class="report-title">{{ report.summary }}</div>
            <div class="report-line">
              <span>风险等级</span>
              <strong>{{ report.risk_level }}</strong>
            </div>
            <div class="report-tags">
              <span v-for="item in report.weak_points" :key="item">{{ item }}</span>
            </div>
            <ul class="report-actions">
              <li v-for="item in report.recommended_actions" :key="item">{{ item }}</li>
            </ul>
          </div>
        </section>
      </aside>
    </div>
  </teleport>
</template>

<style scoped lang="scss">
  .dev-overlay {
    position: fixed;
    inset: 0;
    z-index: 2200;
    background: rgba(15, 23, 42, 0.28);
    backdrop-filter: blur(6px);
    display: flex;
    justify-content: flex-end;
  }

  .dev-drawer {
    width: min(92vw, 420px);
    height: 100%;
    padding: 1rem 1rem 1.2rem;
    background: rgba(255, 255, 255, 0.94);
    border-left: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: -18px 0 44px rgba(15, 23, 42, 0.16);
    overflow-y: auto;
  }

  .dev-header,
  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .dev-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #0f172a;
  }

  .dev-header p {
    margin: 0.2rem 0 0;
    color: #64748b;
    font-size: 0.82rem;
  }

  .close-btn,
  .section-head button {
    border: none;
    border-radius: 10px;
    background: rgba(99, 102, 241, 0.1);
    color: #4338ca;
    cursor: pointer;
    padding: 0.4rem 0.7rem;
  }

  .dev-section {
    margin-top: 1rem;
    padding: 0.9rem;
    border-radius: 16px;
    background: rgba(248, 250, 252, 0.95);
    border: 1px solid rgba(99, 102, 241, 0.08);
  }

  .dev-switch,
  .dev-field {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-top: 0.7rem;
    color: #334155;
    font-size: 0.88rem;
  }

  .dev-field select {
    min-width: 138px;
    border-radius: 10px;
    border: 1px solid rgba(99, 102, 241, 0.16);
    padding: 0.45rem 0.6rem;
    background: #fff;
  }

  .dev-placeholder {
    margin-top: 0.7rem;
    color: #64748b;
    font-size: 0.84rem;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
    margin-top: 0.8rem;
  }

  .metric-card,
  .report-card {
    padding: 0.8rem;
    border-radius: 12px;
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.08);
  }

  .metric-card span {
    display: block;
    color: #64748b;
    font-size: 0.76rem;
  }

  .metric-card strong {
    display: block;
    margin-top: 0.35rem;
    color: #0f172a;
  }

  .report-title {
    color: #0f172a;
    font-size: 0.88rem;
    line-height: 1.55;
  }

  .report-line {
    display: flex;
    justify-content: space-between;
    margin-top: 0.7rem;
    color: #475569;
    font-size: 0.8rem;
  }

  .report-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.7rem;
  }

  .report-tags span {
    padding: 0.24rem 0.5rem;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.1);
    color: #1d4ed8;
    font-size: 0.74rem;
  }

  .report-actions {
    margin: 0.75rem 0 0;
    padding-left: 1rem;
    color: #334155;
    font-size: 0.82rem;
    line-height: 1.5;
  }
</style>

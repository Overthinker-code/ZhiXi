<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import {
    getWrongQuestionBook,
    setWrongQuestionFavorite,
    submitWrongQuestionBook,
    type QuizQuestionResult,
    type WrongQuestionItem,
    type WrongBookSubmitResult,
  } from '@/api/quiz';

  const router = useRouter();
  const loading = ref(true);
  const submitting = ref(false);
  const items = ref<WrongQuestionItem[]>([]);
  const answers = ref<Record<string, string>>({});
  const result = ref<WrongBookSubmitResult | null>(null);
  const activeSubject = ref('全部学科');

  const subjectOptions = computed(() => [
    '全部学科',
    ...Array.from(new Set(items.value.map((item) => item.subject || '未分类'))).sort(
      (a, b) => a.localeCompare(b, 'zh-CN')
    ),
  ]);
  const visibleItems = computed(() =>
    activeSubject.value === '全部学科'
      ? items.value
      : items.value.filter((item) => (item.subject || '未分类') === activeSubject.value)
  );
  const answeredCount = computed(
    () =>
      visibleItems.value.filter((item) => Boolean(answers.value[item.question.id]))
        .length
  );
  const resultByQuestion = computed<Record<string, QuizQuestionResult>>(() =>
    Object.fromEntries((result.value?.results || []).map((item) => [item.question_id, item]))
  );

  async function loadBook() {
    loading.value = true;
    try {
      items.value = (await getWrongQuestionBook()).data.items;
    } catch {
      Message.error('错题本加载失败');
    } finally {
      loading.value = false;
    }
  }

  async function removeItem(item: WrongQuestionItem) {
    try {
      await setWrongQuestionFavorite(item.question.id, false);
      items.value = items.value.filter((entry) => entry.id !== item.id);
      Message.success('已移出错题本');
    } catch {
      Message.error('操作失败');
    }
  }

  async function submit() {
    if (!visibleItems.value.length) return;
    if (answeredCount.value !== visibleItems.value.length) {
      Message.warning('请完成当前筛选下的全部错题后再提交');
      return;
    }
    const visibleAnswers = Object.fromEntries(
      visibleItems.value.map((item) => [
        item.question.id,
        answers.value[item.question.id],
      ])
    );
    submitting.value = true;
    try {
      result.value = (await submitWrongQuestionBook(visibleAnswers)).data;
      await loadBook();
      Message.success('错题重做结果已保存，并更新个人画像');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch {
      Message.error('错题提交失败');
    } finally {
      submitting.value = false;
    }
  }

  function redo() {
    answers.value = {};
    result.value = null;
  }

  onMounted(loadBook);
</script>

<template>
  <main class="wrong-book-page">
    <header>
      <button type="button" @click="router.push({ name: 'ResourceHub' })">← 资料中心</button>
      <div>
        <span>个人学习闭环</span>
        <h1>我的错题本</h1>
        <p>收藏的错题会保留错误次数；重做结果将继续更新个人画像。</p>
      </div>
      <div class="header-filter">
        <select v-model="activeSubject" aria-label="按学科筛选错题">
          <option v-for="subject in subjectOptions" :key="subject" :value="subject">{{ subject }}</option>
        </select>
        <strong>{{ visibleItems.length }} 题</strong>
      </div>
    </header>

    <section v-if="loading" class="empty">正在加载错题本…</section>
    <section v-else-if="!items.length" class="empty">
      <strong>错题本还是空的</strong>
      <p>完成题库后，可在答案解析下方收藏错题。</p>
      <button type="button" @click="router.push({ name: 'ResourceHub' })">去资料中心做题</button>
    </section>
    <template v-else>
      <section v-if="result" class="summary">
        <strong>本次重做正确率 {{ Math.round(result.score * 100) }}%</strong>
        <span>答对 {{ result.correct_count }} / {{ result.total_questions }}</span>
        <p v-if="result.wrong_knowledge_points.length">仍需巩固：{{ result.wrong_knowledge_points.join('、') }}</p>
        <p v-else>本次错题已全部答对，掌握状态已经更新。</p>
      </section>

      <section class="wrong-list">
        <article v-for="(item, index) in visibleItems" :key="item.id">
          <header>
            <span>{{ item.subject || '未分类' }} · 第 {{ index + 1 }} 题 · {{ item.question.knowledge_point }}</span>
            <div>
              <small>累计错误 {{ item.wrong_count }} 次</small>
              <em v-if="item.mastered">最近已答对</em>
              <button type="button" @click="removeItem(item)">移出错题本</button>
            </div>
          </header>
          <h2>{{ item.question.content }}</h2>
          <div class="options">
            <label
              v-for="option in item.question.options"
              :key="option.key"
              :class="{
                selected: answers[item.question.id] === option.key,
                correct: resultByQuestion[item.question.id]?.correct_answer === option.key,
                wrong: result && answers[item.question.id] === option.key && !resultByQuestion[item.question.id]?.is_correct,
              }"
            >
              <input
                v-model="answers[item.question.id]"
                type="radio"
                :name="item.question.id"
                :value="option.key"
                :disabled="Boolean(result)"
              />
              <b>{{ option.key }}</b><span>{{ option.text }}</span>
            </label>
          </div>
          <div v-if="resultByQuestion[item.question.id]" class="analysis">
            <strong>{{ resultByQuestion[item.question.id].is_correct ? '回答正确' : '回答错误' }}</strong>
            <p>正确答案：{{ resultByQuestion[item.question.id].correct_answer }}</p>
            <p>{{ resultByQuestion[item.question.id].analysis }}</p>
          </div>
          <small class="source">来源：{{ item.resource_title }}</small>
        </article>
      </section>

      <footer>
        <span>已完成 {{ answeredCount }} / {{ visibleItems.length }} 题</span>
        <button v-if="!result" type="button" :disabled="submitting" @click="submit">
          {{ submitting ? '正在评估…' : '提交错题重做' }}
        </button>
        <button v-else type="button" @click="redo">再做一遍</button>
      </footer>
    </template>
  </main>
</template>

<style scoped>
  .wrong-book-page { min-height: 100vh; padding: 32px clamp(18px, 5vw, 76px) 100px; background: #f6f7fb; color: #172033; }
  button { border: 0; cursor: pointer; }
  .wrong-book-page > header { display: grid; grid-template-columns: auto 1fr auto; gap: 24px; align-items: center; max-width: 980px; margin: 0 auto 22px; padding: 25px 30px; border-radius: 20px; background: #fff; }
  .wrong-book-page > header button { color: #5b61e6; background: transparent; }
  h1 { margin: 5px 0; } p { margin: 4px 0; } header span, header p { color: #7a8194; }
  .empty { display: grid; place-items: center; gap: 12px; min-height: 55vh; }
  .empty button, footer button { padding: 11px 24px; border-radius: 10px; background: #5b61e6; color: #fff; }
  .summary { max-width: 920px; margin: 0 auto 18px; padding: 18px 30px; border-radius: 15px; background: #eef0ff; color: #4349ad; }
  .summary span { margin-left: 20px; }
  .wrong-list { display: grid; gap: 18px; max-width: 980px; margin: auto; }
  .wrong-list > article { padding: 26px 30px; border: 1px solid #e5e7f0; border-radius: 18px; background: #fff; }
  .wrong-list article > header { display: flex; justify-content: space-between; color: #6269d9; }
  .wrong-list header div { display: flex; gap: 12px; align-items: center; }
  .wrong-list header em { color: #2e9a69; font-style: normal; }
  .wrong-list header button { color: #d65a5a; background: transparent; }
  h2 { margin: 16px 0 20px; font-size: 18px; line-height: 1.65; }
  .options { display: grid; gap: 10px; }
  .options label { display: grid; grid-template-columns: 22px 30px 1fr; padding: 13px 16px; border: 1px solid #e3e5ed; border-radius: 11px; }
  .options label.selected { border-color: #747aeb; background: #f4f5ff; }
  .options label.correct { border-color: #34a875; background: #eefaf4; }
  .options label.wrong { border-color: #e46666; background: #fff2f2; }
  .analysis { margin-top: 16px; padding: 14px 17px; border-radius: 11px; background: #f7f8fb; }
  .analysis p { margin-top: 6px; }
  .source { display: block; margin-top: 14px; color: #9298a8; }
  footer { position: fixed; right: 0; bottom: 0; left: 0; display: flex; justify-content: flex-end; align-items: center; gap: 24px; padding: 15px clamp(18px, 5vw, 76px); border-top: 1px solid #e5e7ef; background: rgba(255,255,255,.96); }
</style>

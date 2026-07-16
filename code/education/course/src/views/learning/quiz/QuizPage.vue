<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import {
    getQuizAttempt,
    getQuizAttempts,
    getQuiz,
    setWrongQuestionFavorite,
    submitQuiz,
    type QuizAttemptSummary,
    type QuizResource,
    type QuizSubmitResult,
  } from '@/api/quiz';

  const route = useRoute();
  const router = useRouter();
  const loading = ref(true);
  const submitting = ref(false);
  const quiz = ref<QuizResource | null>(null);
  const answers = ref<Record<string, string>>({});
  const result = ref<QuizSubmitResult | null>(null);
  const attempts = ref<QuizAttemptSummary[]>([]);
  const viewMode = ref<'choice' | 'answering' | 'review'>('answering');
  const savingWrong = ref<string | null>(null);

  const resourceId = computed(() => String(route.params.resourceId || ''));
  const answeredCount = computed(() => Object.values(answers.value).filter(Boolean).length);
  const resultByQuestion = computed(() =>
    Object.fromEntries((result.value?.results || []).map((item) => [item.question_id, item]))
  );
  const scoreText = computed(() => `${Math.round((result.value?.score || 0) * 100)}%`);

  async function loadQuiz() {
    loading.value = true;
    try {
      const [quizResponse, attemptsResponse] = await Promise.all([
        getQuiz(resourceId.value),
        getQuizAttempts(resourceId.value),
      ]);
      quiz.value = quizResponse.data;
      attempts.value = attemptsResponse.data;
      viewMode.value = attempts.value.length ? 'choice' : 'answering';
    } catch {
      Message.error('题目加载失败或该资源不存在');
    } finally {
      loading.value = false;
    }
  }

  function startRedo() {
    answers.value = {};
    result.value = null;
    viewMode.value = 'answering';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function reviewAttempt(attemptId: string) {
    loading.value = true;
    try {
      const response = await getQuizAttempt(attemptId);
      result.value = response.data;
      answers.value = Object.fromEntries(
        response.data.results.map((item) => [item.question_id, item.selected_answer])
      );
      viewMode.value = 'review';
    } catch {
      Message.error('答题记录加载失败');
    } finally {
      loading.value = false;
    }
  }

  async function toggleWrongQuestion(questionId: string) {
    const item = resultByQuestion.value[questionId];
    if (!item || item.is_correct) return;
    savingWrong.value = questionId;
    const next = !item.saved_to_wrong_book;
    try {
      await setWrongQuestionFavorite(questionId, next);
      item.saved_to_wrong_book = next;
      Message.success(next ? '已收藏到错题本' : '已从错题本移除');
    } catch {
      Message.error('错题本更新失败');
    } finally {
      savingWrong.value = null;
    }
  }

  async function handleSubmit() {
    if (!quiz.value || result.value) return;
    if (answeredCount.value < quiz.value.questions.length) {
      Message.warning('请完成全部题目后再提交');
      return;
    }
    submitting.value = true;
    try {
      const response = await submitQuiz(resourceId.value, answers.value);
      result.value = response.data;
      attempts.value = (await getQuizAttempts(resourceId.value)).data;
      viewMode.value = 'review';
      Message.success('已保存答题记录；错题已自动加入错题本并更新个人画像');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch {
      Message.error('提交失败，请稍后重试');
    } finally {
      submitting.value = false;
    }
  }

  onMounted(loadQuiz);
</script>

<template>
  <main class="quiz-page">
    <section v-if="loading" class="quiz-state">正在加载题目…</section>
    <section v-else-if="!quiz" class="quiz-state">
      <strong>未找到这份练习</strong>
      <button type="button" @click="router.push({ name: 'ResourceHub' })">返回资料中心</button>
    </section>
    <template v-else>
      <header class="quiz-header">
        <div class="header-links">
          <button type="button" class="back" @click="router.push({ name: 'ResourceHub' })">← 资料中心</button>
          <button type="button" class="back" @click="router.push({ name: 'WrongQuestionBook' })">错题本</button>
        </div>
        <div>
          <span>AI 专项练习</span>
          <h1>{{ quiz.title }}</h1>
          <p>{{ quiz.knowledge_point }} · 共 {{ quiz.questions.length }} 题</p>
        </div>
        <div v-if="result" class="score">
          <strong>{{ scoreText }}</strong>
          <span>答对 {{ result.correct_count }}/{{ result.total_questions }}</span>
        </div>
        <div v-else class="progress">
          <strong>{{ answeredCount }}/{{ quiz.questions.length }}</strong>
          <span>已作答</span>
        </div>
      </header>

      <section v-if="viewMode === 'choice'" class="attempt-choice">
        <div>
          <span>检测到 {{ attempts.length }} 次答题记录</span>
          <h2>继续查看上次结果，还是重新做一遍？</h2>
          <p>重新做题会创建一条新的记录，原来的记录不会被覆盖。</p>
        </div>
        <div class="attempt-choice__actions">
          <button type="button" @click="reviewAttempt(attempts[0].attempt_id)">查看上次记录</button>
          <button type="button" class="primary" @click="startRedo">重新做题</button>
        </div>
        <div class="attempt-history">
          <button
            v-for="(attempt, index) in attempts.slice(0, 8)"
            :key="attempt.attempt_id"
            type="button"
            @click="reviewAttempt(attempt.attempt_id)"
          >
            <strong>第 {{ attempts.length - index }} 次</strong>
            <span>{{ new Date(attempt.created_time).toLocaleString('zh-CN') }}</span>
            <b>{{ Math.round(attempt.score * 100) }}%</b>
          </button>
        </div>
      </section>

      <section v-if="viewMode === 'review' && result" class="feedback">
        <strong>本次评估已进入学习闭环</strong>
        <p v-if="result.wrong_knowledge_points.length">
          建议重点巩固：{{ result.wrong_knowledge_points.join('、') }}。错题已自动加入错题本，资料推荐与学习路径已据此调整。
        </p>
        <p v-else>全部答对，当前知识点掌握表现良好，画像已记录本次结果。</p>
      </section>

      <section v-if="viewMode !== 'choice'" class="question-list">
        <article v-for="(question, index) in quiz.questions" :key="question.id" class="question-card">
          <header>
            <span>第 {{ index + 1 }} 题</span>
            <small>{{ question.knowledge_point }}</small>
          </header>
          <h2>{{ question.content }}</h2>
          <div class="options">
            <label
              v-for="option in question.options"
              :key="option.key"
              :class="{
                selected: answers[question.id] === option.key,
                correct: result && resultByQuestion[question.id]?.correct_answer === option.key,
                wrong:
                  result &&
                  answers[question.id] === option.key &&
                  !resultByQuestion[question.id]?.is_correct,
              }"
            >
              <input
                v-model="answers[question.id]"
                type="radio"
                :name="question.id"
                :value="option.key"
                :disabled="Boolean(result)"
              />
              <b>{{ option.key }}</b>
              <span>{{ option.text }}</span>
            </label>
          </div>
          <div v-if="resultByQuestion[question.id]" class="analysis">
            <strong>{{ resultByQuestion[question.id]?.is_correct ? '回答正确' : '回答错误' }}</strong>
            <p>正确答案：{{ resultByQuestion[question.id]?.correct_answer }}</p>
            <p>{{ resultByQuestion[question.id]?.analysis }}</p>
            <button
              v-if="!resultByQuestion[question.id]?.is_correct"
              type="button"
              class="wrong-book-button"
              :disabled="savingWrong === question.id"
              @click="toggleWrongQuestion(question.id)"
            >
              {{ resultByQuestion[question.id]?.saved_to_wrong_book ? '移出错题本' : '收藏到错题本' }}
            </button>
          </div>
        </article>
      </section>

      <footer v-if="viewMode !== 'choice'" class="quiz-footer">
        <span v-if="!result">已完成 {{ answeredCount }} / {{ quiz.questions.length }} 题</span>
        <span v-else>答题结果已保存</span>
        <button v-if="!result" type="button" :disabled="submitting" @click="handleSubmit">
          {{ submitting ? '正在评估…' : '提交答案' }}
        </button>
        <template v-else>
          <button type="button" class="secondary" @click="viewMode = 'choice'">答题记录</button>
          <button type="button" @click="startRedo">重新做题</button>
        </template>
      </footer>
    </template>
  </main>
</template>

<style scoped>
  .quiz-page { min-height: 100vh; padding: 32px clamp(18px, 5vw, 76px) 110px; background: #f6f7fb; color: #172033; }
  .quiz-state { display: grid; place-items: center; gap: 18px; min-height: 60vh; }
  button { border: 0; cursor: pointer; }
  .quiz-header { display: grid; grid-template-columns: auto 1fr auto; gap: 24px; align-items: center; max-width: 980px; margin: 0 auto 24px; padding: 26px 30px; border: 1px solid #e7e9f3; border-radius: 20px; background: #fff; }
  .back { align-self: start; padding: 8px 0; color: #5b61e6; background: transparent; }
  .header-links { display: grid; gap: 4px; align-self: start; }
  .quiz-header h1 { margin: 5px 0 6px; font-size: 25px; }
  .quiz-header p, .quiz-header span { margin: 0; color: #7a8194; }
  .score, .progress { display: grid; min-width: 100px; text-align: right; }
  .score strong, .progress strong { font-size: 30px; color: #5b61e6; }
  .feedback { max-width: 920px; margin: 0 auto 20px; padding: 18px 30px; border-radius: 16px; background: #eef0ff; color: #3b419f; }
  .feedback p { margin: 7px 0 0; }
  .attempt-choice { max-width: 920px; margin: 0 auto; padding: 30px; border: 1px solid #e4e6f4; border-radius: 18px; background: #fff; }
  .attempt-choice h2 { margin: 8px 0; }
  .attempt-choice p, .attempt-choice span { color: #7a8194; }
  .attempt-choice__actions { display: flex; gap: 12px; margin: 22px 0; }
  .attempt-choice__actions button { padding: 11px 22px; border-radius: 10px; background: #eef0ff; color: #4f55c8; }
  .attempt-choice__actions .primary { background: #5b61e6; color: #fff; }
  .attempt-history { display: grid; gap: 8px; }
  .attempt-history button { display: grid; grid-template-columns: 80px 1fr auto; gap: 16px; padding: 12px 15px; border-radius: 10px; background: #f7f8fb; text-align: left; }
  .attempt-history b { color: #5b61e6; }
  .question-list { display: grid; gap: 18px; max-width: 980px; margin: auto; }
  .question-card { padding: 26px 30px; border: 1px solid #e7e9f3; border-radius: 18px; background: #fff; }
  .question-card > header { display: flex; justify-content: space-between; color: #656de0; }
  .question-card h2 { margin: 16px 0 20px; font-size: 18px; line-height: 1.7; }
  .options { display: grid; gap: 10px; }
  .options label { display: grid; grid-template-columns: 22px 30px 1fr; align-items: center; padding: 13px 16px; border: 1px solid #e4e6ee; border-radius: 12px; cursor: pointer; transition: .15s ease; }
  .options label:hover, .options label.selected { border-color: #777ded; background: #f5f5ff; }
  .options label.correct { border-color: #34a875; background: #eefaf4; }
  .options label.wrong { border-color: #e46666; background: #fff2f2; }
  .analysis { margin-top: 18px; padding: 15px 18px; border-radius: 12px; background: #f7f8fb; line-height: 1.7; }
  .analysis p { margin: 4px 0; }
  .wrong-book-button { margin-top: 8px; padding: 8px 14px; border-radius: 8px; background: #fff0f0; color: #d94b4b; }
  .quiz-footer { position: fixed; right: 0; bottom: 0; left: 0; z-index: 10; display: flex; justify-content: flex-end; align-items: center; gap: 24px; padding: 15px clamp(18px, 5vw, 76px); border-top: 1px solid #e5e7ef; background: rgba(255,255,255,.96); }
  .quiz-footer button, .quiz-state button { padding: 11px 28px; border-radius: 10px; background: #5b61e6; color: #fff; }
  .quiz-footer button:disabled { cursor: wait; opacity: .65; }
  .quiz-footer .secondary { background: #eef0ff; color: #4f55c8; }
  @media (max-width: 720px) { .quiz-header { grid-template-columns: 1fr auto; } .back { grid-column: 1 / -1; } .quiz-header, .question-card { padding: 20px; } }
</style>

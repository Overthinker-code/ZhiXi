<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import {
    generateWrongQuestionPractice,
    getWrongQuestionBook,
    setWrongQuestionFavorite,
    submitWrongQuestionBook,
    type QuizQuestionResult,
    type WrongBookSubmitResult,
    type WrongQuestionItem,
  } from '@/api/quiz';

  interface SubjectNotebook {
    subject: string;
    items: WrongQuestionItem[];
    totalWrong: number;
    masteredCount: number;
    latestTime: string;
    weakPoints: string[];
    color: string;
  }

  const router = useRouter();
  const loading = ref(true);
  const submitting = ref(false);
  const generating = ref(false);
  const items = ref<WrongQuestionItem[]>([]);
  const answers = ref<Record<string, string>>({});
  const result = ref<WrongBookSubmitResult | null>(null);
  const activeSubject = ref<string>('');

  const bookColors = ['#6d6cf6', '#20a87b', '#f59f36', '#f06a7a', '#4b9be7', '#9b6cf6'];

  const notebooks = computed<SubjectNotebook[]>(() => {
    const grouped = new Map<string, WrongQuestionItem[]>();
    items.value.forEach((item) => {
      const subject = (item.subject || '未分类学科').trim() || '未分类学科';
      grouped.set(subject, [...(grouped.get(subject) || []), item]);
    });
    return Array.from(grouped.entries())
      .map(([subject, list], index) => {
        const weakPoints = Array.from(
          new Set(list.map((item) => item.question.knowledge_point).filter(Boolean))
        ).slice(0, 5);
        return {
          subject,
          items: list,
          totalWrong: list.reduce((sum, item) => sum + item.wrong_count, 0),
          masteredCount: list.filter((item) => item.mastered).length,
          latestTime: list[0]?.updated_time || '',
          weakPoints,
          color: bookColors[index % bookColors.length],
        };
      })
      .sort((a, b) => b.items.length - a.items.length || a.subject.localeCompare(b.subject, 'zh-CN'));
  });

  const activeBook = computed(() =>
    notebooks.value.find((book) => book.subject === activeSubject.value) || null
  );
  const visibleItems = computed(() => activeBook.value?.items || []);
  const answeredCount = computed(
    () => visibleItems.value.filter((item) => Boolean(answers.value[item.question.id])).length
  );
  const resultByQuestion = computed<Record<string, QuizQuestionResult>>(() =>
    Object.fromEntries((result.value?.results || []).map((item) => [item.question_id, item]))
  );
  async function loadBook() {
    loading.value = true;
    try {
      const bookResponse = await getWrongQuestionBook();
      items.value = bookResponse.data.items;
    } catch {
      Message.error('错题本加载失败');
    } finally {
      loading.value = false;
    }
  }

  function openBook(subject: string) {
    activeSubject.value = subject;
    answers.value = {};
    result.value = null;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function closeBook() {
    activeSubject.value = '';
    answers.value = {};
    result.value = null;
  }

  async function removeItem(item: WrongQuestionItem) {
    try {
      await setWrongQuestionFavorite(item.question.id, false);
      items.value = items.value.filter((entry) => entry.id !== item.id);
      if (activeBook.value && !visibleItems.value.length) closeBook();
      Message.success('已移出错题本');
    } catch {
      Message.error('操作失败');
    }
  }

  async function submit() {
    if (!visibleItems.value.length) return;
    if (answeredCount.value !== visibleItems.value.length) {
      Message.warning('请完成当前本子里的全部错题后再提交');
      return;
    }
    const visibleAnswers = Object.fromEntries(
      visibleItems.value.map((item) => [item.question.id, answers.value[item.question.id]])
    );
    submitting.value = true;
    try {
      result.value = (await submitWrongQuestionBook(visibleAnswers)).data;
      await loadBook();
      Message.success('错题重做结果已保存，并继续更新个人画像');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch {
      Message.error('错题提交失败');
    } finally {
      submitting.value = false;
    }
  }

  async function generatePractice() {
    if (!activeBook.value) return;
    generating.value = true;
    try {
      const response = await generateWrongQuestionPractice({
        subject: activeBook.value.subject,
        question_ids: activeBook.value.items.map((item) => item.question.id),
        count: Math.min(10, Math.max(6, activeBook.value.items.length + 2)),
        difficulty: 'standard',
      });
      Message.success('已根据这本错题生成专项练习');
      router.push({ name: 'QuizPage', params: { resourceId: response.data.resource_id } });
    } catch (error: any) {
      Message.error(error?.response?.data?.detail || '专项练习生成失败，请检查后端 AI 配置');
    } finally {
      generating.value = false;
    }
  }

  function redo() {
    answers.value = {};
    result.value = null;
  }

  function formatDate(value: string) {
    if (!value) return '暂无记录';
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  onMounted(loadBook);
</script>

<template>
  <main class="wrong-book-page">
    <header class="page-hero">
      <button type="button" class="back-link" @click="router.push({ name: 'ResourceHub' })">
        ← 资料中心
      </button>
      <div>
        <span>个人学习闭环</span>
        <h1>我的错题本</h1>
        <p>按学科整理成一本本小册子；打开后可以重做错题，也可以让 AI 生成同类专项练习。</p>
      </div>
      <div class="hero-stat">
        <strong>{{ items.length }}</strong>
        <span>已收藏错题</span>
      </div>
    </header>

    <section v-if="loading" class="empty">正在加载错题本…</section>
    <section v-else-if="!items.length" class="empty">
      <strong>错题本还是空的</strong>
      <p>完成题库后，可以在答案解析下方收藏错题。</p>
      <button type="button" @click="router.push({ name: 'ResourceHub' })">去资料中心做题</button>
    </section>

    <template v-else-if="!activeBook">
      <section class="bookshelf-head">
        <div>
          <span>学科书架</span>
          <h2>一个学科，就是一本错题本</h2>
        </div>
        <p>打开本子后，练习 Agent 会结合错题频次、知识点标签和学生画像，帮你继续生成对应练习。</p>
      </section>

      <section class="notebook-grid">
        <article
          v-for="book in notebooks"
          :key="book.subject"
          class="notebook"
          :style="{ '--book-color': book.color }"
          @click="openBook(book.subject)"
        >
          <div class="book-cover">
            <span class="book-band" />
            <div class="book-label">
              <small>错题本</small>
              <strong>{{ book.subject }}</strong>
            </div>
            <p>{{ book.items.length }} 题 · 累计错 {{ book.totalWrong }} 次</p>
          </div>
          <div class="book-pages">
            <span>最近更新 {{ formatDate(book.latestTime) }}</span>
            <em>{{ book.masteredCount }} 题最近已答对</em>
            <div class="tags">
              <b v-for="point in book.weakPoints.slice(0, 3)" :key="point">{{ point }}</b>
            </div>
          </div>
        </article>
      </section>
    </template>

    <template v-else>
      <section class="opened-book">
        <aside class="opened-cover" :style="{ '--book-color': activeBook.color }">
          <button type="button" class="back-link" @click="closeBook">← 返回书架</button>
          <span>当前本子</span>
          <h2>{{ activeBook.subject }}</h2>
          <p>{{ activeBook.items.length }} 道错题 · 累计错误 {{ activeBook.totalWrong }} 次</p>
          <button type="button" class="practice-btn" :disabled="generating" @click="generatePractice">
            {{ generating ? '小智正在出题…' : '根据这本错题生成练习' }}
          </button>
        </aside>

        <div class="opened-content">
          <section v-if="result" class="summary">
            <strong>本次重做正确率 {{ Math.round(result.score * 100) }}%</strong>
            <span>答对 {{ result.correct_count }} / {{ result.total_questions }}</span>
            <p v-if="result.wrong_knowledge_points.length">
              仍需巩固：{{ result.wrong_knowledge_points.join('、') }}
            </p>
            <p v-else>这本错题已全部答对，掌握状态会继续写入个人画像。</p>
          </section>

          <section class="wrong-list">
            <article v-for="(item, index) in visibleItems" :key="item.id">
              <header>
                <span>第 {{ index + 1 }} 题 · {{ item.question.knowledge_point }}</span>
                <div>
                  <small>累计错误 {{ item.wrong_count }} 次</small>
                  <em v-if="item.mastered">最近已答对</em>
                  <button type="button" @click="removeItem(item)">移出错题本</button>
                </div>
              </header>
              <h3>{{ item.question.content }}</h3>
              <div class="options">
                <label
                  v-for="option in item.question.options"
                  :key="option.key"
                  :class="{
                    selected: answers[item.question.id] === option.key,
                    correct: resultByQuestion[item.question.id]?.correct_answer === option.key,
                    wrong:
                      result &&
                      answers[item.question.id] === option.key &&
                      !resultByQuestion[item.question.id]?.is_correct,
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
        </div>
      </section>

      <footer>
        <span>已完成 {{ answeredCount }} / {{ visibleItems.length }} 题</span>
        <button v-if="!result" type="button" :disabled="submitting" @click="submit">
          {{ submitting ? '正在评估…' : '提交本子重做' }}
        </button>
        <button v-else type="button" @click="redo">再做一遍</button>
      </footer>
    </template>
  </main>
</template>

<style scoped>
  .wrong-book-page {
    min-height: 100vh;
    padding: 32px clamp(18px, 5vw, 76px) 112px;
    background:
      radial-gradient(circle at 12% 8%, rgba(109, 108, 246, 0.11), transparent 32%),
      #f6f7fb;
    color: #172033;
  }
  button { border: 0; cursor: pointer; }
  .page-hero {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 24px;
    align-items: center;
    max-width: 1080px;
    margin: 0 auto 18px;
    padding: 25px 30px;
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 18px 45px rgba(33, 42, 76, 0.06);
  }
  .back-link { color: #5b61e6; background: transparent; }
  .page-hero h1, .bookshelf-head h2, .opened-cover h2 { margin: 5px 0; }
  .page-hero span, .page-hero p, .bookshelf-head span, .bookshelf-head p { color: #7a8194; }
  .hero-stat { display: grid; text-align: right; }
  .hero-stat strong { font-size: 34px; color: #5b61e6; }
  .empty { display: grid; place-items: center; gap: 12px; min-height: 45vh; text-align: center; }
  .empty button, footer button, .practice-btn {
    padding: 11px 24px;
    border-radius: 12px;
    background: #5b61e6;
    color: #fff;
  }
  .bookshelf-head {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    max-width: 1080px;
    margin: 0 auto 16px;
    padding: 0 4px;
  }
  .bookshelf-head p { max-width: 520px; }
  .notebook-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 22px;
    max-width: 1080px;
    margin: auto;
  }
  .notebook {
    display: grid;
    grid-template-columns: 110px 1fr;
    min-height: 190px;
    border-radius: 22px;
    background: #fff;
    box-shadow: 0 18px 40px rgba(24, 32, 62, 0.08);
    overflow: hidden;
    transition: transform .18s ease, box-shadow .18s ease;
  }
  .notebook:hover { transform: translateY(-5px); box-shadow: 0 22px 48px rgba(24, 32, 62, 0.12); }
  .book-cover {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 20px 15px;
    background: var(--book-color);
    color: #fff;
  }
  .book-band { position: absolute; inset: 0 auto 0 18px; width: 10px; background: rgba(255,255,255,.22); }
  .book-label { position: relative; display: grid; gap: 8px; }
  .book-label small { opacity: .75; }
  .book-label strong { font-size: 22px; writing-mode: vertical-rl; letter-spacing: 3px; }
  .book-cover p { position: relative; margin: 0; font-size: 13px; opacity: .88; }
  .book-pages { display: grid; align-content: center; gap: 10px; padding: 20px; color: #6f7688; }
  .book-pages em { color: #239b6e; font-style: normal; }
  .tags { display: flex; flex-wrap: wrap; gap: 7px; }
  .tags b { padding: 5px 8px; border-radius: 999px; background: #f1f3ff; color: #575ed7; font-size: 12px; font-weight: 600; }
  .opened-book {
    display: grid;
    grid-template-columns: minmax(230px, 300px) 1fr;
    gap: 22px;
    max-width: 1180px;
    margin: auto;
  }
  .opened-cover {
    position: sticky;
    top: 22px;
    align-self: start;
    min-height: 380px;
    padding: 25px;
    border-radius: 24px;
    background: linear-gradient(145deg, var(--book-color), #242a67);
    color: #fff;
    box-shadow: 0 24px 55px rgba(24, 32, 62, 0.16);
  }
  .opened-cover .back-link { color: rgba(255,255,255,.88); }
  .opened-cover span, .opened-cover p { color: rgba(255,255,255,.78); }
  .practice-btn { width: 100%; margin-top: 26px; background: #fff; color: #383fb6; font-weight: 700; }
  .practice-btn:disabled { cursor: wait; opacity: .75; }
  .opened-content { min-width: 0; }
  .summary { margin: 0 0 18px; padding: 18px 30px; border-radius: 15px; background: #eef0ff; color: #4349ad; }
  .summary span { margin-left: 20px; }
  .wrong-list { display: grid; gap: 18px; }
  .wrong-list > article { padding: 26px 30px; border: 1px solid #e5e7f0; border-radius: 18px; background: #fff; }
  .wrong-list article > header { display: flex; justify-content: space-between; gap: 16px; color: #6269d9; }
  .wrong-list header div { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: flex-end; }
  .wrong-list header em { color: #2e9a69; font-style: normal; }
  .wrong-list header button { color: #d65a5a; background: transparent; }
  h3 { margin: 16px 0 20px; font-size: 18px; line-height: 1.65; }
  .options { display: grid; gap: 10px; }
  .options label {
    display: grid;
    grid-template-columns: 22px 30px 1fr;
    align-items: center;
    padding: 13px 16px;
    border: 1px solid #e3e5ed;
    border-radius: 11px;
    cursor: pointer;
  }
  .options label.selected { border-color: #747aeb; background: #f4f5ff; }
  .options label.correct { border-color: #34a875; background: #eefaf4; }
  .options label.wrong { border-color: #e46666; background: #fff2f2; }
  .analysis { margin-top: 16px; padding: 14px 17px; border-radius: 11px; background: #f7f8fb; }
  .analysis p { margin-top: 6px; }
  .source { display: block; margin-top: 14px; color: #9298a8; }
  footer {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 24px;
    padding: 15px clamp(18px, 5vw, 76px);
    border-top: 1px solid #e5e7ef;
    background: rgba(255,255,255,.96);
  }
  @media (max-width: 860px) {
    .page-hero, .opened-book { grid-template-columns: 1fr; }
    .hero-stat { text-align: left; }
    .opened-cover { position: static; min-height: auto; }
    .notebook { grid-template-columns: 95px 1fr; }
    .book-label strong { writing-mode: initial; letter-spacing: 0; }
  }
</style>

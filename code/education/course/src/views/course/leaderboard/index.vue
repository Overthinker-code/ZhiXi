<template>
  <div class="leaderboard-page">
    <Breadcrumb :items="['menu.course', 'menu.course.leaderboard']" />

    <!-- 筛选与操作栏 -->
    <a-card class="filter-card" :bordered="false">
      <div class="filter-bar">
        <a-space :size="12">
          <a-select
            v-model="filters.courseId"
            placeholder="选择课程"
            style="width: 200px"
            allow-clear
            @change="fetchData"
          >
            <a-option v-for="c in courses" :key="c.id" :value="c.id">
              {{ c.name }}
            </a-option>
          </a-select>

          <a-select
            v-model="filters.taskId"
            placeholder="选择作业"
            style="width: 200px"
            allow-clear
            @change="fetchData"
          >
            <a-option v-for="t in tasks" :key="t.id" :value="t.id">
              {{ t.name }}
            </a-option>
          </a-select>

          <a-select
            v-model="filters.sortBy"
            style="width: 130px"
            @change="fetchData"
          >
            <a-option value="score">按成绩排序</a-option>
            <a-option value="submit_time">按提交时间</a-option>
            <a-option value="completion_rate">按完成率</a-option>
          </a-select>
        </a-space>

        <a-space :size="10">
          <a-radio-group v-model="filters.scope" type="button" @change="fetchData">
            <a-radio value="class">班级</a-radio>
            <a-radio value="all">全校</a-radio>
          </a-radio-group>
          <a-button @click="fetchData" :loading="loading">
            <template #icon><icon-refresh /></template>
            刷新
          </a-button>
        </a-space>
      </div>
    </a-card>

    <!-- 前三名 Podium -->
    <a-card class="podium-card" :bordered="false" v-if="topThree.length > 0">
      <div class="podium">
        <!-- 第2名 -->
        <div class="podium-item rank-2" v-if="topThree[1]">
          <div class="podium-avatar-wrap">
            <a-avatar :size="52" :style="{ backgroundColor: silverColor }">
              {{ topThree[1].name?.charAt(0) }}
            </a-avatar>
            <div class="podium-medal silver">🥈</div>
          </div>
          <p class="podium-name">{{ topThree[1].name }}</p>
          <p class="podium-score">{{ topThree[1].score }} 分</p>
          <div class="podium-bar rank2-bar"></div>
        </div>

        <!-- 第1名 -->
        <div class="podium-item rank-1" v-if="topThree[0]">
          <div class="podium-crown">👑</div>
          <div class="podium-avatar-wrap">
            <a-avatar :size="64" :style="{ backgroundColor: goldColor }">
              {{ topThree[0].name?.charAt(0) }}
            </a-avatar>
            <div class="podium-medal gold">🥇</div>
          </div>
          <p class="podium-name">{{ topThree[0].name }}</p>
          <p class="podium-score">{{ topThree[0].score }} 分</p>
          <div class="podium-bar rank1-bar"></div>
        </div>

        <!-- 第3名 -->
        <div class="podium-item rank-3" v-if="topThree[2]">
          <div class="podium-avatar-wrap">
            <a-avatar :size="48" :style="{ backgroundColor: bronzeColor }">
              {{ topThree[2].name?.charAt(0) }}
            </a-avatar>
            <div class="podium-medal bronze">🥉</div>
          </div>
          <p class="podium-name">{{ topThree[2].name }}</p>
          <p class="podium-score">{{ topThree[2].score }} 分</p>
          <div class="podium-bar rank3-bar"></div>
        </div>
      </div>
    </a-card>

    <!-- 完整排行榜表格 -->
    <a-card class="table-card" title="完整排名" :bordered="false">
      <template #extra>
        <a-space :size="8">
          <a-input
            v-model="searchName"
            placeholder="搜索学生姓名..."
            style="width: 180px"
            allow-clear
          >
            <template #prefix><icon-search /></template>
          </a-input>
          <a-button @click="exportCSV" size="small">
            <template #icon><icon-export /></template>导出 CSV
          </a-button>
        </a-space>
      </template>

      <a-table
        :data="filteredRows"
        :loading="loading"
        :pagination="{ pageSize: 20, showTotal: true }"
        :stripe="true"
        row-key="studentId"
        size="medium"
      >
        <!-- 排名列 -->
        <a-table-column title="排名" :width="70" align="center">
          <template #cell="{ record }">
            <span v-if="record.rank === 1" class="rank-medal">🥇</span>
            <span v-else-if="record.rank === 2" class="rank-medal">🥈</span>
            <span v-else-if="record.rank === 3" class="rank-medal">🥉</span>
            <span v-else class="rank-num">{{ record.rank }}</span>
          </template>
        </a-table-column>

        <!-- 学生信息 -->
        <a-table-column title="学生" :min-width="140">
          <template #cell="{ record }">
            <a-space :size="8">
              <a-avatar
                :size="30"
                :style="{ backgroundColor: getAvatarColor(record.name) }"
              >
                {{ record.name.charAt(0) }}
              </a-avatar>
              <div>
                <div class="student-name-cell">{{ record.name }}</div>
                <div class="student-id-cell">{{ record.studentId }}</div>
              </div>
            </a-space>
          </template>
        </a-table-column>

        <!-- 成绩 -->
        <a-table-column title="成绩" data-index="score" :width="120" sortable>
          <template #cell="{ record }">
            <div class="score-cell">
              <span class="score-value" :class="getScoreClass(record.score)">
                {{ record.score }}
              </span>
              <a-progress
                :percent="record.score"
                :show-text="false"
                size="mini"
                :color="getScoreColor(record.score)"
                track-color="var(--color-fill-3)"
                style="width: 80px"
              />
            </div>
          </template>
        </a-table-column>

        <!-- 完成率 -->
        <a-table-column title="完成率" data-index="completionRate" :width="120" sortable>
          <template #cell="{ record }">
            <a-progress
              :percent="record.completionRate"
              size="mini"
              :color="record.completionRate >= 90 ? '#00b42a' : record.completionRate >= 60 ? '#ff7d00' : '#f53f3f'"
            />
          </template>
        </a-table-column>

        <!-- 提交时间 -->
        <a-table-column title="提交时间" data-index="submitTime" :width="150" sortable>
          <template #cell="{ record }">
            <span class="time-cell">{{ record.submitTime || '未提交' }}</span>
          </template>
        </a-table-column>

        <!-- 状态 -->
        <a-table-column title="状态" :width="100" align="center">
          <template #cell="{ record }">
            <a-tag
              :color="record.status === 'submitted' ? 'green' : record.status === 'late' ? 'orange' : 'red'"
              size="small"
            >
              {{ statusLabel[record.status] || record.status }}
            </a-tag>
          </template>
        </a-table-column>

        <!-- 操作 -->
        <a-table-column title="操作" :width="90" align="center">
          <template #cell="{ record }">
            <a-button
              size="mini"
              type="text"
              @click="viewDetail(record)"
            >
              <template #icon><icon-eye /></template>
              详情
            </a-button>
          </template>
        </a-table-column>
      </a-table>
    </a-card>

    <!-- 详情抽屉 -->
    <a-drawer
      v-model:visible="detailVisible"
      :title="`${selectedRecord?.name} — 作业详情`"
      :width="400"
    >
      <div v-if="selectedRecord" class="detail-content">
        <div class="detail-section">
          <div class="detail-label">学号</div>
          <div class="detail-value">{{ selectedRecord.studentId }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">成绩</div>
          <div class="detail-value score-big" :class="getScoreClass(selectedRecord.score)">
            {{ selectedRecord.score }} 分
          </div>
        </div>
        <div class="detail-section">
          <div class="detail-label">完成率</div>
          <a-progress :percent="selectedRecord.completionRate" />
        </div>
        <div class="detail-section">
          <div class="detail-label">提交时间</div>
          <div class="detail-value">{{ selectedRecord.submitTime || '未提交' }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">评语</div>
          <div class="detail-value comment-text">{{ selectedRecord.comment || '暂无评语' }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">AI 分析</div>
          <div class="ai-analysis">
            <div class="ai-analysis-item" v-for="item in selectedRecord.aiAnalysis" :key="item.key">
              <div class="ai-item-header">
                <span class="ai-item-key">{{ item.key }}</span>
                <a-tag :color="item.good ? 'green' : 'orange'" size="small">
                  {{ item.good ? '掌握良好' : '需改进' }}
                </a-tag>
              </div>
              <p class="ai-item-detail">{{ item.detail }}</p>
            </div>
          </div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { ref, computed, onMounted } from 'vue';
  import { queryLeaderboard, type LeaderboardRow } from '@/api/course';

  // ========== 类型 ==========
  // 类型定义已经从 @/api/course 导入

  // ========== 状态 ==========
  const loading = ref(false);
  const searchName = ref('');
  const detailVisible = ref(false);
  const selectedRecord = ref<LeaderboardRow | null>(null);

  const filters = ref({
    courseId: '',
    taskId: '',
    sortBy: 'score',
    scope: 'class',
  });

  // ========== 静态数据（TODO: 替换为 API） ==========
  // GET /api/v1/courses → courses
  const courses = ref([
    { id: 'c1', name: '计算机组成原理' },
    { id: 'c2', name: '操作系统' },
    { id: 'c3', name: '计算机网络' },
    { id: 'c4', name: '算法设计与分析' },
  ]);

  // GET /api/v1/courses/:id/tasks → tasks
  const tasks = ref([
    { id: 't1', name: '作业一：流水线设计' },
    { id: 't2', name: '作业二：Cache策略' },
    { id: 't3', name: '实验：模拟CPU' },
  ]);

  const mockRows: LeaderboardRow[] = [
    { rank: 1, name: '李明', studentId: '2021001', score: 98, completionRate: 100, submitTime: '2025-04-06 09:12', status: 'submitted', comment: '结构设计清晰，流水线分析准确。', aiAnalysis: [{ key: '流水线冒险', good: true, detail: '能正确识别数据冒险并给出解决方案' }, { key: '吞吐率计算', good: true, detail: '公式使用正确，结果精确' }] },
    { rank: 2, name: '王芳', studentId: '2021002', score: 95, completionRate: 100, submitTime: '2025-04-06 10:30', status: 'submitted', comment: '整体优秀，代码注释丰富。', aiAnalysis: [{ key: '控制冒险', good: true, detail: '分支预测部分分析清晰' }, { key: '性能优化', good: false, detail: '优化建议较少，可增加局部性分析' }] },
    { rank: 3, name: '张伟', studentId: '2021003', score: 91, completionRate: 95, submitTime: '2025-04-06 14:20', status: 'submitted' },
    { rank: 4, name: '陈静', studentId: '2021005', score: 88, completionRate: 92, submitTime: '2025-04-07 08:45', status: 'late' },
    { rank: 5, name: '周鑫', studentId: '2021007', score: 85, completionRate: 90, submitTime: '2025-04-06 20:11', status: 'submitted' },
    { rank: 6, name: '吴婷', studentId: '2021008', score: 82, completionRate: 88, submitTime: '2025-04-07 11:00', status: 'late' },
    { rank: 7, name: '马丽', studentId: '2021010', score: 80, completionRate: 85, submitTime: '2025-04-06 16:30', status: 'submitted' },
    { rank: 8, name: '朱萌', studentId: '2021012', score: 76, completionRate: 80, submitTime: '2025-04-07 09:00', status: 'submitted' },
    { rank: 9, name: '林峰', studentId: '2021013', score: 72, completionRate: 75, submitTime: '2025-04-07 12:00', status: 'late' },
    { rank: 10, name: '胡宇', studentId: '2021011', score: 68, completionRate: 70, submitTime: '2025-04-08 07:00', status: 'late' },
    { rank: 11, name: '郭磊', studentId: '2021015', score: 65, completionRate: 65, submitTime: '2025-04-07 22:00', status: 'submitted' },
    { rank: 12, name: '韩雪', studentId: '2021017', score: 60, completionRate: 60, submitTime: '', status: 'missing' },
    { rank: 13, name: '刘洋', studentId: '2021006', score: 0, completionRate: 0, submitTime: '', status: 'missing' },
    { rank: 14, name: '赵雷', studentId: '2021004', score: 0, completionRate: 0, submitTime: '', status: 'missing' },
  ];
  
  const rows = ref<LeaderboardRow[]>([]);

  const topThree = computed(() => rows.value.slice(0, 3));

  const filteredRows = computed(() => {
    let result = rows.value;
    if (searchName.value.trim()) {
      result = result.filter((r) => r.name.includes(searchName.value.trim()));
    }
    return result;
  });

  // ========== 颜色工具 ==========
  const goldColor = '#f5a623';
  const silverColor = '#8a9ab5';
  const bronzeColor = '#c87332';

  const statusLabel: Record<string, string> = {
    submitted: '已提交',
    late: '迟交',
    missing: '缺交',
  };

  function getScoreClass(score: number) {
    if (score >= 90) return 'score-excellent';
    if (score >= 75) return 'score-good';
    if (score >= 60) return 'score-pass';
    return 'score-fail';
  }

  function getScoreColor(score: number) {
    if (score >= 90) return '#00b42a';
    if (score >= 75) return '#165DFF';
    if (score >= 60) return '#ff7d00';
    return '#f53f3f';
  }

  const avatarPalette = ['#165DFF', '#0fc6c2', '#9254de', '#f5a623', '#00b42a', '#f53f3f'];
  function getAvatarColor(name: string): string {
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return avatarPalette[Math.abs(hash) % avatarPalette.length];
  }

  function viewDetail(record: LeaderboardRow) {
    selectedRecord.value = record;
    detailVisible.value = true;
  }

  function exportCSV() {
    const headers = ['排名', '姓名', '学号', '成绩', '完成率', '提交时间', '状态'];
    const csvRows = [
      headers.join(','),
      ...rows.value.map((r) =>
        [r.rank, r.name, r.studentId, r.score, `${r.completionRate}%`, r.submitTime || '未提交', statusLabel[r.status]].join(',')
      ),
    ];
    const blob = new Blob(['\uFEFF' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '作业排行榜.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  async function fetchData() {
    loading.value = true;
    try {
      const { data } = await queryLeaderboard(
        filters.value.courseId || 'c1',
        filters.value.taskId || 't1',
        { sortBy: filters.value.sortBy, scope: filters.value.scope }
      );
      rows.value = (data && data.length > 0) ? data : mockRows;
    } catch {
      rows.value = mockRows;
      loading.value = false;
    }
  }

  onMounted(fetchData);
</script>

<style scoped lang="less">
  .leaderboard-page {
    padding: 0 20px 20px;
  }

  // 筛选栏
  .filter-card {
    margin-bottom: 16px;
  }

  .filter-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }

  // 颁奖台
  .podium-card {
    margin-bottom: 16px;
    background: linear-gradient(160deg, #f0f5ff 0%, #f5f0ff 100%);
    border-radius: 12px;

    :deep(.arco-card-body) {
      padding: 24px 40px;
    }
  }

  .podium {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    gap: 24px;
    min-height: 180px;
  }

  .podium-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    position: relative;
  }

  .podium-crown {
    font-size: 20px;
    margin-bottom: -4px;
    animation: float 2s ease-in-out infinite;
  }

  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
  }

  .podium-avatar-wrap {
    position: relative;
    display: inline-block;
  }

  .podium-medal {
    position: absolute;
    bottom: -2px;
    right: -4px;
    font-size: 16px;
  }

  .podium-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-1);
    margin: 0;
    letter-spacing: -0.1px;
  }

  .podium-score {
    font-size: 18px;
    font-weight: 700;
    margin: 0;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.5px;
  }

  .rank-1 .podium-score { color: #f5a623; }
  .rank-2 .podium-score { color: #8a9ab5; }
  .rank-3 .podium-score { color: #c87332; }

  .podium-bar {
    width: 80px;
    border-radius: 6px 6px 0 0;
  }

  .rank1-bar {
    height: 80px;
    background: linear-gradient(180deg, #f5a623, #e8910a);
  }

  .rank2-bar {
    height: 55px;
    background: linear-gradient(180deg, #aebfd8, #8a9ab5);
  }

  .rank3-bar {
    height: 38px;
    background: linear-gradient(180deg, #d4956b, #c87332);
  }

  // 表格卡片
  .table-card {
    :deep(.arco-table-th) {
      background: var(--color-fill-1);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.2px;
      text-transform: uppercase;
    }
  }

  // 排名列
  .rank-medal {
    font-size: 18px;
    line-height: 1;
  }

  .rank-num {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-2);
    font-variant-numeric: tabular-nums;
  }

  // 学生列
  .student-name-cell {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text-1);
    letter-spacing: -0.1px;
  }

  .student-id-cell {
    font-size: 11px;
    color: var(--color-text-3);
    font-variant-numeric: tabular-nums;
  }

  // 成绩列
  .score-cell {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .score-value {
    font-size: 15px;
    font-weight: 700;
    width: 32px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .score-excellent { color: #00b42a; }
  .score-good { color: #165DFF; }
  .score-pass { color: #ff7d00; }
  .score-fail { color: #f53f3f; }

  // 时间列
  .time-cell {
    font-size: 12px;
    color: var(--color-text-2);
    font-variant-numeric: tabular-nums;
  }

  // 详情抽屉
  .detail-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 8px 0;
  }

  .detail-section {
    border-bottom: 1px solid var(--color-border-1);
    padding-bottom: 14px;

    &:last-child {
      border-bottom: none;
    }
  }

  .detail-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text-3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .detail-value {
    font-size: 14px;
    color: var(--color-text-1);
  }

  .score-big {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
    font-variant-numeric: tabular-nums;
  }

  .comment-text {
    line-height: 1.6;
    color: var(--color-text-2);
    font-size: 13px;
  }

  // AI分析
  .ai-analysis {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .ai-analysis-item {
    padding: 10px 12px;
    background: var(--color-fill-1);
    border-radius: 8px;
    border: 1px solid var(--color-border-1);
  }

  .ai-item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .ai-item-key {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text-1);
  }

  .ai-item-detail {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-2);
    line-height: 1.5;
  }
</style>

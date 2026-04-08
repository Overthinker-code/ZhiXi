<template>
  <div class="assignment-submit-page">
    <Breadcrumb :items="['menu.course', '作业提交']" />

    <div class="assignment-layout">
      <!-- 左侧：作业提交表单 -->
      <a-card class="submit-card" title="提交作业" :bordered="false">
        <a-form
          ref="formRef"
          :model="submitForm"
          layout="vertical"
          @submit="handleSubmit"
        >
          <a-row :gutter="24">
            <a-col :span="12">
              <a-form-item
                field="courseId"
                label="选择课程"
                :rules="[{ required: true, message: '请选择课程' }]"
              >
                <a-select v-model="submitForm.courseId" placeholder="请选择课程">
                  <a-option v-for="c in courses" :key="c.id" :value="c.id">
                    {{ c.name }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item
                field="taskId"
                label="选择作业项"
                :rules="[{ required: true, message: '请选择需要提交的作业' }]"
              >
                <a-select v-model="submitForm.taskId" placeholder="请选择对应作业" :disabled="!submitForm.courseId">
                  <a-option v-for="t in tasks" :key="t.id" :value="t.id">
                    {{ t.name }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>

          <a-form-item field="files" label="作业附件 (PDF, ZIP, 代码文件)">
            <a-upload
              draggable
              multiple
              :auto-upload="false"
              v-model:fileList="fileList"
              action="/"
              class="assignment-upload"
            >
              <template #upload-button>
                <div class="upload-area">
                  <div class="upload-icon-wrap">
                    <icon-upload class="upload-icon" />
                  </div>
                  <div class="upload-text">
                    点击或拖拽文件到这里上传
                  </div>
                  <div class="upload-sub">
                    支持单次上传多个文件，单个限100MB
                  </div>
                </div>
              </template>
            </a-upload>
          </a-form-item>

          <a-form-item field="content" label="文字解答 / 备注说明">
            <a-textarea
              v-model="submitForm.content"
              placeholder="如果有需要向老师说明的情况，或者简短的文字解答，请写在这里..."
              :auto-size="{ minRows: 4, maxRows: 8 }"
            />
          </a-form-item>

          <div class="submit-action">
            <a-button type="primary" html-type="submit" :loading="submitting" size="large">
              <template #icon><icon-send /></template>
              确认提交
            </a-button>
            <p class="submit-tip">提示：多次提交以最后一次时间与文件为准。</p>
          </div>
        </a-form>
      </a-card>

      <!-- 右侧：提交历史与状态 -->
      <a-card class="history-card" title="最近提交记录" :bordered="false">
        <div v-if="submitHistory.length === 0" class="empty-history">
          <icon-check-square class="empty-icon" />
          <p>暂无提交记录，继续保持学习！</p>
        </div>
        <a-timeline v-else class="history-timeline">
          <a-timeline-item
            v-for="item in submitHistory"
            :key="item.id"
            :dot-type="item.status === 'graded' ? 'solid' : 'hollow'"
            :dot-color="item.status === 'graded' ? '#00b42a' : '#165DFF'"
          >
            <div class="history-item">
              <div class="history-header">
                <span class="history-task">{{ item.taskName }}</span>
                <a-tag :color="item.status === 'graded' ? 'green' : 'blue'" size="small">
                  {{ item.status === 'graded' ? '已批改' : '待批改' }}
                </a-tag>
              </div>
              <div class="history-meta">
                <icon-clock-circle /> {{ item.submitTime }}
                <span class="history-course">· {{ item.courseName }}</span>
              </div>
              
              <div v-if="item.files?.length" class="history-files">
                <div v-for="cf in item.files" :key="cf.name" class="file-tag">
                  <icon-file /> {{ cf.name }}
                </div>
              </div>

              <div v-if="item.status === 'graded'" class="history-grade">
                <div class="grade-score">{{ item.score }}</div>
                <div class="grade-comment">{{ item.comment }}</div>
              </div>
            </div>
          </a-timeline-item>
        </a-timeline>
      </a-card>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { submitAssignment } from '@/api/course';
  import dayjs from 'dayjs';

  const formRef = ref();
  const submitting = ref(false);

  const courses = ref([
    { id: 'c1', name: '计算机组成原理' },
    { id: 'c2', name: '操作系统' },
    { id: 'c3', name: '计算机网络' },
  ]);

  const tasks = ref([
    { id: 't1', name: '作业一：流水线设计' },
    { id: 't2', name: '作业二：Cache策略' },
    { id: 't3', name: '实验：模拟CPU' },
  ]);

  const submitForm = ref({
    courseId: '',
    taskId: '',
    content: ''
  });

  const fileList = ref<any[]>([]);

  const submitHistory = ref([
    {
      id: 'h1',
      courseName: '操作系统',
      taskName: '进程调度实验',
      submitTime: '2025-04-06 14:30',
      status: 'graded',
      score: 95,
      comment: '分析透彻',
      files: [{ name: 'os_lab1.zip' }]
    },
    {
      id: 'h2',
      courseName: '计算机网络',
      taskName: '抓包分析',
      submitTime: '昨天 21:05',
      status: 'pending',
      files: [{ name: 'wireshark_capture.pcap' }, { name: 'report.pdf' }]
    }
  ]);

  const handleSubmit = async ({ values, errors }: any) => {
    if (errors) return;
    if (fileList.value.length === 0 && !submitForm.value.content.trim()) {
      Message.warning('附件或文字描述至少需提供一项');
      return;
    }

    submitting.value = true;
    try {
      const formData = new FormData();
      formData.append('courseId', submitForm.value.courseId);
      formData.append('taskId', submitForm.value.taskId);
      formData.append('content', submitForm.value.content);
      
      fileList.value.forEach(item => {
        if (item.file) {
          formData.append('files', item.file);
        }
      });

      // 真实后端部署后使用此真实接口
      // await submitAssignment(formData);
      
      // 现在暂时模拟耗时
      await new Promise(r => setTimeout(r, 800));
      
      Message.success('作业提交成功，可多次重复提交覆盖');
      
      // 更新历史（本地mock预览用）
      submitHistory.value.unshift({
        id: 'h' + Date.now(),
        courseName: courses.value.find(c => c.id === submitForm.value.courseId)?.name || '未知课程',
        taskName: tasks.value.find(t => t.id === submitForm.value.taskId)?.name || '未知作业',
        submitTime: dayjs().format('YYYY-MM-DD HH:mm'),
        status: 'pending',
        files: fileList.value.map(f => ({ name: f.name }))
      });

      // 重置表单
      submitForm.value.content = '';
      fileList.value = [];
    } catch (e: any) {
      Message.error(`提交失败: ${e.message || '未知错误'}`);
    } finally {
      submitting.value = false;
    }
  };
</script>

<style scoped lang="less">
  .assignment-submit-page {
    padding: 0 20px 20px;
    min-height: 100%;
    background: var(--color-bg-1);
  }

  .assignment-layout {
    display: grid;
    grid-template-columns: minmax(0, 7fr) minmax(0, 4fr);
    gap: 16px;
    margin-top: 12px;
  }

  @media (max-width: 900px) {
    .assignment-layout {
      grid-template-columns: 1fr;
    }
  }

  // ====== 左侧表单 ======
  .upload-area {
    padding: 30px;
    background: var(--color-fill-1);
    border: 1px dashed var(--color-border-2);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    transition: all 0.2s ease;
    cursor: pointer;

    &:hover {
      background: var(--color-fill-2);
      border-color: #165dff;
    }
  }

  .upload-icon-wrap {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: rgba(22, 93, 255, 0.08);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .upload-icon {
    font-size: 24px;
    color: #165dff;
  }

  .upload-text {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-1);
  }

  .upload-sub {
    font-size: 12px;
    color: var(--color-text-3);
  }

  .submit-action {
    margin-top: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .submit-tip {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-3);
  }

  // ====== 右侧历史 ======
  .empty-history {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 0;
    color: var(--color-text-3);
    font-size: 14px;
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.3;
  }

  .history-timeline {
    padding-top: 10px;
  }

  .history-item {
    background: var(--color-fill-1);
    padding: 12px 14px;
    border-radius: 8px;
    border: 1px solid var(--color-border-1);
  }

  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 6px;
  }

  .history-task {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-1);
    line-height: 1.4;
  }

  .history-meta {
    font-size: 12px;
    color: var(--color-text-3);
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
  }

  .history-course {
    color: var(--color-text-2);
  }

  .history-files {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .file-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #165dff;
    background: rgba(22, 93, 255, 0.05);
    padding: 4px 8px;
    border-radius: 4px;
    width: fit-content;
  }

  .history-grade {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed var(--color-border-2);
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .grade-score {
    font-size: 18px;
    font-weight: 700;
    color: #00b42a;
    font-variant-numeric: tabular-nums;

    &::after {
      content: '分';
      font-size: 12px;
      margin-left: 2px;
      font-weight: normal;
    }
  }

  .grade-comment {
    flex: 1;
    font-size: 12px;
    color: var(--color-text-2);
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
  }
</style>

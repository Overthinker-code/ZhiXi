<template>
  <div>
    <a-container>
      <a-container>
        <a-main>
          <!-- <h1>学生学习情况</h1> -->
          <div class="left-column">
            <!-- 学生画像 -->
            <div class="profile-container student-portrait">
              <img src="@/assets/images/学生头像.jpg" alt="学生头像" />
              <div>
                <h2 class="profile-title">学生画像</h2>
                <p>姓名: 卡布奇</p>
                <p>学号: 12345689</p>
                <p style="margin-bottom: 25px">专业: 计算机科学与技术</p>
                <h2 class="profile-title">本学期选修课程：</h2>
                <p>《计算机组成原理》《操作系统》《计算机网络》······</p>
              </div>
            </div>

            <div class="chart-container2">
              <Calendar v-model:value="value">
                <template #dateCellRender="{ current }">
                  <ul class="events">
                    <li
                      v-for="item in getListData(current)"
                      :key="item.content"
                    >
                      <a-badge :status="item.type" :text="item.content" />
                    </li>
                  </ul>
                </template>
                <template #monthCellRender="{ current }">
                  <div v-if="getMonthData(current)" class="notes-month">
                    <section>{{ getMonthData(current) }}</section>
                    <span>Backlog number</span>
                  </div>
                </template>
              </Calendar>
            </div>
          </div>
          <div class="right-column">
            <!-- 学生学情概况 -->
            <div class="profile-container">
              <h2 class="profile-title">学生学情概况</h2>
              <div class="performance-list">
                <div class="performance-item">
                  <div class="performance-value">11</div>
                  <div class="performance-label">云端时长</div>
                </div>
                <div class="performance-item">
                  <div class="performance-value">2</div>
                  <div class="performance-label">讨论次数</div>
                </div>
                <div class="performance-item">
                  <div class="performance-value">4</div>
                  <div class="performance-label">互动次数</div>
                </div>
                <div class="performance-item">
                  <div class="performance-value">0</div>
                  <div class="performance-label">瞌睡次数</div>
                </div>
                <div class="performance-item">
                  <div class="performance-value">15</div>
                  <div class="performance-label">考勤次数</div>
                </div>
                <div class="performance-item">
                  <div class="performance-value">91</div>
                  <div class="performance-label">平均成绩</div>
                </div>
              </div>
            </div>

            <!-- 学生学情预警 -->
            <div class="profile-container">
              <h2 class="profile-title">学生学情预警</h2>
              <ul class="alert-list">
                <li class="alert-item">
                  <span>2025.4.27</span>
                  <span>操作系统课程</span>
                  <span>上课无故缺席</span>
                </li>
                <li class="alert-item"
                  ><span>2025.4.23</span>
                  <span>计算机网络</span>
                  <span>实验作业未提交</span>
                </li>
                <li class="alert-item">
                  <span>2025.3.15</span>
                  <span>算法设计与分析</span>
                  <span>未发布讨论</span>
                </li>
                <li class="alert-item"
                  ><span>2025.2.25</span>
                  <span>计算机组成原理</span>
                  <span>测试成绩不佳</span>
                </li>
              </ul>
            </div>
            <div class="chart-container1">
              <h2 class="profile-title">学习时长占比</h2>
              <div
                ref="chartDom1"
                style="
                  width: 400px;
                  height: 300px;
                  margin-top: -30px;
                  margin-left: 10%;
                "
              ></div>
            </div>
          </div>
        </a-main>
      </a-container>
    </a-container>
  </div>
</template>

<script>
  import { Calendar } from 'ant-design-vue';
  import 'ant-design-vue/dist/reset.css';
  import dayjs from 'dayjs';
  import * as echarts from 'echarts';
  import { ref } from 'vue';
  import { chartOption1 } from './chartsConfig/chartsConfig'; // 引入数据和配置

  export default {
    name: 'HomePage',
    components: { Calendar },
    setup() {
      const value = ref(dayjs());
      return {
        value,
      };
    },
    data() {
      return {
        myChart1: null,
      };
    },
    mounted() {
      this.initCharts();
    },
    beforeUnmount() {
      this.disposeAllCharts();
    },
    methods: {
      initCharts() {
        this.initChart1();
      },
      initChart1() {
        const { chartDom1 } = this.$refs;
        if (chartDom1) {
          this.myChart1 = echarts.init(chartDom1);
          this.myChart1.setOption(chartOption1);
        } else {
          // console.error('Chart DOM element 1 not found');
        }
      },
      disposeAllCharts() {
        if (this.myChart1) {
          this.myChart1.dispose();
        }
      },
      getListData: (value) => {
        let listData;
        switch (value.date()) {
          case 8:
            listData = [
              {
                type: 'warning',
                content: 'task4截止',
              },
              {
                type: 'success',
                content: '计算机网络课程',
              },
            ];
            break;
          case 10:
            listData = [
              {
                type: 'warning',
                content: '实验1截止',
              },
              {
                type: 'success',
                content: '计算机组成原理',
              },
            ];
            break;
          case 15:
            listData = [
              {
                type: 'success',
                content: '计算机网络课程',
              },
            ];
            break;
          default:
        }
        return listData || [];
      },
      getMonthData: (value) => {
        if (value.month() === 8) {
          return 1394;
        }
        return null;
      },
    },
  };
</script>

<style scoped>
  ul li {
    list-style: none;
  }

  /* 页面布局 */
  a-container {
    display: flex;

    /* flex-direction: column; */
    height: 100vh;
  }

  a-main {
    display: grid;
    grid-template-columns: 6fr 4fr;

    /* 左右宽度比例为6:4 */

    /* grid-template-columns: 1fr 1fr; 左右两列布局 */
    gap: 20px;
    padding: 20px;
    background-color: rgb(232 232 232);
  }

  /* 左侧内容区域（学生信息和学情概况） */
  .left-column {
    display: grid;
    grid-template-rows: 300px 500px;

    /* 两个区域垂直排列 */
    gap: 18px;
  }

  /* 右侧内容区域（图表） */
  .right-column {
    display: grid;
    grid-template-rows: 220px 270px 390px;

    /* 两个图表垂直排列 */
    gap: 15px;

    /* height: fit-content; */
  }

  /* 学生学情概况容器样式 */
  .profile-container {
    padding: 20px;
    background-color: #fff;
    border: 1px solid #ccc;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgb(0 0 0 / 10%);
  }

  /* 标题样式 */
  .profile-title {
    margin-top: 0;
    margin-bottom: 25px;
    color: #333;
    font-weight: bold;
    font-size: 18px;
  }

  /* 数据项布局和样式 */
  .performance-list {
    display: grid;
    grid-template-columns: repeat(6, 1fr);

    /* 设置为6列 */
    gap: 10px;
    text-align: center;
  }

  /* 数字样式 */
  .performance-value {
    /* 数字较大 */
    font-weight: bold;
    font-size: 24px;
  }

  .performance-item:nth-child(1) .performance-value {
    color: #ff5733;

    /* 第1个数字的颜色 - 橙色 */
  }

  .performance-item:nth-child(2) .performance-value {
    color: #33c3ff;

    /* 第2个数字的颜色 - 浅蓝色 */
  }

  .performance-item:nth-child(3) .performance-value {
    color: #33ff57;

    /* 第3个数字的颜色 - 绿色 */
  }

  .performance-item:nth-child(4) .performance-value {
    color: #ff33a1;

    /* 第4个数字的颜色 - 粉色 */
  }

  .performance-item:nth-child(5) .performance-value {
    color: #ffd133;

    /* 第5个数字的颜色 - 黄色 */
  }

  .performance-item:nth-child(6) .performance-value {
    color: #9b33ff;

    /* 第6个数字的颜色 - 紫色 */
  }

  /* 标签文字样式 */
  .performance-label {
    color: #888;
    font-size: 12px;

    /* 灰色 */
  }

  .student-portrait {
    display: flex;
    align-items: center;

    /* margin-bottom: 20px; */
  }

  .student-portrait img {
    width: 120px;
    height: 120px;
    margin-right: 30px;
    border-radius: 50%;
  }

  .performance-list {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    color: #666;
    font-size: 14px;
    text-align: center;
  }

  .performance-item {
    padding: 10px;
    background-color: #f5f5f5;
    border-radius: 5px;
  }

  .alert-list {
    display: grid;
    gap: 10px;
    width: 80%;
    margin: 20px auto;
    padding: 0;
  }

  .alert-item {
    display: flex;
    justify-content: space-around;
    padding: 10px 0;
    font-size: 14px;
    background-color: #ffe4e1;
    border-radius: 5px;
  }

  .alert-item span {
    flex: 1;
    text-align: center;
  }

  /* 图表容器样式 */
  .chart-container1 {
    width: 100%;
    height: 90%;
    margin-top: 5px;
    margin-bottom: 10px;
    padding: 20px;
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgb(0 0 0 / 10%);
  }

  .chart-container2 {
    width: 100%;
    height: 550px;

    /* margin-top: 5px; */
    margin-bottom: 5px;

    /* padding: 20px; */
    overflow: scroll;
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgb(0 0 0 / 10%);
  }

  .events {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .events .ant-badge-status {
    width: 100%;
    overflow: hidden;
    font-size: 12px;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .notes-month {
    font-size: 28px;
    text-align: center;
  }

  .notes-month section {
    font-size: 28px;
  }

  /* 响应式布局 */
  @media (max-width: 768px) {
    .a-main {
      grid-template-columns: 1fr;

      /* 小屏幕时单列布局 */
    }

    .student-portrait {
      flex-direction: column;
      align-items: center;
    }

    .student-portrait img {
      margin-bottom: 15px;
    }

    .performance-list {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>

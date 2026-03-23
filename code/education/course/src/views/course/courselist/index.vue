<template>
  <div>
    <a-container>
      <el-main>
        <!-- 顶部标题 -->
        <div class="page-header">
          <h1>课程总览</h1>
        </div>

        <!-- 分类导航栏和搜索框 -->
        <a-row :gutter="20" class="navbar-container">
          <!-- 导航栏 -->
          <a-col :span="12">
            <div class="navbar">
              <span
                v-for="(category, index) in categories"
                :key="index"
                class="navbar-item"
                :class="{ active: selectedCategory === category }"
                @click="selectCategory(category)"
              >
                {{ category }}
              </span>
            </div>
          </a-col>

          <!-- 搜索框 -->
          <a-col :span="12" class="search-container">
            <a-input-search
              :style="{ width: '320px' }"
              placeholder="搜索教师或课程"
              v-model="searchQuery"
              class="search-input"
              @input="searchTeachers"
              search-button
            >
              <template #button-icon>
                <icon-search />
              </template>
              <template #button-default> Search </template>
            </a-input-search>
          </a-col>
        </a-row>

        <!-- 教师信息表格 -->
        <a-row :gutter="10" justify="left" style="margin: 10px 20px">
          <a-col
            v-for="(teacher, index) in filteredTeachers"
            :key="index"
            :span="8"
          >
            <div class="teacher-card">
              <div class="teacher-image">
                <img :src="teacher.image" alt="Teacher Avatar" />
              </div>
              <div class="teacher-details">
                <p class="teacher-name">{{ teacher.name }}</p>

                <p class="teacher-title">{{ teacher.title }}</p>
                <p class="teacher-email">{{ teacher.email }}</p>

                <p class="teacher-department">{{ teacher.department }}</p>
                <!-- <p class="teacher-research">{{ teacher.research }}</p> -->
              </div>
            </div>
          </a-col>
        </a-row>
      </el-main>
    </a-container>
  </div>
</template>

<script>
  import AIImg from '@/assets/images/AI.jpg';
  import EcoImg from '@/assets/images/宏观经济学.jpg';
  import ShenImg from '@/assets/images/审计学.jpg';
  import DatabaseImg from '@/assets/images/数据库图片.png';
  import DatastructureImg from '@/assets/images/数据结构.jpg';
  import YuanImg from '@/assets/images/金融学.jpg';

  export default {
    name: 'TeacherList',
    components: {},
    data() {
      return {
        searchQuery: '',
        selectedCategory: '全部',
        categories: ['全部', '计算机学院', '经管学院'],
        teachers: [
          {
            image: AIImg,
            name: '人工智能',
            title: '潘教授',
            department: '计算机学院',
            email: 'Ruiiii.teacher@university.com',
            research: '人工智能，机器学习',
          },
          {
            image: EcoImg,
            name: '宏观经济学',
            title: '王教授',
            department: '经管学院',
            email: 'wang.teacher@university.com',
            research: '软件工程，系统架构',
          },
          {
            image: ShenImg,
            name: '审计学',
            title: '张讲师',
            department: '经管学院',
            email: 'zhang.teacher@university.com',
            research: '无线通信，信号处理',
          },
          {
            image: DatabaseImg,
            name: '数据库原理',
            title: '赵讲师',
            department: '计算机学院',
            email: 'zhao.teacher@university.com',
            research: '大数据，云计算',
          },
          {
            image: DatastructureImg,
            name: '数据结构',
            title: '钱教授',
            department: '计算机学院',
            email: 'qian.teacher@university.com',
            research: '数据库系统，数据挖掘',
          },
          {
            image: YuanImg,
            name: '金融学',
            title: '孙教授',
            department: '经管学院',
            email: 'sun.teacher@university.com',
            research: '网络安全，物联网',
          },
        ],
      };
    },
    computed: {
      filteredTeachers() {
        return this.teachers
          .filter((teacher) => {
            const searchTerm = this.searchQuery.toLowerCase();
            return (
              teacher.name.toLowerCase().includes(searchTerm) ||
              teacher.title.toLowerCase().includes(searchTerm)
            );
          })
          .filter((teacher) => {
            return (
              this.selectedCategory === '全部' ||
              teacher.department === this.selectedCategory
            );
          });
      },
    },
    methods: {
      searchTeachers() {
        // 实际搜索逻辑处理可以根据具体需求进行扩展
      },
      selectCategory(category) {
        this.selectedCategory = category;
      },
    },
  };
</script>

<style scoped>
  a-container {
    padding: 20px;
  }

  .page-header {
    margin-top: 30px;
    text-align: center;
  }

  h1 {
    font-weight: bold;
    font-size: 28px;
  }

  .navbar-container {
    margin-top: 20px;
    padding-left: 30px;
  }

  .navbar {
    display: flex;

    /* 横向排列 */
    flex-direction: row;

    /* 左对齐 */
    gap: 30px;

    /* 横向排列 */
    justify-content: flex-start;

    /* 菜单项之间的间隔 */
  }

  .navbar-item {
    /* 文字颜色 */
    padding: 5px 0;

    /* 文字大小 */
    color: #555;
    font-size: 16px;

    /* 鼠标样式 */
    white-space: nowrap;

    /* 内边距，增加点击区域 */
    cursor: pointer;

    /* 防止文字换行 */
  }

  .navbar-item:hover {
    color: #007bff;

    /* 鼠标悬停时的文字颜色 */
  }

  .navbar-item.active {
    color: #007bff;

    /* 激活状态下的文字颜色 */
    font-weight: bold;

    /* 激活状态下加粗 */
  }

  .search-container {
    display: flex;
    justify-content: flex-end;
  }

  .search-input {
    width: 300px;
    margin: 0 20px;

    /* padding: 8px 16px; */
    font-size: 14px;
    background-color: #fff;
    border: 1px solid #007bff;
    border-radius: 4px;
  }

  .teacher-card {
    display: flex;
    flex-direction: column;
    margin-top: 20px;
    padding: 20px;
    background-color: #fff;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgb(0 0 0 / 10%);
  }

  .teacher-image {
    width: 100%;

    /* height: 100px; */
    margin: 0 auto;
  }

  .teacher-image img {
    width: 80%;
    margin-left: 10%;
    object-fit: cover;
  }

  .teacher-details {
    flex-grow: 1;
    text-align: center;
  }

  .teacher-name {
    margin-top: 20px;
    color: #007bff;
    font-weight: bold;
    font-size: 20px;
  }

  .teacher-title {
    color: #007bff;
    font-size: 18px;
  }

  .teacher-department,
  .teacher-email,
  .teacher-research {
    color: #888;
    font-size: 14px;
  }

  .teacher-research {
    margin-top: 10px;
  }

  .el-dialog {
    width: 400px;
  }
</style>

<template>
  <div>
    <el-container>
      <el-main>
        <div
          class="main"
          style="
            display: flex;
            flex-direction: row;
            width: 100%;
            width: 100%;
            height: 1100px;
            padding: 10px;
            overflow-y: hidden;
            background: #e8e8e8;
          "
        >
          <div
            class="left"
            style="
              display: flex;
              flex-direction: column;
              width: 50%;
              height: 100%;
            "
          >
            <div
              class="Course-info"
              style="height: 70%; margin: 10px; background: #fff"
            >
              <p class="title-div">课程信息</p>
              <div
                class="bar"
                style=" width: 90%; margin-left: 5%;border: 1px solid #f0f2f6"
              ></div>
              <p
                style="
                  margin: 15px 20px;
                  color: #1f63ff;
                  font-weight: 600;
                  font-size: 25px;
                "
                >数据库原理
              </p>
              <p
                style="margin: 10px; padding: 0 20px 10px; line-height: 20px"
              >
                《数据库原理》介绍了数据库系统的基本原理、设计方法与应用技术。主要内容包括数据模型、关系数据库、SQL语言、数据库设计、事务管理、并发控制、恢复技术以及数据库安全等。
              </p>
              <div style=" display: flex; flex-direction: row;width: 100%">
                <div style="width: 33.33%">
                  <p
                    style="
                      color: #1f63ff;
                      font-weight: 600;
                      font-size: 15px;
                      text-align: center;
                    "
                    >课程学分
                  </p>
                  <p
                    style="
                      font-weight: 600;
                      font-size: 15px;
                      text-align: center;
                    "
                    >3.0</p
                  >
                </div>
                <div style="width: 33.33%">
                  <p
                    style="
                      color: #1f63ff;
                      font-weight: 600;
                      font-size: 15px;
                      text-align: center;
                    "
                    >课程性质
                  </p>
                  <p
                    style="
                      font-weight: 600;
                      font-size: 15px;
                      text-align: center;
                    "
                    >专业核心课</p
                  >
                </div>
                <div style="width: 33.33%">
                  <p
                    style="
                      color: #1f63ff;
                      font-weight: 600;
                      font-size: 15px;
                      text-align: center;
                    "
                    >课堂数量
                  </p>
                  <p
                    style="
                      font-weight: 600;
                      font-size: 15px;
                      text-align: center;
                    "
                    >3</p
                  >
                </div>
              </div>
              <div
                class="bar"
                style=" width: 90%; margin: 0 auto;border: 1px solid #f0f2f6"
              ></div>
              <div
                id="all-classes"
                class="bottom1"
                style="
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  justify-content: center;
                  margin-top: 10px;
                "
              >
                <div class="title1">
                  <div class="class-info">
                    <p style="color: #1f63ff; font-weight: 600; font-size: 15px"
                      >授课老师</p
                    >
                  </div>
                  <div class="class-info">
                    <p style="color: #1f63ff; font-weight: 600; font-size: 15px"
                      >上课地点</p
                    >
                  </div>
                  <div class="class-info">
                    <p style="color: #1f63ff; font-weight: 600; font-size: 15px"
                      >上课时间</p
                    >
                  </div>
                  <div class="class-info">
                    <p style="color: #1f63ff; font-weight: 600; font-size: 15px"
                      >上课人数</p
                    >
                  </div>
                </div>
                <div
                  v-for="(classInfo, index) in classData"
                  :key="index"
                  class="all-classes"
                >
                  <div class="class-info">
                    <p>{{ classInfo.teacher }}</p>
                  </div>
                  <div
                    class="class-info"
                    style="display: flex; flex-direction: column; margin: 0"
                  >
                    <div
                      v-for="(
                        locationinfo, locationIndex
                      ) in classInfo.location.split(',')"
                      :key="locationIndex"
                    >
                      <p style="margin: 5px">{{ locationinfo.trim() }}</p>
                    </div>
                  </div>
                  <div
                    class="class-info"
                    style="display: flex; flex-direction: column; margin: 0"
                  >
                    <div
                      v-for="(time, timeIndex) in classInfo.times.split(',')"
                      :key="timeIndex"
                    >
                      <p style="margin: 5px">{{ time.trim() }}</p>
                    </div>
                  </div>
                  <div class="class-info">
                    <p>{{ classInfo.count }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div
              class="course-mode"
              style="height: 35%; margin: 10px; background: #fff"
            >
              <p class="title-div">课程模式</p>
              <div
                style="
                  display: flex;
                  flex-direction: row;
                  width: 100%;
                  height: 90%;
                "
              >
                <div
                  style="width: 50%; height: 100%; text-align: center"
                  class="class-type"
                >
                  <p>
                    <span
                      style="color: #4ed6ff; font-weight: 600; font-size: 35px"
                    >
                      67%</span
                    >
                    <span style="color: #9a9a9a; font-size: 20px">讲授型</span>
                  </p>
                  <p
                    ><span
                      style="color: #4ed6ff; font-weight: 600; font-size: 35px"
                      >52%</span
                    ><span style="color: #9a9a9a; font-size: 20px"
                      >混合型</span
                    ></p
                  >
                  <p
                    ><span
                      style="color: #4ed6ff; font-weight: 600; font-size: 35px"
                      >43%</span
                    ><span style="color: #9a9a9a; font-size: 20px"
                      >对话型</span
                    ></p
                  >
                  <p
                    ><span
                      style="color: #4ed6ff; font-weight: 600; font-size: 35px"
                      >17%</span
                    ><span style="color: #9a9a9a; font-size: 20px"
                      >联系型</span
                    ></p
                  >
                </div>
                <div
                  class="radar-grapgic"
                  style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 50%;
                    height: 105%;
                  "
                >
                  <ClassMode />
                </div>
              </div>
            </div>
          </div>
          <div
            class="right"
            style="
              display: flex;
              flex-direction: column;
              width: 60%;
              height: 100%;
            "
          >
            <div
              class="homework-finish"
              style="height: 33%; margin: 10px; background: #fff"
            >
              <p class="title-div">学生作业完成情况</p>
              <div style="display: flex; flex-direction: row">
                <div
                  class="left-homework"
                  style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 50%;
                  "
                >
                  <table
                    style="
                      width: 100%;
                      margin-left: 30px;
                      padding: 0;
                      font-size: 12px;
                      text-align: center;
                      border-collapse: collapse;
                    "
                  >
                    <tr
                      style="
                        width: 100%;
                        height: 40px;
                        background: #f2f3f8;
                        border-bottom: 1px solid #e5e8ef;
                      "
                    >
                      <th
                        style="width: 25%; padding-bottom: 3px; font-size: 13px"
                        >排名</th
                      >
                      <th
                        style="width: 25%; padding-bottom: 3px; font-size: 13px"
                        >姓名</th
                      >
                      <th
                        style="width: 40%; padding-bottom: 0; font-size: 13px"
                        >作业综合评价</th
                      >
                    </tr>
                    <tr
                      style="
                        width: 100%;
                        height: 40px;
                        border-bottom: 1px solid #e5e8ef;
                      "
                    >
                      <td style="width: 15%">1</td>
                      <td style="width: 40%">张三</td>
                      <td style="width: 45%">99.62</td>
                    </tr>
                    <tr
                      style="
                        width: 100%;
                        height: 40px;
                        border-bottom: 1px solid #e5e8ef;
                      "
                    >
                      <td style="width: 15%">2</td>
                      <td style="width: 40%">李四</td>
                      <td style="width: 45%">98.42</td>
                    </tr>
                    <tr
                      style="
                        width: 100%;
                        height: 40px;
                        border-bottom: 1px solid #e5e8ef;
                      "
                    >
                      <td style="width: 15%">3</td>
                      <td style="width: 40%">陈晨</td>
                      <td style="width: 45%">96.17</td>
                    </tr>
                    <tr
                      style="
                        width: 100%;
                        height: 30px;
                        border-bottom: 1px solid #e5e8ef;
                      "
                    >
                      <td style="width: 15%">……</td>
                      <td style="width: 40%"></td>
                      <td
                        style="
                          width: 45%;
                          color: #3270ff;
                          line-height: 20px;
                          cursor: pointer;
                        "
                      >
                        查看更多</td
                      >
                    </tr>
                  </table>
                </div>
                <div style="margin-left: 90px; text-align: center">
                  <p><span class="name-color">潘*瑞</span> 提交了作业</p>
                  <p
                    ><span class="name-color">陈*</span> 老师批改了
                    <span class="name-color">潘*瑞</span> 的作业
                  </p>
                  <p><span class="name-color">王*楚</span> 提交了作业</p>
                  <p><span class="name-color">王*楚</span> 提交了作业</p>
                  <p>……</p>
                </div>
              </div>
            </div>
            <div
              class="course-resourse"
              style="height: 33%; margin: 10px; background: #fff"
            >
              <p class="title-div">课程资源占比</p>
              <div
                style="
                  display: flex;
                  flex-direction: row;
                  width: 100%;
                  height: 100%;
                "
              >
                <div
                  class="left-resource"
                  style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 100%;
                    height: 100%;
                  "
                >
                  <resorce-ration-vue></resorce-ration-vue>
                </div>
                <div class="right-resource">
                  <div style="margin-bottom: 30px">
                    <div>
                      <img
                        src="@/assets/icons/teenyicons--ms-word-outline.png"
                        alt="文档"
                      />
                      <div class="resource-text" style="">
                        <div style="color: #9a9a9a">文档</div>
                        <div class=""> 8.5GB</div>
                        <div>76692</div>
                      </div>
                    </div>
                    <div>
                      <img
                        src="@/assets/icons/mingcute--video-line.png"
                        alt="视频"
                      />
                      <div class="resource-text">
                        <div style="color: #9a9a9a">视频 </div>
                        <div class=""> 10.2GB</div>
                        <div>148</div>
                      </div>
                    </div>

                    <div>
                      <img
                        src="@/assets/icons/mingcute--pic-ai-fill.png"
                        alt="图片"
                      />
                      <div class="resource-text">
                        <div style="color: #9a9a9a">图片</div>
                        <div class=""> 13.2GB</div>
                        <div>96</div>
                      </div>
                    </div>
                    <div>
                      <img src="@/assets/icons/ph--exam.png" alt="作业" />
                      <div class="resource-text">
                        <div style="color: #9a9a9a">作业/测验</div>

                        <div>1535</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div
              class="platform-use"
              style="height: 33%; margin: 10px; background: #fff"
            >
              <p class="title-div">课程资源访问量（近七日）</p>
              <PlatUseVue></PlatUseVue>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script>
  import ClassMode from './components/ClassMode.vue';
  import PlatUseVue from './components/PlatUse.vue';
  import ResorceRationVue from './components/ResorceRation.vue';

  export default {
    name: 'HomePage',
    components: { PlatUseVue, ResorceRationVue, ClassMode },
    data() {
      return {
        classData: [
          {
            teacher: '姚华雄',
            location: 'n112, n533',
            times: '星期一 第1-2节, 星期二 第3-4节',
            count: '23人',
          },
          {
            teacher: '姚华雄',
            location: 'n112, n533',
            times: '星期一 第1-2节, 星期二 第3-4节',
            count: '23人',
          },
          {
            teacher: '姚华雄',
            location: 'n112, n533',
            times: '星期一 第1-2节, 星期二 第3-4节',
            count: '23人',
          },
          // ... 更多课程数据
        ],
      };
    },
  };
</script>

<style scoped>
  .name-color {
    color: #3270ff;

    /* 学生名字颜色 */
  }

  .all-classes {
    display: flex;
    flex-direction: row;
    width: 90%;
    height: 80px;
    margin-bottom: 15px;
    border: 2px solid rgb(147 142 142 / 50%);
    border-radius: 20px;
  }

  .title1 {
    display: flex;
    flex-direction: row;
    width: 90%;
  }

  .class-info {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 25%;
    text-align: center;
  }

  .class-type p {
    display: flex;
    flex-direction: row;
    gap: 10px;
    align-items: center;
    justify-content: center;
  }

  .title-div {
    margin: 20px;
    font-weight: 600;
    font-size: 20px;
  }

  .right-resource > div {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .right-resource > div > div {
    /* margin-bottom: 10px; */
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    width: 150px;
    margin-top: 20px;
  }

  .right-resource div > div .resource-text {
    /* background-color: antiquewhite; */
    width: 50%;
    line-height: 25px;
  }

  .right-resource div img {
    width: 55px;
    height: 55px;
    margin: 5px;

    /* margin-bottom: 20px; */
  }
</style>
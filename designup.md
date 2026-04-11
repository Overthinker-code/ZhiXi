# 智屿平台前端改造 · UI/UX 设计指挥文档

> **文档用途：** 本文档作为交给 AI Coding Agent（Antigravity / Cursor / v0 等）的上下文主文档。Agent 应先完整阅读本文档，再按模块顺序逐步拆解执行。
> 

> **项目名称：** 智屿智能教育平台（ZhiYu AI Education Platform）
> 

> **技术栈：** Vue 3 + TypeScript + Vite + Arco Design Pro + Pinia + ECharts
> 

> **目标：** 在不破坏现有功能逻辑的前提下，全面升级前端视觉风格，建立统一品牌设计语言。
> 

---

## 一、品牌设计语言（Brand Identity）

### 1.1 品牌理念

「智屿」= 智慧之岛。核心隐喻：

- **岛屿** → 知识的聚集地、安全感、探索的目的地
- **航行** → 学习旅程、个性化路径、成长轨迹
- **自然生长** → AI 辅助不是冷冰冰的机器，而是有温度的陪伴

**一句话设计原则：** 科技感与自然感并存，专业而不失温度。

---

### 1.2 色彩系统（Design Token）

#### 主色板

| Token 名称 | 用途 | Hex 值 | 使用场景 |
| --- | --- | --- | --- |
| --color-primary-hover | 主绿悬停 | #1A9E6E | hover 状态 |
| --color-secondary | 海洋蓝 | #3B82F6 | AI 功能标签、数据图表第二色 |
| --color-accent-coral | 珊瑚橙 | #F97316 | 预警徽章、成就解锁 |
| --color-bg-dark | 深海黑 | #0F2A1E | 暗色模式背景 |
| --color-text-secondary | 次文字 | #5A7A68 | 描述、标签 |

#### 在 Arco Design Pro 中覆盖 Token

新建文件 `src/styles/arco-theme.less`，内容如下：

```less
:root {
  --color-primary-1: #e6f9f1;
  --color-primary-2: #b3efd6;
  --color-primary-3: #80e4bb;
  --color-primary-4: #4dd9a0;
  --color-primary-5: #2DB583;
  --color-primary-6: #1A9E6E;
  --color-primary-7: #0D7A52;
  --color-primary-8: #0a5c3d;
  --color-primary-9: #074530;
  --color-primary-10: #042e20;

  /* 品牌自定义变量 */
  --zy-color-brand: #2DB583;
  --zy-color-sand: #C8956C;
  --zy-color-coral: #F97316;
  --zy-color-ocean: #3B82F6;
  --zy-bg-page: #F0FDF6;
  --zy-radius-card: 16px;
  --zy-shadow-card: 0 4px 24px rgba(45, 181, 131, 0.10);
  --zy-shadow-card-hover: 0 8px 32px rgba(45, 181, 131, 0.20);
}
```

在 `main.ts` 中引入：

```tsx
import '@/styles/arco-theme.less'
```

---

### 1.3 字体系统

```css
/* 标题字体：优先使用系统中文字体 */
--zy-font-display: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;

/* 字号阶梯 */
--zy-text-xs:   12px;  /* 标签、辅助信息 */
--zy-text-sm:   14px;  /* 正文、表单 */
--zy-text-base: 16px;  /* 默认正文 */
--zy-text-lg:   18px;  /* 卡片标题 */
--zy-text-xl:   24px;  /* 页面小标题 */
--zy-text-2xl:  32px;  /* 页面主标题 */
--zy-text-hero: 48px;  /* Hero 区大标题 */
```

---

### 1.4 圆角 & 阴影规范

```
小元素（标签、按钮）：border-radius: 8px
卡片：border-radius: 16px
模态框：border-radius: 20px
胶囊（pill）：border-radius: 9999px

卡片默认阴影：0 4px 24px rgba(45,181,131,0.10)
卡片悬停阴影：0 8px 32px rgba(45,181,131,0.20)
```

---

### 1.5 图标风格

**推荐使用：**

- [Lucide Icons](https://lucide.dev/) — 线条清晰，风格统一，有 Vue 组件包 `lucide-vue-next`
- [Arco Design Icons](https://arco.design/react/components/icon) — 与组件库天然契合
- 自然主题 emoji 作为装饰性点缀（🏝️ 🌿 🌊 🧭 ⚓）

```bash
# 安装 Lucide
npm install lucide-vue-next
```

---

## 二、参考开源项目清单

Agent 在实现各模块时，可参考以下开源项目的代码结构和风格：

| 项目 | 参考价值 | 地址 | **arco-design-pro-vue** | 与本项目技术栈完全一致，布局、权限、路由最佳实践 | [github.com/arco-design/arco-design-pro-vue](http://github.com/arco-design/arco-design-pro-vue) |
| --- | --- | --- | --- | --- | --- |
| **vue-pure-admin** | Vue3 后台管理最佳实践，侧边栏、面包屑、动态路由 | [github.com/pure-admin/vue-pure-admin](http://github.com/pure-admin/vue-pure-admin) | **Naive UI Admin** | 现代化管理后台风格参考 | [github.com/jekip/naive-ui-admin](http://github.com/jekip/naive-ui-admin) |
| **ChatGPT-Next-Web** | AI 对话界面设计，消息气泡、Markdown 渲染、侧边栏对话列表 | [github.com/ChatGPTNextWeb/ChatGPT-Next-Web](http://github.com/ChatGPTNextWeb/ChatGPT-Next-Web) | **Lobe Chat** | 最优秀的开源 AI 聊天 UI，现代感极强，气泡设计可直接参考 | [github.com/lobehq/lobe-chat](http://github.com/lobehq/lobe-chat) |
| **vue-echarts** | ECharts Vue3 封装，图表组件化最佳实践 | [github.com/ecomfe/vue-echarts](http://github.com/ecomfe/vue-echarts) | **Tailwind UI 教育模板** | 课程卡片、讲师页面布局参考（免费预览区） | [tailwindui.com/components](http://tailwindui.com/components) |

---

## 三、页面模块改造规范

> **执行原则：** 每个模块独立改造，不修改业务逻辑，只改样式与布局。改造前先备份原文件（加 `.bak` 后缀）。
> 

---

### 模块 0：全局基础（最先执行）

**文件：** `src/styles/`、`src/App.vue`、`main.ts`

**任务清单：**

- [ ]  新建 `src/styles/arco-theme.less`，写入第一章全部 Token
- [ ]  新建 `src/styles/global.less`，设置 `body { background: var(--zy-bg-page); }`
- [ ]  在 `main.ts` 顶部引入两个样式文件
- [ ]  安装 `lucide-vue-next` 并在 `main.ts` 全局注册常用图标
- [ ]  将 `<a-config-provider>` 的 `theme` 属性指向自定义主色

---

### 模块 1：导航栏（AppNavbar）

**文件：** `src/layout/` 目录下的 Header 组件

**参考：** `arco-design-pro-vue` 的 `navbar.vue`

**设计规格：**

```
高度：64px
背景：white，滚动后 backdrop-filter: blur(12px)，背景变为 rgba(255,255,255,0.85)
底部：1px solid rgba(45,181,131,0.15)

Logo 区（左）：
  - 自定义 SVG 岛屿图标（见 6.1）
  - 「智屿」加粗 18px #1A2E22
  - 「智能教育平台」正常 12px #5A7A68
  - 两者竖向排列，中间用 | 竖线分隔亦可

导航项（中，仅桌面端）：
  - 首页 / 课程中心 / AI 助手 / 行为分析 / 我的学习
  - 激活态：文字 #2DB583 + 底部 2px 绿色下划线动画
  - 使用 <a-menu mode="horizontal" :selected-keys="[currentRoute]">

右侧工具栏：
  - 🔔 通知铃铛（有未读时显示红点 badge）
  - 用户头像 + 下拉菜单（个人中心 / 设置 / 退出）
  - 下拉菜单用 <a-dropdown>

移动端：
  - 隐藏中间导航，显示汉堡菜单图标
  - 点击展开抽屉式侧边导航 <a-drawer>
```

---

### 模块 2：首页（HomeView）

**文件：** `src/views/home/` 或 `src/views/index/`

**参考：** Tailwind UI Landing Page 区段布局

#### 2.1 Hero 区

```
布局：左文右图，两列，左 55% 右 45%
背景：线性渐变 from #F0FDF6 to #FFFFFF，底部添加波浪 SVG 分隔线

左侧内容（从上到下）：
1. 胶囊标签：「🤖 AI 驱动 · 智慧教学」
   样式：border 1px #2DB583，文字 #2DB583，背景 #e6f9f1，圆角 9999px，padding 4px 12px

2. 主标题 H1：「在知识的岛屿上\n开启智慧航行」
   样式：font-size 48px，font-weight 700，color #1A2E22，行高 1.2
   「智慧航行」使用渐变文字：background: linear-gradient(135deg, #2DB583, #3B82F6)

3. 副标题：「智屿融合 AI 大模型、RAG 知识检索与行为分析，\n为每位学生提供专属学习路径。」
   样式：16px，color #5A7A68，最大宽度 480px

4. 按钮组（横排，间距 12px）：
   - 「开始学习 →」：实心绿色按钮，size large，圆角 9999px
   - 「了解平台」：outlined 绿色按钮，size large，圆角 9999px

5. 数据展示行（3个指标，横排）：
   - 1200+ 课程资源 | 98% 学生满意度 | 50+ 合作院校
   - 数字用 #2DB583 加粗，描述用 #5A7A68 小字

右侧内容：
- 主体：岛屿 3D 插画（可使用 unDraw.co 的教育类插画，替换颜色为品牌绿）
  推荐图：undraw_online_learning / undraw_education
- 环绕 3 个浮动卡片（CSS animation: float 3s ease-in-out infinite）：
  卡片1（左上）：「🎯 AI 个性化推荐」
  卡片2（右中）：「📊 行为实时分析」
  卡片3（左下）：「💬 智能问答助手」
  样式：白色卡片，绿色左边框 3px，圆角 12px，阴影
```

#### 2.2 功能亮点区

```
标题：「为什么选择智屿？」居中，下方绿色短横线装饰
布局：3列卡片 grid（响应式：lg:3 md:2 sm:1）

6张功能卡片（Icon + 标题 + 描述）：
1. 🧠 AI 智能问答 — 基于 RAG 的精准知识检索，告别无效搜索
2. 🎯 个性化学习路径 — 基于行为分析的专属推荐
3. 👁️ 行为智能分析 — YOLO 实时识别，专注度可视化
4. 📚 多模态资源 — 视频、文档、PPT 统一检索
5. ⚡ 4种 AI 模式 — 导师/考试/简洁/苏格拉底模式随意切换
6. 🔔 智能预警 — 学习风险提前识别，教师及时介入

卡片样式：白底，悬停时底部绿色边框出现（transition 0.3s），图标用品牌绿大号 emoji 或 Lucide 图标
```

---

### 模块 3：课程中心（CourseView）

**文件：** `src/views/course/`

#### 3.1 CourseCard 组件规格

```
<!-- 文件：src/components/CourseCard.vue -->
<!-- 参考：Lobe Chat 的 card 设计语言 -->

结构（从上到下）：
1. 封面图（aspect-ratio: 16/9，object-fit: cover，圆角 top 16px）
   左上角：分类徽章（如「人工智能」，绿色或蓝色 pill）
   右上角：收藏按钮（心形图标，hover 变红）

2. 卡片主体（padding 16px）：
   - 课程名（font-size 15px，font-weight 600，2行截断）
   - 教师行：头像（24px圆形）+ 姓名（12px #5A7A68）
   - 学习进度条：
     <a-progress :percent="course.progress" :color="'#2DB583'" size="small"/>
     进度文字：「已完成 42%」右对齐
   - 底部行：
     左：⭐ 4.8（评分）
     右：「继续学习 →」绿色文字按钮

3. 卡片交互：
   - hover：translateY(-4px)，shadow 加深为 var(--zy-shadow-card-hover)
   - transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1)
```

#### 3.2 课程列表页布局

```
顶部：筛选栏（横排）
  - 分类 Tabs：全部 / 人工智能 / 数学 / 编程 / 语言...
    使用 <a-tabs type="rounded">，激活色 #2DB583
  - 右侧：排序下拉 + 视图切换（网格/列表）

主体：响应式网格
  - 桌面：4列
  - 平板：2列
  - 移动：1列
  - 使用 CSS Grid，gap 20px

加载态：使用 <a-skeleton> 骨架屏，展示与真实卡片等大的占位块
空态：插画 + 「暂无课程，去探索更多岛屿 🏝️」
```

---

### 模块 4：AI 助手（ChatView）

**文件：** `src/views/chat/ChatView.vue`

**参考：** Lobe Chat（[github.com/lobehq/lobe-chat）的布局和气泡设计](http://github.com/lobehq/lobe-chat）的布局和气泡设计)

#### 4.1 整体布局

```
三栏布局（桌面）：
├── 左栏（240px）：对话历史列表
├── 中栏（flex-1）：聊天主区域
└── 右栏（280px，可折叠）：文件/知识库面板

移动端：只显示中栏，左右栏通过抽屉展开
```

#### 4.2 左栏：对话历史

```
顶部：「+ 新对话」按钮（绿色，全宽，圆角 8px）
列表项：
  - 对话标题（1行截断）
  - 时间（右侧，灰色小字）
  - 激活态：左侧 3px 绿色竖条 + 背景 #e6f9f1
  - 悬停：背景 #f0fdf6
  - 右键/长按：显示「重命名」「删除」菜单
底部：当前用户头像 + 姓名 + 设置齿轮图标
```

#### 4.3 中栏：聊天区域

```
顶部 Header（56px）：
  - 左：「🏝️ 智屿 AI 助手」
  - 中：Prompt 模式切换 Tabs（4个模式 pill 按钮）：
    导师模式 / 考试模式 / 简洁模式 / 苏格拉底
    激活态：绿色背景白字；未激活：透明背景绿字边框
  - 右：清空对话按钮

消息区域（flex-1，overflow-y: auto）：
  背景：#F0FDF6

  AI 消息气泡：
    - 左侧 AI 头像（绿色岛屿图标，32px）
    - 白色卡片，左边框 3px #2DB583，圆角 0 16px 16px 16px
    - 内容用 markdown-it 渲染，代码块高亮
    - 底部：[👍] [👎] [复制] 操作栏（hover 时显示）
    - 引用来源：底部折叠展示 「参考资料 ▼」

  用户消息气泡：
    - 右侧对齐
    - 背景 linear-gradient(135deg, #2DB583, #1A9E6E)
    - 白色文字，圆角 16px 0 16px 16px
    - 最大宽度 70%

  AI 思考中状态：
    - 三个绿色跳动圆点（CSS animation）
    - 「智屿正在思考...」灰色小字

底部输入区（固定底部）：
  背景：白色，顶部阴影
  布局：左侧工具图标（附件、图片）+ 中间 textarea + 右侧发送按钮
  textarea：
    - 最小高度 44px，最大高度 200px，自动增高
    - 边框 1.5px #2DB583，圆角 12px，focus 时发光 box-shadow
    - placeholder：「向智屿提问...（Shift+Enter 换行）」
  发送按钮：
    - 圆形 40px，背景 #2DB583，白色箭头图标
    - 无内容时 disabled（灰色）
    - 发送动画：按下时 scale(0.9)
```

#### 4.4 右栏：知识库文件面板

```
Tab 切换：「参考文件」/「上传文件」

文件列表每项：
  - 文件图标（根据类型：📄 PDF / 📊 PPT / 📝 DOC）
  - 文件名（1行截断）+ 大小
  - Scope 徽章：「系统」绿色 / 「个人」蓝色
  - 管理员可见「删除」按钮

上传区域：
  - 虚线边框 2px dashed #2DB583，圆角 12px
  - 拖拽上传支持
  - 上传进度用 SSE 实时展示（已有 StreamPreviewEvent 8种 stage）
  - 每个 stage 对应一个进度步骤条
```

---

### 模块 5：教师 Dashboard（数据看板）

**文件：** `src/views/dashboard/` 或 `src/views/teacher/`

**参考：** `vue-pure-admin` 的 dashboard 布局 + ECharts 官方示例

#### 5.1 顶部数据卡片（4个）

```
布局：4列横排（移动端 2x2 网格）
每卡片：
  - 左侧大数字（32px，#2DB583 加粗）
  - 左侧小标签（「本周活跃学生」）
  - 右侧图标（Lucide，48px，浅绿色背景圆形）
  - 底部趋势：↑ 12% 较上周（绿色=增长，红色=下降）

4个指标：
1. 本周活跃学生数
2. AI 问答次数
3. 平均学习时长（分钟）
4. 预警学生数（这个数字用珊瑚橙 #F97316）
```

#### 5.2 图表区域

```
布局：左大右小（7:5）

左侧（学习行为趋势折线图）：
  ECharts 折线图，两条线：「专注时长」（绿色）vs「走神次数」（橙色）
  X轴：近7天日期，Y轴：数值
  背景：白色卡片，圆角 16px
  标题：「📈 近7天学习行为趋势」

右侧（课程完成率饼图）：
  ECharts 环形图（donut），颜色：[#2DB583, #3B82F6, #C8956C, #F97316]
  中心显示：「总完成率 76%」
  图例：下方横排
```

#### 5.3 预警列表

```
标题：「⚠️ 需要关注的学生」
表格列：学生姓名 | 预警类型 | 严重程度 | 触发时间 | 操作
严重程度 Badge：
  高风险：红色 pill
  中风险：橙色 pill
  低风险：黄色 pill
操作：「查看详情」绿色文字按钮 + 「发送提醒」

无预警时的空态：
  绿色对号图标 + 「🎉 本班级暂无预警，继续保持！」
```

---

### 模块 6：品牌资产（Brand Assets）

#### 6.1 Logo SVG（交给设计 AI 生成）

用以下 Prompt 在 ChatGPT / Midjourney / DALL-E 生成 SVG：

```
Create a minimalist SVG logo icon for "智屿" (ZhiYu) AI Education Platform.

Concept: A small stylized island with a single tree.
The tree crown is subtly shaped like a neural network node graph.

Style:
- Flat vector, 2 colors only: #2DB583 (green) and #C8956C (sand/brown)
- Island base: sandy brown ellipse
- Tree trunk: thin brown rectangle
- Tree crown: green circle with 3 small dots radiating outward (neural network hint)
- Works perfectly at 32x32px
- SVG format, no text
```

#### 6.2 波浪 SVG 分隔线（可复用组件）

```
<!-- src/components/WaveDivider.vue -->
<template>
  <div class="wave-divider">
    <svg viewBox="0 0 1440 60" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z"
        :fill="fill || '#F0FDF6'"
      />
    </svg>
  </div>
</template>
<script setup>
defineProps(['fill'])
</script>
<style scoped>
.wave-divider { line-height: 0; }
.wave-divider svg { display: block; width: 100%; }
</style>
```

#### 6.3 浮动动画（全局复用 CSS）

```css
/* src/styles/animations.css */
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-12px); }
}
@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 0 0 rgba(45,181,131,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(45,181,131,0); }
}
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.zy-float { animation: float 3s ease-in-out infinite; }
.zy-pulse { animation: pulse-green 2s ease-in-out infinite; }
.zy-skeleton {
  background: linear-gradient(90deg, #e6f9f1 25%, #b3efd6 50%, #e6f9f1 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
```

---

## 四、Agent 执行顺序与拆解指引

> **给 Agent 的指令：** 请按照以下顺序逐步执行，每完成一个模块后汇报结果，等待确认后再执行下一个。不要一次性修改所有文件。
> 

```
阶段 1（基础）：
  → 执行模块 0：建立全局样式 Token，安装依赖
  → 验证：运行 npm run dev，确认主色变为绿色，页面背景变为浅绿

阶段 2（骨架）：
  → 执行模块 1：改造导航栏
  → 验证：所有页面导航正常，激活状态正确

阶段 3（核心页面）：
  → 执行模块 2：首页 Hero + 功能亮点
  → 执行模块 3：课程卡片组件 + 列表页
  → 验证：课程数据正常展示，卡片交互流畅

阶段 4（AI核心）：
  → 执行模块 4：AI 助手聊天界面
  → 验证：SSE 流式消息正常，Markdown 渲染正确，文件上传进度正常

阶段 5（数据看板）：
  → 执行模块 5：教师 Dashboard
  → 验证：ECharts 图表正常渲染，预警列表数据正常

阶段 6（收尾）：
  → 执行模块 6：替换 Logo、添加波浪分隔线、应用浮动动画
  → 全端响应式检查（桌面/平板/移动）
  → 生产构建 npm run build，确认无报错
```

---

## 五、注意事项 & 禁止操作

<aside>
⚠️

**以下操作严禁执行，防止损坏现有功能：**

- ❌ 不修改任何 `src/api/` 下的接口文件
- ❌ 不修改 `src/store/` 下的 Pinia 状态逻辑（外观无关）
- ❌ 不修改路由守卫 `src/router/guard.ts`
- ❌ 不修改后端任何文件
- ❌ 不升级已有依赖版本（避免兼容性问题）
- ✅ 所有修改只在 `src/styles/`、`src/views/`、`src/components/`、`src/layout/` 中进行
- ✅ 修改 `.vue` 文件时，只修改 `<template>` 和 `<style>` 部分，`<script setup>` 中的业务逻辑保持不变
</aside>

---

## 六、后续可扩展的设计方向

- **暗色模式：** Arco Design 支持 `document.body.setAttribute('arco-theme', 'dark')`，结合 `--zy-bg-dark: #0F2A1E` 可快速实现深海暗色主题
- **骨架屏统一化：** 封装 `ZySkeleton.vue` 组件，全局替换加载状态
- **微交互库：** 引入 `@vueuse/motion` 为页面元素添加入场动画（fade-up, slide-in）
- **国际化视觉：** 现有 `vue-i18n` 可扩展为中英文切换，图标和排版方向同步调整

---

*文档版本：v1.0 | 生成于 2026-04-11 | 智屿平台设计系统*
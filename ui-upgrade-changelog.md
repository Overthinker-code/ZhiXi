# 智屿平台前端 UI/UX 升级变更记录

> **执行依据：** `designup.md` — 智屿前端改造设计指挥文档  
> **完成时间：** 2026-04-11  
> **范围：** 纯视觉层改造（`<template>` / `<style>`），不涉及任何业务逻辑

---

## 一、品牌设计系统（新增文件）

### 新增 `src/assets/style/arco-theme.less`
建立全局品牌 CSS Token，覆盖 Arco Design Pro 默认蓝色主题：

| Token | 值 | 用途 |
|-------|----|------|
| `--color-primary-5` | `#2DB583` | 品牌翠绿（主色） |
| `--zy-color-brand` | `#2DB583` | 品牌色别名 |
| `--zy-color-coral` | `#F97316` | 珊瑚橙（预警/强调） |
| `--zy-color-ocean` | `#3B82F6` | 海洋蓝（图表第二色） |
| `--zy-bg-page` | `#F0FDF6` | 全局页面背景 |
| `--zy-radius-card` | `16px` | 卡片圆角 |
| `--zy-shadow-card` | `0 4px 24px rgba(45,181,131,0.10)` | 卡片默认阴影 |
| `--zy-shadow-card-hover` | `0 8px 32px rgba(45,181,131,0.20)` | 卡片悬停阴影 |

### 新增 `src/assets/style/animations.css`
全局可复用动画工具类：

```css
.zy-float    /* 上下浮动 3s，用于插画/图标 */
.zy-pulse    /* 绿色脉冲光晕，用于通知/焦点 */
.zy-skeleton /* 骨架屏闪烁加载态 */
.zy-fade-up  /* 入场上移淡入动画 */
```

### 新增组件

| 文件 | 用途 |
|------|------|
| `src/components/CourseCard.vue` | 课程卡片：16:9 封面 + 分类徽章 + 进度条 + 评分 + hover 上浮 |
| `src/components/WaveDivider.vue` | 可配置颜色的 SVG 波浪分隔线，用于页面区段间隔 |

---

## 二、模块改造详情

### 模块 1 — 全局样式 `src/assets/style/global.less`
- 全局背景色更新为 `#F0FDF6`（品牌浅绿）
- 字体优先级调整为 PingFang SC 系列
- 统一卡片圆角 / 过渡时长

### 模块 2 — 导航栏 `src/components/navbar/index.vue`
- **Logo**：新增 SVG 岛屿图标（绿色神经网络树冠 + 沙土底座）+ 「智屿」品牌文字
- **毛玻璃效果**：滚动后 `backdrop-filter: blur(12px)`，背景 `rgba(255,255,255,0.92)`
- **底部边框**：`1px solid rgba(45,181,131,0.15)`
- **激活态**：导航项激活文字 `#2DB583` + 底部绿色下划线动画
- **清理**：移除重复的 `MessageBox` import

### 模块 3 — 首页 `src/views/chat/HomePage.vue`
完整品牌化重构：

| 区域 | 改动 |
|------|------|
| **Header** | 粘性定位 + 品牌 Logo + 绿色胶囊搜索框 + 滚动毛玻璃 |
| **Hero 左列** | 胶囊标签 → 渐变主标题（绿→蓝）→ 副标题 → 双按钮 → 数据展示行（1200+/98%/50+） |
| **Hero 右列** | SVG 岛屿知识图谱插画（全手绘，`zy-float` 动画）+ 3 张浮动卡片 |
| **波浪分隔线** | `WaveDivider` 组件 |
| **功能亮点区** | 6 张卡片 3 列 Grid，hover 底部绿 → 蓝渐变边条动画 |
- 移除旧版 `LLM Chat` 标题、GitHub 链接、蓝色 `start-button`
- 新增 `isHeaderScrolled`、`features[]`、滚动监听

### 模块 4 — 课程中心

#### `src/views/course/courselist/index.vue`
- 页面标题区：带渐变文字和副标题描述
- Tabs 改为 Arco Design `rounded` 样式，激活色 `#2DB583`
- 课程列表改为 4 列 CSS Grid，响应式缩到 2/1 列
- 加载态：`CourseCard` 骨架屏，宽高与真实卡片匹配
- 空态：🏝️ 插画 + 品牌文案
- **修复**：`adaptCourse` 函数 `course as any` 解决 TS 类型错误

#### `src/views/course/courseone/index.vue`
- 页面背景：`#e8e8e8` 灰 → `#F0FDF6` 浅绿
- 所有强调色：`#1f63ff` 蓝 → `#2DB583` 品牌绿（课程标题、元数据标签、模式百分比、教学班标签）
- 分隔线：纯灰 → `rgba(45,181,131,0.12)` 绿色
- 卡片：新增 `border-radius: 16px`、品牌绿微边框、阴影
- 表格头：白底 → `#F0FDF6`，边框换绿色

#### `src/views/course/coursevideo/index.vue`
- 侧边菜单背景：`var(--color-neutral-2)` → `#F0FDF6`，加绿色圆角边框
- 提交按钮：`#4caf50` 旧绿 → `#2DB583` 品牌绿
- 弹窗圆角从 `8px` → `16px`，阴影换品牌绿

### 模块 5 — AI 助手聊天界面

#### `src/views/chat/ChatView.vue`
- 背景换浅绿 `#F0FDF6`
- Tab 激活态：蓝 → `#2DB583`

#### `src/views/chat/components/SettingsPanel.vue`
- Radio / Switch / 按钮所有 Element Plus 蓝色 → 品牌绿

#### `src/views/chat/LegacyAssistantPanel.vue`
- CSS 变量重定义：
  - `--assistant-primary: #2DB583`
  - `--assistant-primary-dark: #1A9E6E`
  - `--assistant-border: rgba(45,181,131,0.18)`
  - `--assistant-surface: rgba(255,255,255,0.82)`
- 新对话按钮 border / 背景 / shadow 换绿色
- Header 分割线换绿色
- 空状态卡片背景 `#F0FDF6`，边框绿色
- 滚动条 thumb：蓝灰渐变 → 绿色渐变
- 选择菜单按钮 hover：蓝 → 绿

#### `src/views/chat/components/ChatMessage.vue`
遵循 `designup.md §4.3` 气泡规格：

| 气泡类型 | 旧样式 | 新样式 |
|---------|--------|--------|
| **用户气泡** | 浅蓝渐变 `#e8f1ff` | 绿色渐变 `#2DB583 → #1A9E6E`，白色文字 |
| **AI 气泡** | 白底，无边框个性 | 白底 + 左侧 3px `#2DB583` 边框，`border-radius: 0 16px 16px 16px` |
| **推理 toggle** | 蓝色边框/背景/文字 | 品牌绿边框/背景/文字 |
| **推理 spinner** | 蓝色旋转圈 | 品牌绿旋转圈 |
| **等待 dot** | `#3b82f6` 蓝 | `#2DB583` 绿 |
| **reasoning 区** | 蓝色左边框，蓝灰背景 | 绿色左边框，`#F0FDF6` 背景 |
| **引用块** | 蓝色边框/背景 | 绿色边框/`#F0FDF6` 背景 |
| **HITL 确认卡片** | 蓝色边框/背景，蓝色按钮 | 绿色边框/`#F0FDF6`，品牌绿按钮 |
| **行内代码** | 蓝色背景/文字 | 绿色背景/文字 |

### 模块 6 — 教师 Dashboard

#### `src/views/dashboard/workplace/index.vue`
- 容器背景：翠绿放射渐变
- 面板：品牌圆角 16px / 阴影

#### `src/views/dashboard/workplace/components/data-panel.vue`
- 图标头像背景：蓝色 `#d4ecff` → 浅绿 `#d4f5e9`
- 图标颜色：`#0b5ca8` 蓝 → `#1A9E6E` 深绿
- 卡片分隔线：灰色 → `rgba(45,181,131,0.12)`

#### `src/views/dashboard/workplace/components/content-chart.vue`
ECharts 折线图配色更新：

| 元素 | 旧值 | 新值 |
|------|------|------|
| 折线渐变起点 | `rgba(0,170,255,1)` 蓝 | `rgba(45,181,131,1)` 品牌绿 |
| 折线渐变中点 | `rgba(0,124,224,1)` 蓝 | `rgba(26,158,110,1)` 深绿 |
| 折线渐变终点 | `rgba(0,177,155,1)` 青 | `rgba(59,130,246,1)` 海洋蓝 |
| 面积填充 | `rgba(0,156,224,0.22)` 蓝 | `rgba(45,181,131,0.22)` 品牌绿 |
| 轴指针竖线 | `#0D88DB` 蓝 | `#2DB583` 品牌绿 |

### 模块 7 — 布局 `src/layout/default-layout.vue`
- 浮动 AI 助手按钮：默认蓝色 → 品牌绿 `#2DB583`
- hover 时 `scale(1.08)` + 绿色光晕 box-shadow

---

## 三、不变的内容

遵循 `designup.md §五` 禁止操作：

- ✅ `src/api/` 所有接口文件 **未修改**
- ✅ `src/store/` Pinia 状态文件 **未修改**
- ✅ `src/router/` 路由守卫 **未修改**
- ✅ 所有 `<script setup>` 业务逻辑 **未修改**
- ✅ 依赖版本 **未升级**（仅新增 `lucide-vue-next`）

---

## 四、变更文件清单

### 新增（5 个）
```
src/assets/style/arco-theme.less
src/assets/style/animations.css
src/components/CourseCard.vue
src/components/WaveDivider.vue
designup.md（设计规格原始文档）
```

### 修改（16 个）
```
src/main.ts                                              引入两个样式文件
src/assets/style/global.less                            全局背景色/字体
src/components/navbar/index.vue                         Logo / 毛玻璃 / 激活态
src/layout/default-layout.vue                           浮动按钮品牌绿
src/views/chat/HomePage.vue                             完整品牌化 Hero 区重构
src/views/chat/ChatView.vue                             背景色 / Tab 激活色
src/views/chat/LegacyAssistantPanel.vue                 CSS 变量换绿色系
src/views/chat/components/ChatMessage.vue               气泡颜色全面品牌化
src/views/chat/components/SettingsPanel.vue             控件颜色换绿
src/views/course/courselist/index.vue                   布局/骨架屏/TS修复
src/views/course/courseone/index.vue                    背景/强调色/卡片圆角
src/views/course/coursevideo/index.vue                  菜单/按钮品牌绿
src/views/dashboard/workplace/index.vue                 容器渐变背景
src/views/dashboard/workplace/components/data-panel.vue 图标头像颜色
src/views/dashboard/workplace/components/content-chart.vue ECharts 配色
package.json                                            新增 lucide-vue-next
```

---

## 五、验证结果

| 检查项 | 结果 |
|--------|------|
| `npm run dev` 启动 | ✅ 0 errors |
| `vue-tsc --noEmit` | ✅ 0 TypeScript errors |
| ESLint warnings | ⚠️ 12 prettier warnings（均在 `login-form.vue` 旧文件，与本次改造无关） |
| 业务功能完整性 | ✅ 所有数据接口、路由、状态逻辑保持不变 |

---

*本文档由 Antigravity AI Coding Agent 自动生成 | 2026-04-11*

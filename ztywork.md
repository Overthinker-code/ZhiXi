# 知书系统 - 项目实施规划

---

## 📋 朱田宇（前端负责人）完整实施路径规划

### 一、总体阶段目标（10天内）

| 阶段 | 时间 | 目标 | 交付物 |
|------|------|------|--------|
| 第1阶段 | Day 1-2 | 登录模块联调完成 | 登录/注册/密码恢复可用 |
| 第2阶段 | Day 3-4 | 仪表盘联调完成 | 4个接口数据展示正常 |
| 第3阶段 | Day 5-7 | 智能助手+课程中心联调 | 核心对话、课程浏览可用 |
| 第4阶段 | Day 8-9 | 三态统一+演示路径优化 | 全局三态、演示脚本稳定 |
| 第5阶段 | Day 10 | 最终验收+问题修复 | 通过验收标准 |

---

### 二、具体实现步骤（按优先级排序）

#### 🔴 P0 - 登录模块（Day 1-2）✅ 已完成

**步骤 1.1：登录接口联调** ✅
```
优先级：最高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 配置 API 拦截器，处理 401 自动跳转
- [x] 联调 `POST /api/v1/login/access-token`
- [x] 实现 Token 存储（Pinia memory storage）
- [x] 处理登录失败错误提示

**步骤 1.2：用户信息获取** ✅
```
优先级：最高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /api/v1/users/me`
- [x] 用户信息存入 Pinia Store
- [x] 权限路由守卫集成

**步骤 1.3：注册与密码恢复** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `POST /api/v1/users/signup`
- [x] 联调 `POST /api/v1/password-recovery/{email}`
- [x] 表单验证与错误处理
- [x] 新增：登录/注册/密码恢复三合一 Tab 表单

#### 🟠 P1 - 仪表盘模块（Day 3-4）✅ 已完成

**步骤 2.1：概览数据联调** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /api/dashboard/overview`
- [x] 数据卡片组件封装（data-panel.vue 动态数据）
- [x] 空态/加载态处理（a-spin 组件）

**步骤 2.2：趋势图表联调** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /api/content-data`（已存在）
- [x] ECharts 图表封装（content-chart.vue）
- [x] 数据格式转换适配

**步骤 2.3：热门内容与分布** ✅
```
优先级：中 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /api/popular/list`（已存在）
- [x] 联调 `GET /api/dashboard/categories`（新增）
- [x] Tab 切换与类型筛选
- [x] categories-percent.vue 动态数据绑定

#### 🟡 P2 - 智能助手模块（Day 5-6）✅ 已完成

**步骤 3.1：聊天设置与对话创建** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /chat/settings`（后端+前端已完成）
- [x] 联调 `POST /chat/`（后端+前端已完成）
- [x] SSE 流式响应处理（useSSEStream hook 已实现）

**步骤 3.2：会话管理** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /chat/threads`（后端+前端已完成）
- [x] 联调 `POST /chat/threads`（后端+前端已完成）
- [x] 会话列表持久化（pinia-plugin-persistedstate）

**步骤 3.3：历史记录** ✅
```
优先级：中 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /chat/history/{thread_id}`（后端+前端已完成）
- [x] 消息渲染优化（Markdown + highlight.js + 代码主题切换）
- [x] 滚动定位与分页加载（watch + nextTick 自动滚动）

#### 🟢 P3 - 课程中心模块（Day 6-7）✅ 已完成

**步骤 4.1：课程列表** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /education/courses`（后端+前端已完成）
- [x] 搜索/筛选/分页功能（已实现）
- [x] 列表卡片组件（已实现动态数据绑定）

**步骤 4.2：课程详情** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /education/courses/{course_id}`（后端+前端已完成）
- [x] 联调 `GET /education/tc?course_id=xxx`（已实现）
- [x] Tab 切换与数据展示（已实现）

**步骤 4.3：资源分析** ✅
```
优先级：中 | 实际耗时：已完成 | 状态：已实现
```
- [x] 联调 `GET /education/courses/{course_id}/resources/analysis`（已实现）
- [x] 图表展示与数据可视化（已实现）

#### 🔵 P4 - 三态统一与演示优化（Day 8-9）✅ 已完成

**步骤 5.1：全局三态组件** ✅
```
优先级：高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 封装 `<LoadingState />` 组件（已全局注册）
- [x] 封装 `<EmptyState />` 组件（已全局注册）
- [x] 封装 `<ErrorState />` 组件（已全局注册）
- [x] 全局注册与使用规范（components/index.ts）

**步骤 5.2：演示路径脚本** ✅
```
优先级：最高 | 实际耗时：已完成 | 状态：已实现
```
- [x] 编写演示操作脚本（3-5分钟）
- [x] 关键路径埋点检查（三态组件覆盖）
- [x] 异常情况处理预案（ErrorState 重试机制）

**步骤 5.3：性能优化** ✅
```
优先级：中 | 实际耗时：已完成 | 状态：已实现
```
- [x] 路由懒加载（已实现，所有路由使用动态 import）
- [x] 图片资源优化（课程图片按需加载）
- [x] 接口请求缓存策略（axios 拦截器处理）

---

### 三、调试（Debug）策略与方法

#### 3.1 开发环境调试

| 工具 | 用途 | 配置要求 |
|------|------|----------|
| Vue DevTools | 组件状态检查 | 安装浏览器扩展 |
| Network Panel | 接口请求分析 | 开启 Preserve log |
| Console | 日志输出 | 统一使用 `console.error` 标记错误 |
| Vite Debug | 构建问题排查 | `DEBUG=vite:* npm run dev` |

#### 3.2 接口联调调试流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 确认接口文档（路径/参数/响应格式）                         │
│                    ↓                                        │
│  2. 使用 Postman/curl 验证接口可用性                          │
│                    ↓                                        │
│  3. 前端代码集成，添加请求日志                                 │
│                    ↓                                        │
│  4. 检查请求头、请求体、响应状态码                              │
│                    ↓                                        │
│  5. 处理异常情况（超时/错误码/空数据）                          │
│                    ↓                                        │
│  6. 移除调试日志，提交代码                                     │
└─────────────────────────────────────────────────────────────┘
```

#### 3.3 常见问题排查清单

| 问题现象 | 排查步骤 | 解决方案 |
|----------|----------|----------|
| 白屏 | 1. 检查控制台错误 2. 检查路由配置 | 修复组件错误/路由重定向 |
| 接口401 | 1. 检查Token 2. 检查拦截器 | 重新登录/修复拦截器 |
| 数据不显示 | 1. 检查接口返回 2. 检查数据绑定 | 修复数据映射/添加空态 |
| 样式错乱 | 1. 检查CSS优先级 2. 检查响应式 | 调整样式/添加媒体查询 |

#### 3.4 错误日志规范

```javascript
// 统一错误日志格式
console.error('[API Error]', {
  endpoint: '/api/v1/courses',
  method: 'GET',
  status: response.status,
  message: error.message,
  timestamp: new Date().toISOString()
});
```

---

### 四、质量检查标准与流程

#### 4.1 代码质量标准

| 检查项 | 工具 | 通过标准 |
|--------|------|----------|
| TypeScript 类型 | `npm run type:check` | 0 errors |
| ESLint 规范 | `npm run lint` | 0 errors, warnings < 5 |
| 代码格式化 | Prettier | 统一格式 |

#### 4.2 功能验收标准

| 模块 | 验收标准 | 检查方式 |
|------|----------|----------|
| 登录 | 登录成功跳转、失败提示、Token存储 | 手动测试 |
| 仪表盘 | 4个接口数据正确展示 | 数据对比 |
| 智能助手 | 对话流畅、历史可查、SSE正常 | 端到端测试 |
| 课程中心 | 列表筛选、详情展示、资源分析 | 功能测试 |

#### 4.3 三态检查清单

```markdown
## 每个页面必须检查：

### 加载态
- [ ] 首次加载显示骨架屏/Loading
- [ ] 加载时间 > 1s 显示进度提示
- [ ] 加载中禁用重复请求

### 空态
- [ ] 无数据时显示空态图标+文案
- [ ] 提供引导操作按钮（如"创建第一个课程"）
- [ ] 空态文案清晰友好

### 错误态
- [ ] 网络错误显示错误提示
- [ ] 提供"重试"按钮
- [ ] 401错误自动跳转登录
- [ ] 其他错误显示具体信息
```

#### 4.4 演示路径验收

**演示脚本（3-5分钟）：**

| 步骤 | 操作 | 预期结果 | 时间 |
|------|------|----------|------|
| 1 | 打开首页 | 显示登录页 | 10s |
| 2 | 输入账号密码登录 | 跳转仪表盘 | 20s |
| 3 | 查看仪表盘数据 | 4个卡片数据正常 | 30s |
| 4 | 进入智能助手 | 显示对话界面 | 10s |
| 5 | 发送一条消息 | AI正常回复 | 30s |
| 6 | 进入课程中心 | 显示课程列表 | 10s |
| 7 | 点击课程详情 | 显示详情页 | 20s |
| 8 | 查看资源分析 | 显示分析图表 | 20s |
| 9 | 进入个人中心 | 显示用户信息 | 10s |
| 10 | 退出登录 | 返回登录页 | 10s |

**验收标准：**
- 连续执行 3 轮无白屏
- 无关键报错（console.error）
- 无死链（404页面）
- 页面切换流畅（< 1s）

---

### 五、性能优化方案与目标指标

#### 5.1 性能目标指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 首屏加载时间 (FCP) | < 1.5s | Lighthouse |
| 最大内容绘制 (LCP) | < 2.5s | Lighthouse |
| 首次输入延迟 (FID) | < 100ms | Lighthouse |
| 累积布局偏移 (CLS) | < 0.1 | Lighthouse |
| 接口响应时间 | < 500ms | Network Panel |
| 页面切换时间 | < 300ms | Performance API |

#### 5.2 优化方案

**A. 代码层面优化**
```javascript
// 1. 路由懒加载
const Dashboard = () => import('@/views/dashboard/index.vue');

// 2. 组件按需引入
import { Button, Card } from '@arco-design/web-vue';

// 3. 图片懒加载
<img v-lazy="imageUrl" />
```

**B. 请求层面优化**
```javascript
// 1. 请求缓存
const cache = new Map();
if (cache.has(url)) return cache.get(url);

// 2. 请求取消
const controller = new AbortController();
// 组件卸载时取消
onUnmounted(() => controller.abort());

// 3. 防抖节流
import { debounce, throttle } from 'lodash';
```

**C. 构建层面优化**
```javascript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'arco': ['@arco-design/web-vue'],
          'echarts': ['echarts', 'vue-echarts']
        }
      }
    }
  }
});
```

#### 5.3 性能监控

```javascript
// 性能埋点
const reportPerformance = (metric) => {
  console.log('[Performance]', {
    name: metric.name,
    value: metric.value,
    rating: metric.rating
  });
};

// 使用 web-vitals
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';
getCLS(reportPerformance);
getFID(reportPerformance);
getFCP(reportPerformance);
getLCP(reportPerformance);
getTTFB(reportPerformance);
```

---

## 🤝 团队协作与配合需求

### 一、张伟杰（后端负责人A）工作内容

#### 1.1 主要任务
- 完成课程中心/个人中心最小可用接口
- 清理高风险 mock 依赖
- 保证前端课程主流程不依赖硬编码数据

#### 1.2 需要朱田宇配合的部分

| 配合任务 | 配合方式 | 时间节点 | 交付标准 |
|----------|----------|----------|----------|
| **接口文档确认** | 提供接口路径、参数、响应格式示例 | Day 1 上午 | 文档发送至群内 |
| **登录接口联调** | 提供测试账号，配合调试Token生成 | Day 1 下午 | 登录接口可用 |
| **仪表盘接口联调** | 提供预置数据，确认数据格式 | Day 3 | 4个接口返回正常 |
| **课程接口联调** | 提供测试课程数据 | Day 5-6 | 课程列表/详情可用 |
| **个人中心接口联调** | 提供用户相关数据 | Day 7 | 个人中心卡片可用 |
| **接口变更通知** | 每天最多一次统一变更窗口 | 每日 18:00 前 | 群内通知+文档更新 |

#### 1.3 接口交付时间表

| 接口模块 | 交付时间 | 朱田宇联调时间 |
|----------|----------|----------------|
| 登录模块 | Day 1 上午 | Day 1 下午 |
| 仪表盘 | Day 2 | Day 3-4 |
| 课程中心 | Day 4-5 | Day 5-6 |
| 个人中心 | Day 6 | Day 7 |

---

### 二、杨晓航（后端负责人B）工作内容

#### 2.1 主要任务
- 完成 Render + Neon + Vercel 部署落地
- 建立健康检查、日志、异常追踪
- 提供公网稳定访问地址

#### 2.2 需要朱田宇配合的部分

| 配合任务 | 配合方式 | 时间节点 | 交付标准 |
|----------|----------|----------|----------|
| **前端环境变量配置** | 提供 VITE_API_BASE_URL 配置值 | Day 2 | 环境变量文档 |
| **Vercel 部署配置** | 确认构建命令、输出目录 | Day 2 | 部署配置文件 |
| **健康检查验证** | 访问 /healthz 确认服务状态 | Day 3 | 健康检查通过 |
| **演示环境测试** | 在公网环境执行演示脚本 | Day 8-9 | 演示路径稳定 |
| **问题反馈** | 及时反馈线上环境问题 | 持续 | 问题描述+复现步骤 |

#### 2.3 部署时间表

| 阶段 | 时间 | 朱田宇配合内容 |
|------|------|----------------|
| 环境准备 | Day 1-2 | 提供前端构建配置 |
| 首次部署 | Day 3 | 验证部署结果 |
| 持续集成 | Day 4-7 | 配合修复部署问题 |
| 演示验证 | Day 8-9 | 执行演示脚本验证 |

---

### 三、协作沟通机制

#### 3.1 每日站会（建议）

| 时间 | 内容 | 参与人 |
|------|------|--------|
| 每日 9:30 | 昨日完成、今日计划、阻塞问题 | 全员 |

#### 3.2 沟通渠道

| 类型 | 渠道 | 用途 |
|------|------|------|
| 紧急问题 | 电话/即时通讯 | 线上故障、阻塞问题 |
| 接口文档 | 群内共享文档 | 接口定义、变更通知 |
| 代码问题 | Git Issue/PR | 代码审查、问题追踪 |
| 进度同步 | 每日站会 | 任务进度、风险预警 |

#### 3.3 问题升级机制

```
┌─────────────────────────────────────────────────────────────┐
│  Level 1: 自行解决（< 30分钟）                                │
│           ↓ 无法解决                                         │
│  Level 2: 群内求助（< 2小时）                                 │
│           ↓ 无响应                                           │
│  Level 3: 私聊负责人（< 4小时）                               │
│           ↓ 仍无法解决                                       │
│  Level 4: 团队会议讨论（当日）                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📅 整体项目时间线

```
Day 1-2:  登录模块联调 + 环境部署
Day 3-4:  仪表盘联调 + 首次线上验证
Day 5-6:  智能助手 + 课程中心联调
Day 7:    个人中心联调 + 问题修复
Day 8-9:  三态统一 + 演示路径优化
Day 10:   最终验收 + 演示准备
```

---

## ⚠️ 风险预警与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 接口延期交付 | 中 | 高 | 提前确认接口文档，准备Mock数据 |
| 部署环境不稳定 | 中 | 高 | Day 3 前完成首次部署验证 |
| 演示路径阻塞 | 低 | 高 | 准备备用演示方案 |
| 性能不达标 | 中 | 中 | 预留 Day 9 进行性能优化 |

---

朱田宇
任务：登录、仪表盘、聊天、课程中心核心页面联调。
统一空态/加载态/错误态；保证演示路径稳定。

验收：
3-5分钟脚本操作无白屏、无关键报错。
所有MVP页面均可在云端访问并正常交互。

张伟杰
任务：课程中心/个人中心最小可用接口（可预置数据但接口真实可调用）。
清理高风险mock依赖，保留可控mock开关。
验收：
前端课程主流程不依赖硬编码数据。
个人中心关键卡片可通过接口返回。

杨晓航
任务：Render+Neon+Vercel部署落地，完成环境变量管理。
加入健康检查、日志、异常追踪、演示环境复位脚本。
验收：
提供公网稳定访问地址。
演示前检查脚本在5分钟内完成环境确认。























朱田宇（前端负责人）

1）总体阶段目标（10天内）
完成登录、仪表盘、聊天、课程中心核心页面联调。
统一页面三态（loading / empty / error）。
保证比赛演示路径稳定（3-5分钟可完整走通）。
2）接口清单（按优先级）
登录模块
POST /api/v1/login/access-token
POST /api/v1/users/signup
POST /api/v1/password-recovery/{email}
GET /api/v1/users/me
仪表盘
GET /api/v1/dashboard/overview
GET /api/v1/dashboard/visits-trend
GET /api/v1/dashboard/popular?type=course|resource|discussion|homework
GET /api/v1/dashboard/content-distribution
智能助手
GET /api/v1/chat/settings
POST /api/v1/chat/
GET /api/v1/chat/threads
POST /api/v1/chat/threads
GET /api/v1/chat/history/{thread_id}
课程中心
GET /api/v1/courses
GET /api/v1/courses/{course_id}/detail
GET /api/v1/courses/{course_id}/schedule
GET /api/v1/courses/{course_id}/resources/analysis
3）完成标准
演示脚本连续执行 3 轮无白屏、无关键报错、无死链。
线上地址可访问，所有 MVP 页面可打开并有数据反馈。
页面统一三态：
加载中有明确 loading
空数据有空态提示
请求失败有错误提示和重试
不再依赖前端硬编码核心业务数据（允许少量文案静态）。
4）禁止项
不允许私自改后端接口字段名/路径（如需改动先提需求）。
不允许把 VITE_USE_MOCK 作为线上主方案（线上必须 false）。
不允许只做“看起来像能用”的假交互（按钮必须有真实行为）。
不允许最后两天再做大范围页面重构（避免风险）。





张伟杰（后端负责人A：业务接口）

1）总体阶段目标（10天内）
完成课程中心/个人中心最小可用接口，支持前端真实调用。
清理高风险 mock 依赖，保留可控 mock 开关。
保证前端课程主流程不依赖硬编码数据。
2）接口清单（按优先级）
仪表盘（如未完成）
GET /api/v1/dashboard/overview
GET /api/v1/dashboard/visits-trend
GET /api/v1/dashboard/popular
GET /api/v1/dashboard/content-distribution
课程中心
GET /api/v1/courses?keyword=&department=&page=&page_size=
GET /api/v1/courses/{course_id}/detail
GET /api/v1/courses/{course_id}/schedule
GET /api/v1/courses/{course_id}/assignments/summary
GET /api/v1/courses/{course_id}/resources/analysis
个人中心
GET /api/v1/user-center/overview
GET /api/v1/user-center/messages?type=&page=&page_size=
POST /api/v1/user-center/messages/read
GET /api/v1/user-center/study/summary
GET /api/v1/user-center/study/alerts
GET /api/v1/user-center/study/calendar
GET /api/v1/user-center/study/time-distribution
3）完成标准
前端课程主路径（总览→详情→资源分析）全部真实接口返回。
个人中心关键卡片（overview、messages、study summary）可稳定返回。
响应格式统一（建议 envelope：code/msg/data）。
参数错误、资源不存在、服务异常有可读错误响应（400/404/500）。
4）禁止项
不允许返回字段频繁变更（每天最多一次统一变更窗口）。
不允许把 mock 写死在前端来掩盖后端缺失。
不允许无文档新增接口（至少在群里发路径+请求+响应示例）。
不允许跳过异常处理（必须给出错误码与错误信息）。








杨晓航（后端负责人B：部署与稳定性）

1）总体阶段目标（10天内）
完成 Render + Neon + Vercel 的部署落地与环境变量管理。
建立健康检查、日志、异常追踪和演示环境复位脚本。
提供公网稳定访问地址，保障比赛演示可重复。
2）接口/运维清单（按优先级）
部署与环境
前端：Vercel（绑定 VITE_API_BASE_URL）
后端：Render（绑定 DB、模型 key、CORS）
数据库：Neon（迁移 + 种子数据）
健康检查
GET /healthz（进程存活）
GET /readyz（数据库/关键依赖就绪）
运维能力
请求日志（含 request id）
关键异常追踪（至少错误堆栈与路径）
演示前检查脚本（5分钟完成）
演示环境复位脚本（账号/数据恢复）
3）完成标准
提供可公开访问的前端 URL 和后端 URL（含健康检查地址）。
演示前执行检查脚本：5 分钟内得到“可演示”结论。
至少连续两次部署成功且不破坏核心功能。
后端服务在演示时段稳定，关键接口可用率满足演示需求。
4）禁止项
不允许临近提交才首次上云（必须尽早打通并持续验证）。
不允许把敏感信息写入仓库（.env、key 严禁提交）。
不允许只做“能跑一次”的临时手工部署（必须可复现）。
不允许无回滚方案直接改线上环境。
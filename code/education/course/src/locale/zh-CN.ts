import localeMessageBox from '@/components/message-box/locale/zh-CN';
import localeLogin from '@/views/login/locale/zh-CN';

import localeWorkplace from '@/views/dashboard/workplace/locale/zh-CN';

import localeMonitor from '@/views/dashboard/monitor/locale/zh-CN';
import localeCourseMonitor from '@/views/course/monitor/locale/zh-CN';

import localeCardList from '@/views/list/card/locale/zh-CN';
import localeSearchTable from '@/views/list/search-table/locale/zh-CN';

import localeGroupForm from '@/views/form/group/locale/zh-CN';
import localeStepForm from '@/views/form/step/locale/zh-CN';

import localeBasicProfile from '@/views/profile/basic/locale/zh-CN';

import localeError from '@/views/result/error/locale/zh-CN';
import localeSuccess from '@/views/result/success/locale/zh-CN';

import locale403 from '@/views/exception/403/locale/zh-CN';
import locale404 from '@/views/exception/404/locale/zh-CN';
import locale500 from '@/views/exception/500/locale/zh-CN';

import localeUserInfo from '@/views/user/info/locale/zh-CN';
import localeUserSetting from '@/views/user/setting/locale/zh-CN';

import localeSettings from './zh-CN/settings';

export default {
  'menu.dashboard': '仪表盘',
  'menu.server.dashboard': '仪表盘-服务端',
  'menu.server.workplace': '工作台-服务端',
  'menu.server.monitor': '实时监控-服务端',
  'menu.list': '列表页',
  'menu.result': '结果页',
  'menu.exception': '异常页',
  'menu.form': '表单页',
  'menu.assistant': 'AI助理',
  'menu.assistant.chat': '智能助手',
  'menu.profile': '个人中心',
  'menu.visualization': '数据可视化',
  'menu.course': '课程中心',
  'menu.digitalHuman': '数字人',
  'menu.digitalHuman.tools': '数字人工具',
  'menu.digitalHuman.pptToVideo': 'PPT 转视频',
  'menu.digitalHuman.textToVideo': '文本转视频',
  'menu.digitalHuman.clone': '数字人克隆',
  'menu.digitalHuman.my': '我的数字人',
  'menu.profile.userInfo': '用户信息',
  'menu.profile.learningData': '学习数据',
  'menu.user': '账户',
  'menu.arcoWebsite': 'Arco Design',
  'menu.faq': '常见问题',
  'navbar.docs': '文档中心',
  'navbar.action.locale': '切换为中文',
  ...localeSettings,
  ...localeMessageBox,
  ...localeLogin,
  ...localeWorkplace,

  ...localeMonitor,
  ...localeCourseMonitor,
  ...localeSearchTable,
  ...localeCardList,
  ...localeStepForm,
  ...localeGroupForm,
  ...localeBasicProfile,
  ...localeSuccess,
  ...localeError,
  ...locale403,
  ...locale404,
  ...locale500,
  ...localeUserInfo,
  ...localeUserSetting,
};

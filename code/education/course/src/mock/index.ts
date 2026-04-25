import Mock from 'mockjs';

import './message-box';
import './user';
import './course';
import './chat';

import '@/views/dashboard/workplace/mock';

import '@/views/dashboard/monitor/mock';

import '@/views/list/card/mock';
import '@/views/list/search-table/mock';

import '@/views/form/step/mock';

import '@/views/profile/basic/mock';

import '@/views/user/info/mock';
import '@/views/user/setting/mock';

Mock.setup({
  timeout: '60-100',
});

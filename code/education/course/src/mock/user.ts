import setupMock, {
  failResponseWrap,
  successResponseWrap,
} from '@/utils/setup-mock';
import Mock from 'mockjs';

import { MockParams } from '@/types/mock';
import { isLogin } from '@/utils/auth';

setupMock({
  setup() {
    // Mock.XHR.prototype.withCredentials = true;

    // 用户信息
    Mock.mock(new RegExp('/api/users/me'), () => {
      if (isLogin()) {
        const role = window.localStorage.getItem('userRole') || 'admin';
        return successResponseWrap({
          name: '卡布奇',
          avatar:
            'https://hiraethsev-1354715391.cos.ap-shanghai.myqcloud.com/uploads/zhixi/%E5%8D%A1%E5%B8%83%E5%A5%87.jpg',
          email: 'wangliqun@email.com',
          job: 'frontend',
          jobName: '计算机学院',
          organization: 'Frontend',
          organizationName: '计算机科学与技术',
          location: 'beijing',
          locationName: '武汉',
          introduction: '人潇洒，性温存',
          personalWebsite: 'https://www.arco.design',
          phone: '150****0000',
          registrationDate: '2013-05-10 12:10:00',
          accountId: '15012312300',
          certification: 1,
          role,
        });
      }
      return failResponseWrap(null, '未登录', 50008);
    });

    // 登录
    Mock.mock(new RegExp('/api/login/access-token'), (params: MockParams) => {
      // Decode x-www-form-urlencoded body
      const urlParams = new URLSearchParams(params.body);
      const username = urlParams.get('username') || '';
      const password = urlParams.get('password') || '';
      
      if (!username) {
        return failResponseWrap(null, '用户名不能为空', 5000);
      }
      if (!password) {
        return failResponseWrap(null, '密码不能为空', 5000);
      }
      if (username === 'admin' && password === 'admin') {
        window.localStorage.setItem('userRole', 'admin');
        return successResponseWrap({
          access_token: '12345',
        });
      }
      if (username === 'user' && password === 'user') {
        window.localStorage.setItem('userRole', 'user');
        return successResponseWrap({
          access_token: '54321',
        });
      }
      return failResponseWrap(null, '账号或者密码错误', 5000);
    });

    // 登出
    Mock.mock(new RegExp('/api/user/logout'), () => {
      return successResponseWrap(null);
    });

    // 用户的服务端菜单
    Mock.mock(new RegExp('/api/user/menu'), () => {
      const menuList = [
        {
          path: '/dashboard',
          name: 'dashboard',
          meta: {
            locale: 'menu.server.dashboard',
            requiresAuth: true,
            icon: 'icon-dashboard',
            order: 1,
          },
          children: [
            {
              path: 'workplace',
              name: 'Workplace',
              meta: {
                locale: 'menu.server.workplace',
                requiresAuth: true,
              },
            },
            {
              path: 'https://arco.design',
              name: 'arcoWebsite',
              meta: {
                locale: 'menu.arcoWebsite',
                requiresAuth: true,
              },
            },
          ],
        },
      ];
      return successResponseWrap(menuList);
    });
  },
});

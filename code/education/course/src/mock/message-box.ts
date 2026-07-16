import setupMock, { successResponseWrap } from '@/utils/setup-mock';
import Mock from 'mockjs';

const haveReadIds: number[] = [];
const getMessageList = () => {
  return [
    {
      id: 1,
      type: 'message',
      title: '郑曦月',
      subTitle: '的消息',
      avatar:
        '//p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/8361eeb82904210b4f55fab888fe8416.png~tplv-uwbnlip3yd-webp.webp',
      content: '我已批改你的作业，请查收！',
      time: '今天 12:30:01',
    },
    {
      id: 2,
      type: 'message',
      title: '宁波',
      subTitle: '的回复',
      avatar:
        '//p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/3ee5f13fb09879ecb5185e440cef6eb9.png~tplv-uwbnlip3yd-webp.webp',
      content: '此处 bug 已经修复',
      time: '今天 12:30:01',
    },
    {
      id: 3,
      type: 'message',
      title: 'CCLAOS',
      subTitle: '的消息',
      avatar:
        '//p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/3ee5f13fb09879ecb5185e440cef6eb9.png~tplv-uwbnlip3yd-webp.webp',
      content: '请按照要求压缩代码提交',
      time: '今天 12:20:01',
    },
    {
      id: 4,
      type: 'notice',
      title: '提交截止通知',
      subTitle: '',
      avatar: '',
      content: '您的算法作业即将截止，请尽快前往作业提交…',
      time: '今天 12:20:01',
      messageType: 3,
    },
    {
      id: 5,
      type: 'notice',
      title: '规则开通成功',
      subTitle: '',
      avatar: '',
      content: '内容屏蔽规则于 2025-02-01 开通成功并生效',
      time: '今天 12:20:01',
      messageType: 1,
    },
    {
      id: 6,
      type: 'todo',
      title: '新测验发布',
      subTitle: '',
      avatar: '',
      content: 'ICPC考试于 2025-05-15 15:00 开始，请准时…',
      time: '今天 12:20:01',
      messageType: 0,
    },
  ].map((item) => ({
    ...item,
    status: haveReadIds.indexOf(item.id) === -1 ? 0 : 1,
  }));
};

setupMock({
  setup: () => {
    Mock.mock(new RegExp('/api/message/list'), () => {
      return successResponseWrap(getMessageList());
    });

    Mock.mock(new RegExp('/api/message/read'), (params: { body: string }) => {
      const { ids } = JSON.parse(params.body);
      haveReadIds.push(...(ids || []));
      return successResponseWrap(true);
    });
  },
});

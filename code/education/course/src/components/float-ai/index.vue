<template>
  <div class="chat-container">
    <div class="chat-messages">
      <a-list :data-source="data" style="width: 100%">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #avatar>
                <a-avatar :image-url="item.avatar" />
              </template>
              <!-- <template #title>
                {{
                  item.type === 'teacher'
                    ? '虚拟老师'
                    : item.type === 'student'
                    ? '学生'
                    : item.type
                }}
              </template> -->
              <template #description>
                <pre class="chat-font" style="white-space: pre-wrap">{{
                  item.content
                }}</pre>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </div>

    <form class="chat-input" @submit.prevent="handleSubmit">
      <a-input
        v-model="inputValue"
        placeholder="输入你的问题..."
        :style="{ borderRadius: '20px' }"
      />
      <a-button type="primary" html-type="submit">发送</a-button>
    </form>
  </div>
</template>

<script setup>
  import img1 from '@/assets/images/学生头像.jpg';
  import img2 from '@/assets/images/老师头像.png';
  import {
    Button as AButton,
    Input as AInput,
    List as AList,
  } from 'ant-design-vue';
  import { ref } from 'vue';

  const data = ref([
    {
      type: 'teacher',
      content: '同学你好！请问您遇到什么问题了吗？',
      avatar: img2,
    },
    {
      type: 'student',
      content:
        '老师，我这段代码一直报错，不知道哪里错了。\nfunction add(a, b) {\n  return a + b;\n}\nconsole.log(add(2));\n',
      avatar: img1,
    },
    {
      type: 'teacher',
      content:
        '你好！我看到你的代码了。问题在于你调用`add`函数时只传递了一个参数，但这个函数需要两个参数。修正后的代码应该是这样的：\nfunction add(a, b) {\n  return a + b;\n}\nconsole.log(add(2, 3)); // 正确传递两个参数\n\n知识点回顾：在JavaScript中，函数调用时传递的参数数量必须与函数定义时的参数数量相匹配，否则会导致错误。',
      avatar: img2,
    },
  ]);

  const inputValue = ref('');

  const handleSubmit = () => {
    if (inputValue.value.trim()) {
      const newMessage = {
        type: 'student',
        content: inputValue.value,
        avatar: '你的学生头像url', // 换成你的路径
      };
      data.value.push(newMessage);
      inputValue.value = '';
    }
  };
</script>

<style scoped>
  /* Chat.css */
  .ant-list-item {
    margin-bottom: 16px;
  }

  .ant-list-item-meta-title {
    margin-bottom: 4px;
    font-weight: bold;
  }

  .ant-list-item-meta-description pre {
    padding: 8px;
    overflow-x: auto;
    text-align: left;
    border-radius: 4px;
  }

  /* 可以进一步定制头像大小、颜色等 */

  /* Chat.css */

  /* 整体容器样式 */
  .chat-container {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 100%;
    height: 100%;
  }

  /* 对话列表区域 */
  .chat-messages {
    padding: 5px;
    overflow-y: auto; /* 添加滚动条 */
  }

  /* 输入框区域 */
  .chat-input {
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 0;
    background-color: white;
  }

  /* 输入框 */
  .chat-input input {
    flex-grow: 1;
    padding: 10px;
    font-size: 14px;
    border: 1px solid #ccc;
    border-radius: 10px;
  }

  .chat-font {
    font-weight: bold; /* 设置字体加粗 */
    font-size: 12px; /* 设置字体大小，例如16像素 */
    font-family: Arial, sans-serif;
    text-align: left;
  }
</style>

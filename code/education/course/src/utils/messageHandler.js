export const messageHandler = {
  formatMessage(role, content, reasoning_content = '', files = []) {
    return {
      id: Date.now(),
      role,
      content,
      reasoning_content,
      files,
      completion_tokens: 0,
      speed: 0,
      loading: false,
    };
  },

  // 处理流式响应
  async handleStreamResponse(response, updateCallback) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedContent = '';
    let accumulatedReasoning = '';
    const startTime = Date.now();

    const processChunk = async () => {
      const { done, value } = await reader.read();
      if (done) return;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter((line) => line.trim() !== '');

      lines.forEach((line) => {
        if (line === 'data: [DONE]') return;
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(5));
          const content = data.choices[0].delta.content || '';
          const reasoning = data.choices[0].delta.reasoning_content || '';

          accumulatedContent += content;
          accumulatedReasoning += reasoning;

          // 通过回调更新消息
          updateCallback(
            accumulatedContent,
            accumulatedReasoning,
            data.usage?.completion_tokens || 0,
            (
              (data.usage?.completion_tokens || 0) /
              ((Date.now() - startTime) / 1000)
            ).toFixed(2)
          );
        }
      });

      await processChunk();
    };

    await processChunk();
  },

  // 处理非流式响应
  handleNormalResponse(response, updateCallback) {
    updateCallback(
      response.choices[0].message.content,
      response.choices[0].message.reasoning_content || '',
      response.usage.completion_tokens,
      response.speed
    );
  },

  // 统一的响应处理函数
  async handleResponse(response, isStream, updateCallback) {
    if (isStream) {
      await this.handleStreamResponse(response, updateCallback);
    } else {
      this.handleNormalResponse(response, updateCallback);
    }
  },
};

export default messageHandler;

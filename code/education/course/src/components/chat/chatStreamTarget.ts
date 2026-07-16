type StreamData = Record<string, any>;

/**
 * Binds one streaming request to the assistant message created for that request.
 * The target never follows the currently selected conversation.
 */
export function createChatStreamTarget(
  sessionId: string,
  assistant: Record<string, any>
) {
  let runId = '';

  return {
    message: assistant,
    accepts(event: string, data: StreamData) {
      const eventSessionId = String(data.sessionId || data.session_id || '');
      if (eventSessionId && eventSessionId !== sessionId) return false;

      const eventRunId = String(data.runId || data.run_id || '');
      if (event === 'run_started' && eventRunId) {
        if (runId && runId !== eventRunId) return false;
        runId = eventRunId;
      } else if (eventRunId && runId && eventRunId !== runId) {
        return false;
      }
      return true;
    },
    get runId() {
      return runId;
    },
  };
}

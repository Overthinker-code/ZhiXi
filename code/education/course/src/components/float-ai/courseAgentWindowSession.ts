import type { CourseAgentContractSummary } from '@/api/ai-chat';

export interface CourseAgentWindowSession {
  token: string;
  agent: CourseAgentContractSummary;
  courseId: string;
  courseTitle: string;
  chapterId?: string;
  chapterLabel?: string;
  knowledgePointIds?: string[];
  initialPrompt?: string;
}

let sessionSequence = 0;

export type CourseAgentWindowSessionInput = Omit<CourseAgentWindowSession, 'token'>;

export function createCourseAgentWindowSession(
  input: CourseAgentWindowSessionInput
): CourseAgentWindowSession {
  if (!input.courseId.trim()) throw new Error('Course context is required');
  if (input.agent.executionKind !== 'chat') {
    throw new Error('Only chat agents can open a realtime window');
  }
  sessionSequence += 1;
  return {
    ...input,
    courseId: input.courseId.trim(),
    courseTitle: input.courseTitle.trim(),
    initialPrompt: input.initialPrompt?.trim(),
    token: `course-agent-${Date.now()}-${sessionSequence}`,
  };
}

export function isCourseAgentWindowSessionCurrent(
  activeToken: string | undefined,
  eventToken: string
) {
  return Boolean(activeToken) && activeToken === eventToken;
}

export const COURSE_AGENT_WINDOW_EVENT = 'open-classroom-ai';

export function dispatchCourseAgentWindow(
  target: Pick<EventTarget, 'dispatchEvent'>,
  session: CourseAgentWindowSession
) {
  const event = new Event(COURSE_AGENT_WINDOW_EVENT) as Event & {
    detail: { agentSession: CourseAgentWindowSession };
  };
  Object.defineProperty(event, 'detail', {
    configurable: false,
    enumerable: true,
    value: { agentSession: session },
  });
  return target.dispatchEvent(event);
}

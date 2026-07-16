import axios from 'axios';

/** 学生中心读接口在后端不可达时要尽快失败，页面才能进入课程快照状态。 */
const READ_TIMEOUT_MS = 8000;

export interface StudentMessage {
  id: string;
  title: string;
  body: string;
  category: string;
  is_read: boolean;
  link?: string | null;
  created_at: string;
}

export interface StudyGroupItem {
  id: string;
  name: string;
  description: string;
  member_count: number;
  course_name?: string | null;
  my_role: string;
  updated_at: string;
}

export interface PracticeTopicSummary {
  subject: string;
  topic: string;
  sessions: number;
  total_questions: number;
  correct_count: number;
  avg_score: number;
  last_practiced_at?: string | null;
}

export interface PracticeSummary {
  total_sessions: number;
  total_questions: number;
  correct_rate: number;
  subjects: string[];
  topics: PracticeTopicSummary[];
  assignment_completed: number;
  assignment_total: number;
}

export interface AchievementItem {
  id: string;
  code: string;
  title: string;
  description: string;
  icon: string;
  points_awarded: number;
  earned_at: string;
}

export interface AchievementPayload {
  total_points: number;
  level: number;
  next_level_points: number;
  data: AchievementItem[];
  count: number;
}

function unwrap<T>(res: unknown): T {
  const payload = res as { data?: T };
  return (payload.data ?? res) as T;
}

export async function fetchStudentMessages(limit = 20) {
  const res = await axios.get('/api/student-hub/messages', {
    params: { limit },
    timeout: READ_TIMEOUT_MS,
  });
  return unwrap<{ data: StudentMessage[] }>(res).data ?? [];
}

export async function fetchStudyGroups() {
  const res = await axios.get('/api/student-hub/groups', { timeout: READ_TIMEOUT_MS });
  return unwrap<{ data: StudyGroupItem[] }>(res).data ?? [];
}

export async function fetchPracticeSummary() {
  const res = await axios.get('/api/student-hub/practice/summary', {
    timeout: READ_TIMEOUT_MS,
  });
  return unwrap<PracticeSummary>(res);
}

export async function fetchAchievements() {
  const res = await axios.get('/api/student-hub/achievements', {
    timeout: READ_TIMEOUT_MS,
  });
  return unwrap<AchievementPayload>(res);
}

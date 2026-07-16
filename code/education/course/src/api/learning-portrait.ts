import axios from 'axios';

export interface PortraitAnalyticsSeries {
  key: string;
  label: string;
  values: Array<number | null>;
}

export interface PortraitAnalyticsCapability {
  key: string;
  label: string;
  value: number | null;
  previous: number | null;
  evidence_count: number;
}

export interface PortraitAnalyticsRhythm {
  week_labels: string[];
  day_labels: string[];
  activity: number[][];
  hour_labels: string[];
  focus_hours: number[];
  method_version: string;
}

export interface PortraitAnalyticsResourcePreference {
  key: string;
  label: string;
  value: number;
  count: number;
}

export interface PortraitAnalyticsCourse {
  id: string;
  name: string;
  score: number | null;
  trend: number | null;
  focus: string;
  evidence_count: number;
}

export interface PortraitAnalytics {
  profile_version: number;
  generated_at: string;
  evidence_count: number;
  confidence: number | null;
  overall_score: number | null;
  growth_30d: number | null;
  engagement: number | null;
  attention_count: number;
  trend_labels: string[];
  trend_series: PortraitAnalyticsSeries[];
  capabilities: PortraitAnalyticsCapability[];
  rhythm: PortraitAnalyticsRhythm;
  resource_preferences: PortraitAnalyticsResourcePreference[];
  courses: PortraitAnalyticsCourse[];
  method_version: string;
}

export function fetchPortraitAnalytics() {
  return axios
    .get<PortraitAnalytics>('/api/learning-report/portrait/analytics', {
      timeout: 12000,
    })
    .then((response) => response.data);
}

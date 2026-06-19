// Types mirroring the backend API schemas.

export interface Account {
  id: string;
  email: string;
  lang: string;
  plan: string;
  limits: { free_monthly_lap_limit: number; free_ai_trial: number };
  usage: { laps_this_month: number; ai_reports_used: number };
  subscription: {
    id: string;
    plan: string;
    status: string;
    current_period_end: string | null;
  } | null;
}

export interface LapListItem {
  id: string;
  session_id: string;
  game: string;
  track: string | null;
  car_or_team: string | null;
  lap_time_ms: number;
  valid: boolean;
  recorded_at: string;
}

export interface SessionSummary {
  id: string;
  game: string;
  track: string | null;
  car_or_team: string | null;
  session_type: string | null;
  started_at: string;
  lap_count: number;
  best_lap_time_ms: number | null;
}

export interface LapSummary {
  id: string;
  session_id: string;
  lap_time_ms: number;
  valid: boolean;
  sample_count: number;
  recorded_at: string;
  has_metrics: boolean;
}

export interface Corner {
  number: number;
  entry_dist_m: number;
  apex_dist_m: number;
  exit_dist_m: number;
  entry_speed_kmh: number;
  apex_speed_kmh: number;
  exit_speed_kmh: number;
  brake_point_dist_m: number;
  brake_to_apex_m: number;
  peak_brake: number;
  throttle_point_dist_m: number;
  trail_brake_overlap_m: number;
  steering_reversals: number;
  direction: "left" | "right";
  time_s: number;
}

export interface LapMetricsSummary {
  distance_m: number;
  top_speed_kmh: number;
  min_speed_kmh: number;
  avg_speed_kmh: number;
  full_throttle_pct: number;
  braking_pct: number;
  trail_braking_pct: number;
  corner_count: number;
  avg_apex_speed_kmh: number | null;
  steering_reversals_total: number;
}

export interface LapMetrics {
  schema: string;
  lap_time_ms: number;
  summary: LapMetricsSummary;
  corners: Corner[];
}

export interface TraceMeta {
  schema_version: string;
  hz: number;
  points: number;
  size_bytes: number;
}

export interface LapDetail {
  id: string;
  session_id: string;
  game: string;
  track: string | null;
  car_or_team: string | null;
  lap_time_ms: number;
  valid: boolean;
  sample_count: number;
  recorded_at: string;
  has_metrics: boolean;
  metrics: LapMetrics | null;
  trace: TraceMeta | null;
  reference_lap_id: string | null;
}

export interface LapTrace {
  schema: string;
  hz: number;
  channels: Record<string, number[]>;
}

export interface CompareCorner {
  number: number;
  apex_dist_m: number;
  delta_s: number;
  self_apex_kmh: number;
}

export interface LapCompare {
  a: { id: string; lap_time_ms: number; track: string | null };
  b: { id: string; lap_time_ms: number; track: string | null };
  distance_m: number[];
  delta_s: number[];
  total_delta_s: number;
  corners: CompareCorner[];
}

export interface CoachMistake {
  title: string;
  detail: string;
  corner: number | null;
  time_loss_s: number | null;
}

export interface CoachSummary {
  summary_text: string;
  top_mistakes: CoachMistake[];
  corner_notes: { corner: number; note: string }[];
  training_plan: string[];
}

export interface CoachReport {
  id: string;
  lap_id: string;
  summary: CoachSummary;
  body: string;
  model: string;
  created_at: string;
}

export interface Plan {
  id: string;
  title: string;
  price_rub: number;
  period: string | null;
  features: string[];
}

// Espelha os DTOs do backend. O frontend NÃO guarda regra de negócio (ADR-0011).

export type ContentKind = "BOOK" | "COURSE" | "ARTICLE" | "VIDEO" | "OTHER";
export type ContentStatus = "LOCKED" | "IN_PROGRESS" | "CONSOLIDATED" | "FINISHED";
export type MasteryLevel = "BEGINNER" | "INTERMEDIATE" | "ADVANCED";
export type SessionKind = "STUDY" | "REVIEW";
export type WithheldReason = "TOO_SHORT" | "NO_NOTES" | "NO_REVIEW" | "EXPIRED";

export interface Me {
  id: string;
  email: string;
  created_at: string;
  is_admin?: boolean;
}

/** Conta vista pelo admin: só contagens, nunca anotações (spec do admin). */
export interface AdminAccount {
  id: string;
  email: string;
  created_at: string;
  last_activity_at: string | null;
  contents: number;
  sessions: number;
}

export interface AdminAccountsPage {
  items: AdminAccount[];
  next_cursor: string | null;
}

export interface Registration {
  open: boolean;
}

export interface Challenge {
  id: string;
  description: string;
  target_level: MasteryLevel;
  created_at: string;
  solved: boolean;
  solved_at: string | null;
  evidence: string | null;
}

export interface NextLevel {
  level: MasteryLevel;
  points_required: number;
  challenges_required: number;
  challenges_solved: number;
}

export interface Content {
  id: string;
  title: string;
  kind: ContentKind;
  status: ContentStatus;
  points: number;
  level: MasteryLevel;
  next_level: NextLevel | null;
  queued_at: string;
  finished_at: string | null;
  last_session_at: string | null;
  queue_position: number | null;
  lock_reason: string | null;
  challenges: Challenge[];
  last_to_review: string | null;
}

export type QuestionSource = "TO_REVIEW" | "SPACED_TOPIC" | "TOPIC" | "LEARNER";
export type RecallGrade = "MISSED" | "PARTIAL" | "RECALLED";

export interface RecallQuestion {
  id: string;
  text: string;
  source: QuestionSource;
}

export interface RecallAnswer {
  question_id: string;
  answer: string;
  grade: RecallGrade;
  useful: boolean | null;
}

export interface RecallItem {
  text: string;
  source: QuestionSource;
  answer: string;
  grade: RecallGrade;
  useful: boolean | null;
}

export interface ActiveSession {
  content_id: string;
  content_title: string;
  kind: SessionKind | null;
  started_at: string;
  expires_at: string;
  questions: RecallQuestion[];
  last_to_review: string | null;
}

export interface Plan {
  timezone: string;
  preferences: Preferences;
  max_in_progress: number;
  server_time: string;
  last_review_on: string | null;
  reviewed_today: boolean;
  needs_review_today: boolean;
  active_session: ActiveSession | null;
  contents: Content[];
}

export interface Outcome {
  content_id: string;
  kind: SessionKind;
  duration_seconds: number;
  awarded: boolean;
  reason: WithheldReason | null;
  total_points: number;
  level: MasteryLevel;
  unlocked_content_id: string | null;
}

/** Uma página do histórico. `next_cursor` é opaco: só devolvê-lo para pedir a próxima. */
export interface HistoryPage {
  items: SessionRecord[];
  next_cursor: string | null;
}

export interface SessionRecord {
  event_id: string;
  type: "study_session_finished" | "study_session_abandoned";
  content_id: string;
  content_title: string;
  kind: SessionKind;
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  awarded: boolean;
  reason: string | null;
  notes_studied: string;
  notes_understood: string;
  notes_to_review: string;
  level_after: MasteryLevel | null;
  recall_rating: number | null;
  recall_test?: RecallItem[];
}

export interface Stats {
  total_sessions: number;
  total_points: number;
  total_minutes: number;
  current_streak_days: number;
  withheld_by_reason: Record<string, number>;
  daily: { day: string; sessions: number; minutes: number; points: number }[];
}

export interface Recommendations {
  model: string;
  model_info: { trained_on: string | null; trained_at: string | null; real_samples: number };
  items: { content_id: string; title: string; recall_probability: number }[];
}

export interface NotesInput {
  studied: string;
  understood: string;
  to_review: string;
  recall_rating?: number;
  answers?: RecallAnswer[];
}

export interface DayPlan {
  day: number;
  phase: string;
  kind: "STUDY" | "PRACTICE" | "CHALLENGE" | "TEACH" | "REVIEW";
  focus: string;
  activity: string;
  warmup: string[];
  target_level: MasteryLevel | null;
  done: boolean;
}

export interface TodayItem {
  content_id: string;
  title: string;
  day: number;
  total_days: number;
  plan: DayPlan;
}

export interface Preferences {
  minutes_per_day: number;
  rest_days: number[];
}

export interface WeekBlock {
  kind: "REVIEW" | "STUDY" | "CHALLENGE";
  content_id: string;
  title: string;
  competency: string;
  competency_name: string;
  pomodoros: number;
  minutes: number;
  first_day: number;
  last_day: number;
  focus: string;
}

export interface WeekDay {
  date: string;
  weekday: number;
  name: string;
  is_rest: boolean;
  minutes: number;
  competencies: string[];
  blocks: WeekBlock[];
}

export interface Week {
  minutes_per_day: number;
  rest_days: number[];
  pomodoro_minutes: number;
  study_minutes: number;
  days: WeekDay[];
}

export interface Today {
  studies: TodayItem[];
  reviews: TodayItem[];
  blocks: WeekBlock[];
}

export interface ContentSchedule {
  content_id: string;
  title: string;
  area: string;
  depth: string;
  depth_goal: string;
  from_map: boolean;
  note: string;
  current_day: number;
  total_days: number;
  days: DayPlan[];
}

export interface CompetencyContribution {
  title: string;
  progress: number;
  freshness: number;
  rust_in_days: number | null;
}

export type CompetencyStatus = "em dia" | "enferruja em breve" | "enferrujando" | "sem progresso";

export interface Competency {
  key: string;
  name: string;
  area: string;
  score: number;
  peak: number;
  rust_lost: number;
  tier: string;
  title: string;
  target: string | null;
  target_score: number | null;
  points: number;
  status: CompetencyStatus;
  rust_in_days: number | null;
  contents: CompetencyContribution[];
}

export interface CompetencySheet {
  xp: number;
  level: number;
  next_level_xp: number;
  total_points: number;
  competencies: Competency[];
  effort: { area: string; points: number }[];
  rules: { grace_days: number; decay_per_day: number; floor: number };
}

export interface Notebook {
  content_id: string;
  text: string;
  version: number;
  updated_at: string | null;
}

export interface NotebookSummary {
  content_id: string;
  chars: number;
  updated_at: string | null;
}

export type Archetype = "Archetype_A" | "Archetype_B";

export interface Strategy {
  archetype: Archetype;
  key_anchors: string[];
  press_quotes: string[];
  cultural_themes: string[];
  comparison_artists: string[];
  sensory_motifs: string[];
  descriptors: string[];
  angle_options: string[];
  artist_voice: string;
  recommended_angle: string;
  note?: string | null;
}

export interface AnalyzeResponse {
  context: string;
  artist_name: string;
  archetype: Archetype;
  descriptors: string[];
  angle_options: string[];
  suggested_style: string;
  artist_voice: string;
  comparison_artists: string[];
  press_quotes: string[];
  note?: string | null;
}

export interface StylePreset {
  key: string;
  label: string;
  description: string;
}

export interface PitchOption {
  id: number;
  raw_llm_output: string;
  audited_output: string;
  audit_removed: string[];
  status: "pending" | "accepted" | "edited" | "rejected";
}

export interface GenerateResponse {
  generation_id: number;
  artist_id: number | null;
  strategy: Strategy;
  options: PitchOption[];
  note?: string | null;
}

export interface Insights {
  blurb: string;
  worked: string[];
  avoid: string[];
  avg_rating: number | null;
  count: number | null;
}

export interface ArtistSummary {
  id: number;
  name: string;
  archetype: Archetype | "";
  pitch_count: number;
  avg_rating: number | null;
  last_activity: string | null;
}

export interface PitchCardT {
  id: number;
  generation_id: number;
  text: string;
  status: "pending" | "accepted" | "edited" | "rejected";
  rating: number;
  comment: string;
  angle: string;
  style: string;
  audit_removed: string[];
  created_at: string;
}

/** Label-wide rules generalized from every artist's feedback. */
export interface HouseRules extends Insights {
  updated_at?: string | null;
}

/** What the user just did on a card — drives the acknowledgement toast. */
export type FeedbackStatus = "accepted" | "edited" | "rejected" | "rated";

/** Genres of a text edit, so the learner attributes the change correctly. */
export const EDIT_KINDS = [
  "content", "phrasing", "style", "grammar", "facts", "length",
] as const;
export type EditKind = (typeof EDIT_KINDS)[number];

export interface ArtistDetail {
  id: number;
  name: string;
  archetype: Archetype | "";
  has_context: boolean;
  insights: Insights | null;
  pitches: PitchCardT[];
}

export interface GenerateParams {
  num_options: number;
  length: string;
  style: string;
  angle: string;
  descriptors: string[];
}

export interface Health {
  ok: boolean;
  ai_key_set: boolean;
  generate_model: string;
}

export const ARCHETYPE_LABELS: Record<Archetype, string> = {
  Archetype_A: "Worldbuilding / Sensory",
  Archetype_B: "Authority / Thesis",
};

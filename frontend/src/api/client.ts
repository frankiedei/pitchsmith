import type {
  AnalyzeResponse, ArtistDetail, ArtistSummary, FeedbackStatus, GenerateParams,
  GenerateResponse, Health, HouseRules, Insights, PitchOption, StylePreset,
} from "../types";

// Inherited from LabelOS: the UI only ever calls /api/... on a configurable
// base. A typed req<T> fetch wrapper is the whole client surface.
const BASE = (import.meta as any).env?.VITE_API_BASE ?? "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => null);
    throw new Error(detail?.detail ?? `${init?.method ?? "GET"} ${path} → ${r.status}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  health: () => req<Health>("/api/v1/health"),
  styles: () => req<StylePreset[]>("/api/v1/pitches/styles"),

  // Step 1: analyze a pasted-or-uploaded sheet into clickable themes + defaults.
  analyze: (payload: { context: string; artist_name: string }) =>
    req<AnalyzeResponse>("/api/v1/pitches/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  analyzeFiles: (files: File[], artist_name: string) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("file", f));
    fd.append("artist_name", artist_name);
    return req<AnalyzeResponse>("/api/v1/pitches/analyze", {
      method: "POST",
      headers: {}, // browser sets the multipart boundary
      body: fd,
    });
  },

  suggestThemes: (context: string, existing: string[]) =>
    req<{ descriptors: string[] }>("/api/v1/pitches/suggest-themes", {
      method: "POST",
      body: JSON.stringify({ context, existing }),
    }),

  // Step 2: generate from the held context + the user's selections.
  generate: (payload: {
    context: string;
    artist_name: string;
    params: GenerateParams;
  }) =>
    req<GenerateResponse>("/api/v1/pitches/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  generateMore: (generation_id: number, num_options: number) =>
    req<{ generation_id: number; options: PitchOption[]; note?: string | null }>(
      "/api/v1/pitches/generate-more",
      { method: "POST", body: JSON.stringify({ generation_id, num_options }) },
    ),

  feedback: (payload: {
    pitch_option_id: number;
    status: FeedbackStatus;
    final_user_edited_text: string;
    rating: number;
    comment: string;
    edit_kinds: string[];
  }) =>
    req<{
      id: number; status: string; diff_analysis: Record<string, unknown>;
      insights: Insights | null; house: HouseRules | null;
    }>(
      "/api/v1/pitches/feedback",
      { method: "POST", body: JSON.stringify(payload) },
    ),

  houseRules: () => req<HouseRules | null>("/api/v1/house-rules"),

  putHouseRules: (worked: string[], avoid: string[]) =>
    req<HouseRules>("/api/v1/house-rules", {
      method: "PUT", body: JSON.stringify({ worked, avoid }),
    }),

  putInsights: (artistId: number, worked: string[], avoid: string[]) =>
    req<Insights>(`/api/v1/artists/${artistId}/insights`, {
      method: "PUT", body: JSON.stringify({ worked, avoid }),
    }),

  artists: () => req<ArtistSummary[]>("/api/v1/artists"),
  artist: (id: number) => req<ArtistDetail>(`/api/v1/artists/${id}`),

  resetArtist: (id: number) =>
    req<{ ok: boolean }>(`/api/v1/artists/${id}/reset`, { method: "POST" }),
  deleteArtist: (id: number) =>
    req<{ ok: boolean }>(`/api/v1/artists/${id}`, { method: "DELETE" }),
};

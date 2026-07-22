import { create } from "zustand";
import { api } from "../api/client";
import type {
  AnalyzeResponse, ArtistDetail, ArtistSummary, FeedbackStatus, GenerateParams,
  Health, HouseRules, PitchCardT, StylePreset,
} from "../types";

const THEME_KEY = "pitchsmith.theme";

export function applyTheme(theme: string) {
  document.documentElement.dataset.scheme = theme;
  document.body.dataset.scheme = theme;
}

export interface Chip {
  label: string;
  on: boolean;
}

/** Acknowledgement toast: proof the app just learned from an action. */
export interface Toast {
  id: number;
  kind: "star" | "accept" | "edit" | "reject" | "note" | "error";
  msg: string;
}
let toastSeq = 0;
let learnTimer: number | undefined;

type View = "compose" | "artist";

const LENGTHS = ["80-120 words", "150-200 words", "250-320 words"];

interface State {
  health: Health | null;
  styles: StylePreset[];
  theme: string;

  view: View;
  artists: ArtistSummary[];
  selectedArtistId: number | null;
  detail: ArtistDetail | null;
  loadingDetail: boolean;
  activeGenerationId: number | null;
  house: HouseRules | null;
  toasts: Toast[];

  // composer
  files: File[];
  artistName: string;
  analyzing: boolean;
  context: string;
  analysis: AnalyzeResponse | null;
  chips: Chip[];
  newChip: string;
  suggesting: boolean;
  style: string;
  angle: string;
  customAngle: string;
  numOptions: number;
  length: string;

  generating: boolean;
  generatingMore: boolean;
  error: string | null;

  boot: () => Promise<void>;
  setTheme: (t: string) => void;
  set: <K extends keyof State>(k: K, v: State[K]) => void;

  newPitch: () => void;
  selectArtist: (id: number) => Promise<void>;
  refreshArtists: () => Promise<void>;

  analyze: () => Promise<void>;
  toggleChip: (i: number) => void;
  addChip: () => void;
  suggestMore: () => Promise<void>;
  generate: () => Promise<void>;
  generateMore: () => Promise<void>;

  pushToast: (kind: Toast["kind"], msg: string) => void;
  sendFeedback: (
    card: PitchCardT,
    status: FeedbackStatus,
    rating: number,
    text: string,
    comment?: string,
    editKinds?: string[],
  ) => Promise<void>;
  saveArtistRules: (worked: string[], avoid: string[]) => Promise<void>;
  saveHouseRules: (worked: string[], avoid: string[]) => Promise<void>;
  resetArtist: () => Promise<void>;
  deleteArtist: () => Promise<void>;
}

export const useStore = create<State>((set, get) => ({
  health: null,
  styles: [],
  theme: localStorage.getItem(THEME_KEY) || "apricot",

  view: "compose",
  artists: [],
  selectedArtistId: null,
  detail: null,
  loadingDetail: false,
  activeGenerationId: null,
  house: null,
  toasts: [],

  files: [],
  artistName: "",
  analyzing: false,
  context: "",
  analysis: null,
  chips: [],
  newChip: "",
  suggesting: false,
  style: "match",
  angle: "",
  customAngle: "",
  numOptions: 3,
  length: LENGTHS[1],

  generating: false,
  generatingMore: false,
  error: null,

  boot: async () => {
    try {
      const [health, styles, artists, house] = await Promise.all([
        api.health(), api.styles(), api.artists(),
        api.houseRules().catch(() => null),
      ]);
      set({ health, styles, artists, house });
      // deep link: #artist-<id> opens that project's hub directly
      const m = location.hash.match(/artist-(\d+)/);
      if (m) get().selectArtist(Number(m[1]));
    } catch {
      /* backend not up yet */
    }
  },

  setTheme: (t) => {
    localStorage.setItem(THEME_KEY, t);
    applyTheme(t);
    set({ theme: t });
  },

  set: (k, v) => set({ [k]: v } as unknown as Partial<State>),

  newPitch: () => {
    if (location.hash) location.hash = "";
    set({
      view: "compose", selectedArtistId: null, detail: null, activeGenerationId: null,
      files: [], artistName: "", analysis: null, context: "", chips: [],
      angle: "", customAngle: "", error: null,
    });
  },

  refreshArtists: async () => {
    try {
      set({ artists: await api.artists() });
    } catch { /* ignore */ }
  },

  selectArtist: async (id) => {
    if (location.hash !== `#artist-${id}`) location.hash = `artist-${id}`;
    set({ view: "artist", selectedArtistId: id, loadingDetail: true, error: null });
    try {
      const detail = await api.artist(id);
      set({
        detail, loadingDetail: false,
        activeGenerationId: detail.pitches[0]?.generation_id ?? null,
      });
    } catch (e) {
      set({ loadingDetail: false, error: (e as Error).message });
    }
  },

  analyze: async () => {
    const { files, artistName } = get();
    if (files.length === 0) {
      set({ error: "Add one or more .pdf or .txt sheets to analyze." });
      return;
    }
    set({ analyzing: true, error: null });
    try {
      const a = await api.analyzeFiles(files, artistName);
      set({
        analyzing: false,
        analysis: a,
        context: a.context,
        artistName: a.artist_name || artistName,
        chips: a.descriptors.map((label) => ({ label, on: true })),
        style: a.suggested_style || "match",
        angle: a.angle_options[0] ?? "",
      });
    } catch (e) {
      set({ analyzing: false, error: (e as Error).message });
    }
  },

  toggleChip: (i) =>
    set({ chips: get().chips.map((c, j) => (j === i ? { ...c, on: !c.on } : c)) }),

  addChip: () => {
    const label = get().newChip.trim();
    if (!label) return;
    if (get().chips.some((c) => c.label.toLowerCase() === label.toLowerCase())) {
      set({ newChip: "" });
      return;
    }
    set({ chips: [...get().chips, { label, on: true }], newChip: "" });
  },

  suggestMore: async () => {
    const { context, chips } = get();
    set({ suggesting: true, error: null });
    try {
      const { descriptors } = await api.suggestThemes(context, chips.map((c) => c.label));
      const have = new Set(chips.map((c) => c.label.toLowerCase()));
      const fresh = descriptors
        .filter((d) => !have.has(d.toLowerCase()))
        .map((label) => ({ label, on: true }));
      set({ chips: [...chips, ...fresh], suggesting: false });
    } catch (e) {
      set({ suggesting: false, error: (e as Error).message });
    }
  },

  generate: async () => {
    const { context, artistName, chips, style, angle, customAngle, numOptions, length } = get();
    if (!artistName.trim()) {
      set({ error: "Add an artist name so this pitch has a project." });
      return;
    }
    set({ generating: true, error: null });
    try {
      const params: GenerateParams = {
        num_options: numOptions,
        length,
        style,
        angle: angle === "" ? customAngle : angle,
        descriptors: chips.filter((c) => c.on).map((c) => c.label),
      };
      const res = await api.generate({ context, artist_name: artistName, params });
      await get().refreshArtists();
      if (res.artist_id != null) {
        await get().selectArtist(res.artist_id);
        set({ activeGenerationId: res.generation_id });
      }
      set({ generating: false });
    } catch (e) {
      set({ error: (e as Error).message, generating: false });
    }
  },

  generateMore: async () => {
    const { activeGenerationId, selectedArtistId } = get();
    if (activeGenerationId == null) return;
    set({ generatingMore: true, error: null });
    try {
      await api.generateMore(activeGenerationId, 2);
      if (selectedArtistId != null) await get().selectArtist(selectedArtistId);
      set({ generatingMore: false, activeGenerationId });
    } catch (e) {
      set({ error: (e as Error).message, generatingMore: false });
    }
  },

  pushToast: (kind, msg) => {
    const id = ++toastSeq;
    set({ toasts: [...get().toasts, { id, kind, msg }] });
    setTimeout(() => set({ toasts: get().toasts.filter((t) => t.id !== id) }), 3200);
  },

  sendFeedback: async (card, status, rating, text, comment = "", editKinds = []) => {
    try {
      const res = await api.feedback({
        pitch_option_id: card.id,
        status,
        final_user_edited_text: status === "rejected" ? "" : text,
        rating,
        comment,
        edit_kinds: editKinds,
      });
      const detail = get().detail;
      if (detail) {
        const pitches = detail.pitches.map((p) =>
          p.id === card.id
            ? {
                ...p,
                status: status === "rated" ? p.status : (status as PitchCardT["status"]),
                rating: rating || p.rating,
                comment: comment || p.comment,
                text: status === "rejected" ? p.text : text,
              }
            : p,
        );
        set({
          detail: { ...detail, pitches, insights: res.insights ?? detail.insights },
          house: res.house ?? get().house,
        });
      } else if (res.house) {
        set({ house: res.house });
      }
      // acknowledge: say what the app just learned from this action
      const push = get().pushToast;
      if (comment.trim()) {
        push("note", "Note saved — folding it into the label-wide house rules");
      } else if (status === "rated") {
        push("star", `Rated ${rating}/5 — Pitchsmith noted what you like`);
      } else if (status === "accepted") {
        push("accept", "Accepted — future batches will lean on this pitch");
      } else if (status === "edited") {
        push("edit", editKinds.length
          ? `Edit saved as ${editKinds.join(" + ")} — teaching exactly that`
          : "Edit saved — your changes teach the next drafts");
      } else {
        push("reject", "Rejected — noted what to avoid from here on");
      }
      get().refreshArtists();
      // the learning summaries recompute in the background on the server;
      // quietly pull the fresh insights + house rules in a few seconds
      window.clearTimeout(learnTimer);
      learnTimer = window.setTimeout(async () => {
        try {
          const [d, h] = await Promise.all([
            get().selectedArtistId != null && get().view === "artist"
              ? api.artist(get().selectedArtistId as number)
              : Promise.resolve(null),
            api.houseRules(),
          ]);
          const cur = get().detail;
          if (d && cur && d.id === cur.id) {
            set({ detail: { ...cur, insights: d.insights } });
          }
          if (h) set({ house: h });
        } catch { /* quiet — this is a bonus refresh */ }
      }, 6000);
    } catch (e) {
      get().pushToast("error", `Couldn't save that — ${(e as Error).message}`);
    }
  },

  saveArtistRules: async (worked, avoid) => {
    const id = get().selectedArtistId;
    if (id == null) return;
    try {
      const insights = await api.putInsights(id, worked, avoid);
      const detail = get().detail;
      if (detail && detail.id === id) set({ detail: { ...detail, insights } });
      get().pushToast("note", "Rules updated — deleted ones stay gone, yours stay put");
    } catch (e) {
      get().pushToast("error", `Couldn't update rules — ${(e as Error).message}`);
    }
  },

  saveHouseRules: async (worked, avoid) => {
    try {
      const house = await api.putHouseRules(worked, avoid);
      set({ house });
      get().pushToast("note", "House rules updated — every artist follows your version");
    } catch (e) {
      get().pushToast("error", `Couldn't update house rules — ${(e as Error).message}`);
    }
  },

  resetArtist: async () => {
    const id = get().selectedArtistId;
    if (id == null) return;
    try {
      await api.resetArtist(id);
      get().pushToast("reject", "Artist data cleared — pitches and learnings wiped, fresh start");
      await get().selectArtist(id);
      get().refreshArtists();
    } catch (e) {
      get().pushToast("error", `Couldn't reset — ${(e as Error).message}`);
    }
  },

  deleteArtist: async () => {
    const id = get().selectedArtistId;
    if (id == null) return;
    try {
      await api.deleteArtist(id);
      get().pushToast("reject", "Artist deleted");
      get().newPitch();
      get().refreshArtists();
    } catch (e) {
      get().pushToast("error", `Couldn't delete — ${(e as Error).message}`);
    }
  },
}));

export const LENGTH_OPTIONS = LENGTHS;

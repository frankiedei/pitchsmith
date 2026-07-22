"""Pydantic request/response models for the pitch API (Label OS style: explicit
Out models, from_attributes for ORM serialization)."""
from datetime import datetime

from pydantic import BaseModel, Field


# --- generate ---------------------------------------------------------------

class GenerateParams(BaseModel):
    num_options: int = Field(default=3, ge=2, le=3)
    length: str = "150-200 words"
    style: str = "match"            # style-preset key (see prompts.STYLE_PRESETS)
    angle: str = ""                 # chosen lead angle (from angle_options or custom)
    descriptors: list[str] = []     # the theme chips the user kept switched on


class GenerateRequest(BaseModel):
    """JSON path (no file upload). The multipart path reuses these fields as form
    values plus an optional file — see the route."""
    context: str = ""
    artist_name: str = ""
    params: GenerateParams = GenerateParams()


# --- analyze (upload sheet -> clickable themes + smart defaults) -------------

class AnalyzeRequest(BaseModel):
    context: str = ""
    artist_name: str = ""


class AnalyzeResponse(BaseModel):
    """Everything the composer needs to render its chips + dropdowns. `context`
    is the extracted sheet text, held by the client (hidden) and passed back to
    /generate — the UI never shows a raw context box."""
    context: str
    artist_name: str
    archetype: str
    descriptors: list[str]
    angle_options: list[str]
    suggested_style: str
    artist_voice: str
    comparison_artists: list[str]
    press_quotes: list[str]
    note: str | None = None


class SuggestThemesRequest(BaseModel):
    context: str
    existing: list[str] = []


class SuggestThemesResponse(BaseModel):
    descriptors: list[str]


class StylePreset(BaseModel):
    key: str
    label: str
    description: str


class PitchOptionOut(BaseModel):
    id: int
    raw_llm_output: str
    audited_output: str
    audit_removed: list[str]
    status: str

    model_config = {"from_attributes": True}


class StrategyOut(BaseModel):
    archetype: str
    key_anchors: list[str] = []
    press_quotes: list[str] = []
    cultural_themes: list[str] = []
    comparison_artists: list[str] = []
    sensory_motifs: list[str] = []
    descriptors: list[str] = []
    angle_options: list[str] = []
    artist_voice: str = ""
    recommended_angle: str = ""
    note: str | None = None


class GenerateResponse(BaseModel):
    generation_id: int
    artist_id: int | None
    strategy: StrategyOut
    options: list[PitchOptionOut]
    note: str | None = None


class GenerateMoreRequest(BaseModel):
    generation_id: int
    num_options: int = Field(default=2, ge=1, le=3)


class GenerateMoreResponse(BaseModel):
    generation_id: int
    options: list[PitchOptionOut]
    note: str | None = None


# --- feedback ---------------------------------------------------------------

class FeedbackRequest(BaseModel):
    pitch_option_id: int
    # accepted | edited | rejected change the pitch's status; "rated" records a
    # star rating and/or comment on its own without accepting or rejecting.
    status: str = "edited"
    final_user_edited_text: str = ""
    rating: int = Field(default=0, ge=0, le=5)
    comment: str = ""               # "what worked / what didn't" note
    # user-tagged genres of the edit (content, phrasing, style, grammar, ...)
    edit_kinds: list[str] = []


class Insights(BaseModel):
    blurb: str = ""
    worked: list[str] = []
    avoid: list[str] = []
    avg_rating: float | None = None
    count: int | None = None


class HouseRules(Insights):
    """Label-wide rules generalized from every artist's feedback."""
    updated_at: datetime | None = None


class RulesUpdate(BaseModel):
    """The user's edited worked/avoid lists (for an artist or the house)."""
    worked: list[str] = []
    avoid: list[str] = []


class FeedbackResponse(BaseModel):
    id: int
    pitch_option_id: int
    status: str
    diff_analysis: dict
    insights: Insights | None = None   # refreshed after this rating/edit
    house: HouseRules | None = None    # refreshed label-wide rules


# --- pitch hub (projects) ---------------------------------------------------

class ArtistSummary(BaseModel):
    id: int
    name: str
    archetype: str = ""
    pitch_count: int = 0
    avg_rating: float | None = None
    last_activity: datetime | None = None


class PitchCard(BaseModel):
    """One pitch as it appears in the hub: the current text (the user's edit if
    they made one, else the audited draft) plus its rating/status."""
    id: int
    generation_id: int
    text: str
    status: str
    rating: int = 0
    comment: str = ""
    angle: str = ""
    style: str = ""
    audit_removed: list[str] = []
    created_at: datetime


class ArtistDetail(BaseModel):
    id: int
    name: str
    archetype: str = ""
    has_context: bool = False
    insights: Insights | None = None
    pitches: list[PitchCard] = []


# --- history (read) ---------------------------------------------------------

class GenerationSummary(BaseModel):
    id: int
    artist_id: int | None
    archetype_selected: str
    created_at: datetime
    option_count: int

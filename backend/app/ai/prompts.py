"""Prompt engineering for the pitch pipeline: the two strategic archetypes, the
banned-phrase constraints, and the few-shot system prompts each stage uses.

Kept in one module (data, not logic) so a non-engineer can tune the voice, add
banned phrases, or extend the few-shot set without touching pipeline code.
"""

# --- Strategic archetypes (the core domain logic) -------------------------

ARCHETYPE_A = "Archetype_A"  # Worldbuilding / Sensory
ARCHETYPE_B = "Archetype_B"  # Authority / Thesis

ARCHETYPES = {
    ARCHETYPE_A: {
        "name": "Worldbuilding / Sensory",
        "when": (
            "Emerging artists with lower traction or credibility, thin press, few "
            "co-signs. There is a gap where authority would go."
        ),
        "fill_with": (
            "Fill that gap with sensory imagery, vivid figurative language, and "
            "concrete visual anchors — what the music sounds and looks like, the "
            "world it builds. Make the reader see and hear it."
        ),
    },
    ARCHETYPE_B: {
        "name": "Authority / Thesis",
        "when": (
            "Established artists with heavy press quotes, notable co-signs, or strong "
            "metrics. There is leverage to press on."
        ),
        "fill_with": (
            "Capitalize on leverage points: lead with the strongest press quote or "
            "co-sign, surface a cultural contradiction the artist embodies, and build "
            "the pitch around the artist's own thesis statement or quote."
        ),
    },
}

# --- Anti-AI / style constraints ------------------------------------------
# The deterministic audit (logic/audit.py) scans for these; the LLM audit is
# told to never emit them. Extend freely — this is the house style-guard.
BANNED_PHRASES = [
    "carving out a lane",
    "carve out a lane",
    "tapestry of sound",
    "sonic tapestry",
    "testament to",
    "seamlessly blends",
    "seamlessly blend",
    "a force to be reckoned with",
    "force to be reckoned with",
    "burst onto the scene",
    "bursting onto the scene",
    "took the world by storm",
    "no stranger to",
    "wise beyond",
    "poised to take",
    "the next big thing",
    "genre-bending",
    "genre-defying",
    "boundary-pushing",
    "pushing boundaries",
    "soundscape",
    "soundscapes",
    "captivating",
    "mesmerizing",
    "hauntingly beautiful",
    "raw and honest",
    "wears their heart on their sleeve",
    "in a league of their own",
    "one to watch",
    "rising star",
    "meteoric rise",
    "delve into",
    "delves into",
    "rich tapestry",
    "leaves no stone unturned",
    "at the end of the day",
    "when it comes to",
    "elevate",
    "elevates",
    "resonate deeply",
    "resonates deeply",
]

STYLE_RULES = (
    "House style rules:\n"
    "- Never use generic PR/AI clichés. Concrete beats abstract every time.\n"
    "- Describe the actual sound (instruments, tempo, texture, production choices), "
    "the visual world, or the cultural context — not vague praise.\n"
    "- Prefer specific nouns and verbs over adjectives. Cut hype words.\n"
    "- Every claim should be traceable to a fact in the source context or a real "
    "press quote. Do not invent quotes, outlets, numbers, or co-signs.\n"
    "- Sound like a sharp human publicist writing to an editor they respect."
)

# Voice mirroring — the single biggest quality lever. A pitch should carry a
# subtle echo of the artist's OWN aesthetic and energy (a playful, sensory artist
# earns slightly warmer, more colourful prose; an austere one stays lean). The
# guardrail matters as much as the effect: a light touch, never parody.
VOICE_RULE = (
    "VOICE - write from INSIDE the artist's world, not from a critic's chair "
    "outside it. Play a little with their aesthetic and let the prose carry their "
    "own energy: a sunny, playful artist earns warmth, wit, and a light whimsy; an "
    "austere one stays spare. Crucially, match their emotional TEMPERATURE. If "
    "their heartbreak is sweet and summery, keep it sweet and summery. Do NOT "
    "default to irony, cynicism, menace, or noir darkness unless the artist "
    "genuinely lives there. A light touch of whimsy is the goal; heavy-handed "
    "quirk, parody, purple prose, or twee is not. Never trade a concrete fact for a "
    "flourish, and the pitch must still read as a professional writing to an editor."
)

# Imagery — the thing the real reference pitches do that AI copy doesn't: reach for
# the oddly specific sensory detail from the artist's own world.
IMAGERY_RULE = (
    "IMAGERY - evoke the artist's visual and sonic world through specific, sensory "
    "word choice: the colours, textures, tastes, objects, and sounds that belong to "
    "them. Being a little too specific is a feature, not a bug (\"best served with a "
    "side of watermelon and ice-cold lemonade\" beats \"summery and refreshing\"; a "
    "\"mall-bought strawberry Ray-Ban\" beats \"retro sunglasses\"). Reach for the "
    "concrete noun the artist would use. But do NOT oversaturate: a few precise "
    "images land harder than a pile of similes, and much of the showing can be plain "
    "concrete detail, not metaphor. Aim for one or two vivid strokes per paragraph."
)

# Show, don't tell — the fix for prose that is "too literal": stop narrating the
# artist's method or how to feel, and render the thing so the reader feels it.
SHOW_DONT_TELL_RULE = (
    "SHOW, DON'T TELL - put a concrete image, scene, or sound in front of the "
    "reader and let THEM draw the conclusion. Do not explain the artist's method, "
    "intent, or cleverness, and do not tell the reader how to feel or think. "
    "Ban meta-commentary like \"she sings it through a whimsical lens instead of a "
    "bitter one\", \"heartbreak isn't a mood, it's a world\", \"the genius move "
    "is\", or \"the thesis is\". Compare: TELLING is \"her visuals are dreamy and "
    "inviting\"; SHOWING is \"her visuals glimmer like the opalescent surface of a "
    "sweltering swimming pool, begging you to jump in\". Render the world; trust the "
    "image to carry the meaning, and trust the editor to get it."
)

# Grounded figures — the fix for strained images and empty wordplay. A figure
# earns its place only when it tells the editor something about the music.
GROUNDED_RULE = (
    "GROUNDED FIGURES - every metaphor or simile must have a POINT. It earns its "
    "place only if it tells the editor something true about how the music sounds "
    "or feels. \"Her visuals glimmer like a sweltering swimming pool, begging you "
    "to jump in\" works because the record is summery and the image says what the "
    "music does: it invites you in. Wordplay is not a point: riffing on an album "
    "title or extending the artist's conceit (\"a boy who scammed her gets the "
    "antique-spinning-wheel treatment\") is clever but tells the reader nothing "
    "about the sound, so cut it and use the artist's imagery as texture instead. "
    "Also cut anything surreal, melodramatic, or that needs decoding (\"singing "
    "over VHS static like she's the girl in a home movie nobody meant to keep\"). "
    "Reach for everyday, relatable comparisons an editor gets on the first read. "
    "A true, concrete sentence always beats a strained image. When in doubt, "
    "describe what is literally there."
)

# Movement-based structure — a strong pitch progresses, it doesn't dump. Modelled
# on how real press releases move: the immediate release and its image, then the
# project and its marketable specifics, then momentum. It ends on substance, NOT
# on a "happy to send / let me know" sign-off.
STRUCTURE_RULE = (
    "STRUCTURE - write in distinct movements (2-4 short paragraphs) that flow into "
    "each other, not one undifferentiated block:\n"
    "  1. LEAD: the immediate release (the new single / focus track) and the "
    "broader image or hook it opens up.\n"
    "  2. WIDEN: the album/project itself, its concept, sound, and visual world, "
    "plus the marketable points an editor actually uses (comparison artists "
    "\"for fans of X to Y\", standout visual or production facts, a press quote).\n"
    "  3. CLOSE: momentum, tours, notable tourmates and collaborators, release "
    "cadence. End on the music or the momentum, NOT on a call to action.\n"
    "This is the shape of a good pitch, not a rigid template; adapt the movements "
    "to the material and let them read as connected prose, never labelled sections."
)

# The AI "watermarks" to design out — the tells that make a pitch read as
# machine-written even when every fact is right. These are hard constraints and
# the deterministic audit backstops the dash rule regardless of the model.
WRITING_RULES = (
    "WRITING MECHANICS - avoid the tells of AI writing:\n"
    "- NO em dashes or en dashes anywhere (no —, no –). Reach for a comma, a "
    "period, parentheses, or split the sentence. A dash almost always means the "
    "line wants to be two sentences or one comma.\n"
    "- Almost no colons. At most one in the entire pitch, and only for a real list. "
    "Never a colon for dramatic reveal (\"The concept: ...\", \"The genius move: "
    "...\").\n"
    "- Let it FLOW. Most sentences should be medium-length and connected, joined "
    "with real clauses; vary the length around that. Never strand a small fact as "
    "a clipped fragment (\"Day Wave produced.\", \"The hook is sweet.\"); fold it "
    "into a fuller sentence. No runs of punchy fragments, one-line drama, or "
    "mic-drop sentences. Equally, no run-ons that cram a whole list into one "
    "breath: when you have five vivid details, keep the two or three best and let "
    "the rest go. Read it aloud; it should sound relaxed and human, like prose to "
    "a colleague.\n"
    "- Keep every sentence CLEAR and easy to read. Legible, not simple: an editor "
    "should glide through on the first pass. Favour plain syntax and everyday words "
    "that carry vivid images; avoid tangled clauses and clever-for-clever's-sake "
    "phrasing that makes the reader stop and re-read.\n"
    "- Trust the details. Don't over-dramatize or hype; the specifics do the work.\n"
    "- NO sign-off and NO call to action. Never end with \"happy to send,\" \"I can "
    "send the link / press photos,\" \"reach out,\" or \"let me know.\" End on the "
    "record or the momentum.\n"
    "- Name a producer, engineer, or collaborator ONLY if they are a genuine draw "
    "an editor would recognize. If they aren't notable, leave them out rather than "
    "spend a line on them."
)

# Style presets for the UI dropdown — the register the writer adopts. Each maps
# to a one-line instruction fed to the generator. "match" leans on the extracted
# artist_voice; the rest set an explicit register.
STYLE_PRESETS: dict[str, tuple[str, str]] = {
    "match":       ("Match the artist",
                    "Echo the artist's own voice and energy; let their aesthetic set the register."),
    "understated": ("Cool & understated",
                    "Calm and confident, low on adjectives. Let the facts and details carry it."),
    "vivid":       ("Warm & vivid",
                    "Sensory and image-led with a little colour, still grounded and professional."),
    "authority":   ("Authority & thesis",
                    "Lead with leverage: press, co-signs, metrics, and a clear cultural thesis."),
    "plain":       ("Straight & factual",
                    "Newsy and direct. Minimal styling, just the story and the specifics."),
}


def style_guidance(style_key: str, artist_voice: str = "") -> str:
    key = style_key if style_key in STYLE_PRESETS else "match"
    label, desc = STYLE_PRESETS[key]
    line = f"Style register: {label}. {desc}"
    if key == "match" and artist_voice:
        line += f" The artist's voice: {artist_voice}"
    return line

# --- Stage 1: strategy classifier & fact extractor ------------------------

CLASSIFIER_SYSTEM = (
    "You are a senior music PR strategist. You read an artist's background material "
    "and decide the strategic angle for a pitch, then pull out the concrete raw "
    "material a writer will use — including the artist's own tonal fingerprint so "
    "the pitch can subtly echo their voice. You are precise and never invent facts."
)


def classifier_prompt(context: str) -> str:
    return (
        "Analyze the artist background below and return ONLY a JSON object with this "
        "exact shape:\n"
        "{\n"
        '  "archetype": "Archetype_A" | "Archetype_B",\n'
        '  "key_anchors": [concrete visuals, sonic details, or co-signs to build on],\n'
        '  "press_quotes": [verbatim quotes actually present in the text, with source if given],\n'
        '  "cultural_themes": [themes/contradictions the artist embodies],\n'
        '  "comparison_artists": [named acts a writer can anchor to for "for fans of X"],\n'
        '  "sensory_motifs": [recurring images, textures, colours, or objects from the artist\'s world],\n'
        '  "descriptors": [8-14 short clickable tags, 1-4 words each, capturing the record\'s themes, sonic qualities, and visual motifs - the toggles a user picks from],\n'
        '  "angle_options": [2-3 distinct one-line strategic angles the pitch could lead with],\n'
        '  "artist_voice": "2-3 sentences naming the artist\'s tonal fingerprint, their EMOTIONAL TEMPERATURE (sunny? playful? melancholy? deadpan? warm? dark?), and the sensory world (colours, textures, tastes, objects) a writer should echo. Capture the warmth/whimsy if it is there, not only the edge",\n'
        '  "recommended_angle": "the single strongest one-line strategic angle (usually angle_options[0])"\n'
        "}\n\n"
        f"Choose {ARCHETYPE_A} ({ARCHETYPES[ARCHETYPE_A]['name']}) when: "
        f"{ARCHETYPES[ARCHETYPE_A]['when']}\n"
        f"Choose {ARCHETYPE_B} ({ARCHETYPES[ARCHETYPE_B]['name']}) when: "
        f"{ARCHETYPES[ARCHETYPE_B]['when']}\n\n"
        "Rules: press_quotes must appear verbatim in the text (else empty list). "
        "comparison_artists must be acts explicitly named in the source (as "
        "influences, tourmates, or reference points); do not invent comparisons. "
        "descriptors, sensory_motifs and artist_voice are read from the source's own "
        "imagery and tone; do not fabricate a personality the material doesn't "
        "support. descriptors should be crisp and human-readable (e.g. \"woman-scorned "
        "summer\", \"lo-fi darkwave\", \"fairytale revenge\").\n\n"
        "--- ARTIST BACKGROUND ---\n"
        f"{context}\n"
        "--- END ---"
    )


# --- Gold-standard examples (few-shot) ------------------------------------
# Real pitches that exemplify the house voice, one per archetype. The model
# imitates examples far more faithfully than it follows described rules, so
# these carry the sentence rhythm and metaphor discipline. Lightly edited to
# conform to house mechanics (no dashes, at most one colon); source: the
# reference pitch doc. They are calibration, not material — the prompt forbids
# reusing their images or phrases, even for the same artist.
GOLD_EXAMPLES = (
    "GOLD-STANDARD EXAMPLES - two real pitches written in exactly the voice to "
    "aim for. Study how the sentences flow (connected, medium-length, relaxed), "
    "how every image says something true about the music, and how each pitch "
    "ends on the record or the momentum. Do NOT reuse their specific images, "
    "phrases, jokes, or openings in your own pitches, even when writing for the "
    "same artist. They calibrate the voice, nothing more.\n"
    "\n"
    "EXAMPLE 1 (Worldbuilding / Sensory):\n"
    "Faerybabyy is frolicking through summer ahead of her upcoming sophomore "
    "album. Her latest single “tough luck” is an indie rock and pop jam best "
    "served with a side of watermelon and ice-cold lemonade. Bobbing around "
    "between buoyant synthesizers and sun-kissed hooks, the track is a veritable "
    "ribbon-cutting ceremony for what Faerybabyy calls her “woman-scorned "
    "summer,” contrasting the imagery of suburban Americana with the cloying "
    "sting of heartbreak.\n"
    "\n"
    "Drawing from internet culture, fantasy, horror, and DIY art, "
    "“rumpelstiltskin” blends iconography from fairytales, dating sims, "
    "found-footage horror, hand-drawn animation, and suburban photobooks into a "
    "world equal parts conflict, discovery, humor, vulnerability, and "
    "imagination. Behold through your mall-bought strawberry Ray-Bans as "
    "Faerybabyy’s relationships rise and collapse in surreal fashion. "
    "“rumpelstiltskin”’s upbeat mix of rock and pop will invite the eager ears "
    "of anyone, from fans of The Strokes to Olivia Rodrigo, while never "
    "compromising on her dusty, lofi sound. Her distinct visuals glimmer like "
    "the opalescent surface of a sweltering swimming pool, begging listeners to "
    "jump right in. When they do, they’ll be greeted by a visual world much "
    "deeper than it appears. Faerybabyy has created music videos and visualizers "
    "for all ten tracks on “rumpelstiltskin.”\n"
    "\n"
    "With a steady stream of upcoming releases and tour dates throughout the "
    "U.S. this fall and winter, including performances with blood club, Slater, "
    "Israel’s Arcade, and SadGirl, Faerybabyy continues to gather momentum and "
    "approach a worldwide listener-base, all the while building distinct musical "
    "worlds from scratch. Her first full-length project since the acclaimed "
    "“Jabbermouth”, “rumpelstiltskin” is the summer picnic that you just can’t "
    "miss. Bring your swimsuit!\n"
    "\n"
    "EXAMPLE 2 (Authority / Thesis):\n"
    "Thoom could have made two records: one rooted in American pop and another "
    "in experimental, punk-influenced Arabic music. Instead, she made Everyday, "
    "everything is at stake, because separating those sides of her music would "
    "have meant separating parts of herself. “I would be lying to my listeners "
    "if I tried to separate what seems the most natural to me,” she says. “The "
    "contradiction is the point.” You can hear that decision across the "
    "nine-song project with “December Forever” embracing the English pop "
    "songwriting she had long wanted to master, while “Janani,” the fully "
    "Arabic focus track, moves into more experimental territory. "
    "Executive-produced by Dylan Brady of 100 gecs and created between Los "
    "Angeles and Lebanon, the project takes its title from what she describes as "
    "“the immigrant mentality”, the reality of building a life in America while "
    "carrying family, history, and another part of herself in Lebanon, never "
    "fully integrating into either. Inspired by her travels, the project is "
    "“part diary, part mythology,” with each song written as its own intense, "
    "self-contained story. Less a confession than a record of survival, the "
    "result is, in Thoom’s words, “messy, pop, Arabic, experimental, and "
    "unapologetic.” That same instinct shapes how she writes. “Melody always "
    "comes before the lyrics for me. The emotion always comes before you have "
    "the words to express it.”\n"
    "\n"
    "On “Towards the sky,” Thoom turns the rhetoric of exile into something "
    "triumphant. Released July 17 with an accompanying music video, the single "
    "captures the project’s core tensions between displacement and belonging, "
    "tenderness and rage, girlhood and revolution. The single follows “December "
    "Forever” (500K+ streams) which appeared in an Instagram Story of Arca "
    "singing along last October, and serves as the final release ahead of the "
    "project’s arrival on July 31.\n"
    "\n"
    "The project arrives amid growing international momentum for Thoom. "
    "Alongside recent shows in Cairo and Los Angeles, including a show with Cece "
    "Natalie, she has performed across the US and Europe with Bassvictim, "
    "Jockstrap, Yves Tumor, Underscores, Frost Children, Dorian Electra, and The "
    "Dare. Everyday, everything is at stake, Thoom’s first project since her "
    "2023 debut EP Fantasy for Danger, is the fullest realization yet of a sound "
    "she has spent years developing. A separate full-length album will follow "
    "later this summer, ahead of an unannounced direct-support run across more "
    "than 20 North American cities this fall."
)


# --- Stage 2: pitch generator ---------------------------------------------

# Pitches are multi-paragraph prose, which does not survive a JSON array (the
# model emits real newlines inside the strings and breaks the parse). So the
# generator returns plain text with pitches split by this delimiter line.
PITCH_DELIM = "===PITCH==="

GENERATOR_SYSTEM = (
    "You are an elite music publicist writing a pitch to a specific editor. "
    "You write with concrete detail and a distinct point of view. "
    + STYLE_RULES + "\n\n" + VOICE_RULE + "\n\n" + IMAGERY_RULE + "\n\n"
    + SHOW_DONT_TELL_RULE + "\n\n" + GROUNDED_RULE + "\n\n" + STRUCTURE_RULE
    + "\n\n" + WRITING_RULES + "\n\n" + GOLD_EXAMPLES
)


def generator_prompt(*, context: str, strategy: dict, num_options: int,
                     length: str, style: str, angle: str,
                     descriptors: list[str], learning: str = "",
                     avoid_openings: list[str] | None = None) -> str:
    arch = strategy.get("archetype", ARCHETYPE_A)
    meta = ARCHETYPES.get(arch, ARCHETYPES[ARCHETYPE_A])
    lead_angle = angle.strip() or strategy.get("recommended_angle", "")
    voice = strategy.get("artist_voice", "")
    desc_line = (
        f"Selected themes to carry (see THEMES ARE ATMOSPHERE below): "
        f"{descriptors}\n" if descriptors else ""
    )
    theme_rule = (
        "THEMES ARE ATMOSPHERE, NOT PHRASES. The themes and sensory motifs "
        "above are a mood board, not vocabulary. Absorb them, then write from "
        "inside that mood so it quietly colors the verbs, images, and structure "
        "of the WHOLE pitch. Never insert a tag's wording verbatim (unless it is "
        "a proper noun like an album or genre name), never paraphrase the tags "
        "into one dutiful sentence each, and never cluster them in a single "
        "paragraph. An editor should finish the pitch able to guess the themes "
        "without ever seeing the list. Across your options, express the themes "
        "through DIFFERENT images in different places; if the same phrase would "
        "appear in two options, cut it from one.\n"
        if (descriptors or strategy.get("sensory_motifs")) else ""
    )
    learn_line = f"{learning}\n" if learning else ""
    avoid_line = (
        "These pitches already exist for this artist; make the new ones clearly "
        "DIFFERENT (different lead single, opening image, and structure), not "
        f"variations on them:\n{[o[:160] for o in avoid_openings]}\n"
        if avoid_openings else ""
    )
    return (
        f"Strategic archetype: {arch}, {meta['name']}.\n"
        f"{meta['fill_with']}\n\n"
        f"{style_guidance(style, voice)}\n\n"
        f"{learn_line}"
        f"{avoid_line}"
        f"Strategic angle to lead with: {lead_angle}\n"
        f"{desc_line}"
        f"Sensory motifs from their world (raw material to transform, not to "
        f"quote): {strategy.get('sensory_motifs', [])}\n"
        f"{theme_rule}"
        f"Comparison artists to anchor an editor (use only these, verbatim): "
        f"{strategy.get('comparison_artists', [])}\n"
        f"Key anchors: {strategy.get('key_anchors', [])}\n"
        f"Press quotes available (use verbatim, never invent): "
        f"{strategy.get('press_quotes', [])}\n"
        f"Cultural themes: {strategy.get('cultural_themes', [])}\n\n"
        f"OPEN each pitch with the artist's name as the subject of the first "
        f"sentence (\"<Artist> is...\", \"<Artist> could have...\"), then go "
        f"straight to something concrete. Use the angle as your strategic north "
        f"star, not as the opening line.\n"
        f"Write {num_options} DISTINCT pitch options. Each takes a genuinely "
        f"different approach (a different lead single, a different concrete detail to "
        f"build on), not paraphrases of one pitch. Follow every rule above, "
        f"especially SHOW DON'T TELL, GROUNDED FIGURES (every image must say "
        f"something true about the music), and the sentence rules: relaxed, "
        f"connected, medium-length sentences, no clipped fragments, no crammed "
        f"lists, no em dashes, no sign-off.\n"
        f"Target length per pitch: {length} (total across the paragraphs).\n\n"
        "Write each pitch as normal prose with blank lines between its paragraphs. "
        "Separate the pitches from each other with a line containing ONLY:\n"
        f"{PITCH_DELIM}\n"
        "Do not number the pitches, do not give them titles, and do not add any "
        "other commentary before, between, or after them.\n\n"
        "--- ARTIST BACKGROUND (ground every claim in this) ---\n"
        f"{context}\n"
        "--- END ---"
    )


# --- learning insights ("what worked / what didn't") ----------------------

INSIGHTS_SYSTEM = (
    "You are a PR lead reviewing how an editor rated and rewrote a batch of pitch "
    "drafts. You infer, from their stars and their edits, what to do more of and "
    "what to avoid next time. You are concrete and brief, and you never invent "
    "preferences the data doesn't show."
)


def insights_prompt(signal: dict) -> str:
    return (
        "Below is one artist's pitch feedback: star ratings, the versions the user "
        "kept, the ones they rejected, the specific edits they made (text they "
        "added vs. removed), and any written comments. Comments are the user "
        "telling you directly what worked or didn't; weight them heaviest. Infer "
        "their preferences and return ONLY a JSON object:\n"
        "{\n"
        '  "blurb": "2-3 sentences, plain language, on what has been landing and '
        'what has not for this artist",\n'
        '  "worked": [3-6 short, concrete things to do MORE of],\n'
        '  "avoid": [3-6 short, concrete things to STOP doing]\n'
        "}\n\n"
        "Base every point on the evidence. If they consistently cut a certain kind "
        "of phrase, 'avoid' it. If a high-rated version has a trait, 'worked' it. "
        "Keep each item a few words. Do not invent.\n\n"
        "ATTRIBUTE EDITS CORRECTLY. Edits may carry user-chosen edit_kinds tags "
        "(content, phrasing, style, grammar, facts, length). An edit tagged "
        "phrasing/style/grammar/length says the WORDING was wrong, never the "
        "topic: if the user rewrote a clunky sentence about a previous project, "
        "the lesson is about the clunk, NOT 'avoid mentioning previous "
        "projects'. Only edits tagged content or facts (or clear evidence across "
        "several edits) justify rules about what topics or facts to include or "
        "drop. Untagged edits: be conservative, prefer style-level lessons.\n\n"
        "RESPECT THE USER'S CURATION. If the signal lists user_rejected_rules, "
        "the user explicitly deleted those inferences as wrong: never restate "
        "them or close paraphrases of them. If it lists user_pinned_rules, those "
        "are ground truth the user wrote; do not contradict or duplicate them.\n\n"
        f"--- FEEDBACK SIGNAL ---\n{signal}\n--- END ---"
    )


# --- house rules (cross-artist learning) ----------------------------------

HOUSE_SYSTEM = (
    "You are the PR lead of a record label, distilling how the team's pitch "
    "feedback across MANY different artists should change the house writing "
    "style. You extract only the rules that generalize beyond any single artist, "
    "and you never invent preferences the data doesn't show."
)


def house_rules_prompt(signal: dict) -> str:
    return (
        "Below is pitch feedback aggregated across every artist on the label: "
        "each artist's own worked/avoid summary, overall rating stats, and the "
        "user's written comments on what is and isn't working. Distill the "
        "GENERALIZABLE house rules and return ONLY a JSON object:\n"
        "{\n"
        '  "blurb": "1-2 plain sentences on the label-wide pattern in the feedback",\n'
        '  "worked": [3-6 short, concrete rules to follow in EVERY future pitch],\n'
        '  "avoid": [3-6 short, concrete things to stop doing in EVERY future pitch]\n'
        "}\n\n"
        "Every rule must transfer across artists: sentence style, structure, tone, "
        "imagery discipline, length, what kinds of facts to lead with. DROP "
        "anything tied to one artist's world (a specific image, album, scene, or "
        "genre quirk). The user's written comments are direct instructions; weight "
        "them heaviest. If the evidence is thin, return fewer rules rather than "
        "inventing any.\n\n"
        "RESPECT THE USER'S CURATION. If the signal lists user_rejected_rules, "
        "the user explicitly deleted those inferences as wrong: never restate "
        "them or close paraphrases of them. If it lists user_pinned_rules, those "
        "are ground truth the user wrote; do not contradict or duplicate them.\n\n"
        f"--- LABEL-WIDE FEEDBACK ---\n{signal}\n--- END ---"
    )


# --- theme suggestion (the "generate more" button) ------------------------

SUGGEST_SYSTEM = (
    "You expand a set of short descriptor tags for a music pitch, staying strictly "
    "grounded in the source material. You never invent facts."
)


def suggest_themes_prompt(context: str, existing: list[str], n: int = 6) -> str:
    return (
        f"From the artist background below, suggest up to {n} ADDITIONAL short "
        f"descriptor tags (1-4 words each) that capture themes, sonic qualities, or "
        f"visual motifs and are NOT already in this list:\n{existing}\n\n"
        "Base every tag on the material; do not repeat the existing ones and do not "
        "invent facts. Return ONLY a JSON array of strings.\n\n"
        "--- ARTIST BACKGROUND ---\n"
        f"{context}\n"
        "--- END ---"
    )


# --- Stage 3: style & anti-AI audit ---------------------------------------

AUDIT_SYSTEM = (
    "You are a ruthless line editor. You strip AI/PR clichés and the tells of "
    "machine writing out of music pitches, ground every strained metaphor, break "
    "run-on sentences, and replace it all with concrete, flowing, legible human "
    "prose, while leaving the writer's intentional voice and structure intact. "
    + STYLE_RULES
)


def audit_prompt(draft: str, flagged: list[str],
                 tag_phrases: list[str] | None = None) -> str:
    flagged_note = (
        f"A deterministic scan flagged these banned phrases in the draft: {flagged}. "
        "Remove or rewrite every one of them.\n\n"
        if flagged else
        "Scan the draft yourself for any generic PR/AI clichés and rewrite them.\n\n"
    )
    tags_note = (
        f"DISSOLVE THE TAGS. These theme tags were briefing inputs and must not "
        f"appear in the pitch verbatim: {tag_phrases}. If one shows up "
        "word-for-word (and is not a proper noun like an album or genre name), "
        "rewrite that sentence so the idea stays but the exact wording goes.\n\n"
        if tag_phrases else ""
    )
    return (
        "Edit the pitch below so it reads as natural, human, professional prose with "
        "zero clichés. Replace buzzwords with a concrete image, a specific sonic "
        "detail, or a real fact from the pitch. Do not add facts.\n\n"
        "Also fix these problems:\n"
        "- GROUND THE FIGURES. Rewrite or delete any metaphor or simile that is "
        "surreal, melodramatic, doesn't quite parse (e.g. \"singing over VHS "
        "static like she's the girl in a home movie nobody meant to keep\"), or is "
        "empty wordplay that riffs on a title or conceit without saying anything "
        "about the sound (e.g. \"gets the antique-spinning-wheel treatment\"). A "
        "figure stays only if it tells the editor something true about how the "
        "music sounds or feels; otherwise replace it with a plain, true statement.\n"
        "- BREAK RUN-ONS. Split any sentence that stacks three or more clauses or "
        "comma-separated items into shorter sentences. Do not let a sentence cram a "
        "whole list of details; keep the two or three best and cut the rest.\n"
        "- FOLD IN FRAGMENTS. Merge any clipped, stranded fragment (\"Day Wave "
        "produced.\") into a neighbouring sentence so the prose reads connected, "
        "not punchy.\n"
        "- Delete EVERY em dash and en dash (no —, no –). Replace with a comma, a "
        "period, parentheses, or a rephrase so the sentence still flows.\n"
        "- Cut colons down to at most one, and never a colon used for dramatic "
        "reveal.\n"
        "- Delete any sign-off or call to action (\"happy to send\", \"I can send "
        "the link / press photos\", \"let me know\"). End on the record or momentum.\n"
        "- Drop a producer/collaborator mention if the name isn't a recognizable "
        "draw.\n\n"
        "Preserve exactly: the paragraph structure (keep the \\n\\n breaks), every "
        "fact, every verbatim press quote, AND the pitch's deliberate voice. A "
        "playful, sensory pitch stays playful and sensory; only remove the generic "
        "clichés and the tells, never flatten it into neutral copy.\n\n"
        f"{flagged_note}"
        f"{tags_note}"
        "Return ONLY the edited pitch text, no preamble, no explanation.\n\n"
        "--- DRAFT ---\n"
        f"{draft}\n"
        "--- END ---"
    )

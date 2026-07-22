"""Prompt engineering for the pitch pipeline: the two strategic archetypes, the
banned-phrase constraints, and the few-shot system prompts each stage uses.

Kept in one module (data, not logic) so a non-engineer can tune the voice, add
banned phrases, or extend the few-shot set without touching pipeline code.
"""

# --- Strategic archetypes (the core domain logic) -------------------------

ARCHETYPE_A = "Archetype_A"  # Story & Momentum (emerging)
ARCHETYPE_B = "Archetype_B"  # Authority & Press (established)

ARCHETYPES = {
    ARCHETYPE_A: {
        "name": "Story & Momentum",
        "when": (
            "Emerging artists with lower traction or credibility, thin press, few "
            "co-signs. The heavy authority material isn't there yet."
        ),
        "fill_with": (
            "Lead with the release itself and the story behind the artist: the "
            "scene they came up in, their origins and aesthetic, and whatever "
            "early momentum exists (buzzy singles, a cult following, co-signs, "
            "tour dates, a first bit of press). Build the credibility case from "
            "the ground up out of concrete, specific facts, not adjectives."
        ),
    },
    ARCHETYPE_B: {
        "name": "Authority & Press",
        "when": (
            "Established artists with heavy press quotes, notable co-signs, chart "
            "positions, or strong streaming numbers. There is real leverage to lead "
            "with."
        ),
        "fill_with": (
            "Lead with the strongest credibility: the biggest press quote or "
            "outlet, the notable co-sign, the chart position, the streaming "
            "number. Stack the achievements into a case that this artist has "
            "already arrived and is still climbing."
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

# The whole voice, in one brief. The gold examples below are the real target;
# this brief only names what they have in common so the model has the pattern in
# words too. Resist re-growing it: new lessons belong in the learned editor's
# notes (feedback.py), and the surest way to teach the voice is to add another
# gold example, not another rule.
VOICE_BRIEF = (
    "HOW TO WRITE\n"
    "Write like a music publicist sending an editor a one-sheet: clear, "
    "confident, factual prose that leads with news and earns attention with real "
    "achievements, not adjectives. The gold examples below are the target; match "
    "their register, not any single one's subject.\n"
    "- Lead with the news. Open with the artist and the immediate reason for the "
    "pitch, the new single, video, mixtape, tour, or announcement, stated "
    "plainly. Never open with a metaphor, a mood, or a scene.\n"
    "- Stack real credibility. The substance of a pitch is concrete achievement: "
    "named press outlets, streaming and chart numbers, co-signs, festival slots, "
    "tourmates, collaborators, sold-out dates, the label. Surface these, do not "
    "trim them; density of real facts is the point. Use only facts present in the "
    "source, verbatim, and never invent a number, outlet, quote, or co-sign.\n"
    "- Build momentum. Arrange the facts into an ascending case that this artist "
    "is on the rise, and give the reader a reason to care right now.\n"
    "- One quote, for the thesis. When the source has an artist quote that frames "
    "the project's intent or story, use it verbatim to anchor the pitch. Do not "
    "stack several quotes, and never invent one.\n"
    "- Two movements. First the immediate news and the momentum around it; then "
    "the origin story and the longer case for why the artist matters. End on "
    "forward motion, what is next or coming, not a sign-off or call to action.\n"
    "- Keep the prose plain and journalistic and let the facts carry it. A light "
    "flourish is welcome when it is bolted to a fact (\"glitter-encrusted "
    "electronic pop\", \"melt-in-your-mouth dance pop earworms\"), but never a "
    "whole sentence of atmosphere, never an extended metaphor, and never "
    "worldbuilding for its own sake. If a phrase carries no information, cut it.\n"
    "- Punctuation is normal professional prose. Em dashes, colons, and lists are "
    "all fine, used the way the examples use them. Write naturally and name "
    "producers, collaborators, and outlets freely; that is the kind of fact an "
    "editor wants."
)

# Style presets for the UI dropdown — the register the writer adopts. Each maps
# to a one-line instruction fed to the generator. "match" leans on the extracted
# artist_voice; the rest set an explicit register.
STYLE_PRESETS: dict[str, tuple[str, str]] = {
    "match":       ("Match the artist",
                    "Let the artist's own energy set the register, still newsy and fact-led."),
    "understated": ("Cool & understated",
                    "Calm and confident, low on adjectives. Let the facts and details carry it."),
    "vivid":       ("Warm & vivid",
                    "A little more colour and energy, every flourish still bolted to a fact."),
    "authority":   ("Authority & press",
                    "Lead with leverage: the biggest press, co-signs, chart and streaming numbers."),
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
    "material a writer will use, above all the marketable facts and achievements "
    "that build the artist's credibility. You are precise and never invent facts."
)


def classifier_prompt(context: str) -> str:
    return (
        "Analyze the artist background below and return ONLY a JSON object with this "
        "exact shape:\n"
        "{\n"
        '  "archetype": "Archetype_A" | "Archetype_B",\n'
        '  "news_hook": "the single immediate reason for this pitch (the new single, video, mixtape, tour, or announcement) the pitch should open with",\n'
        '  "momentum_points": [the concrete achievements to STACK, verbatim from the source: named press outlets, streaming and chart numbers, co-signs, festival slots, tourmates, collaborators, sold-out or notable shows, labels, list placements],\n'
        '  "key_anchors": [concrete sonic, visual, or biographical details to build on],\n'
        '  "press_quotes": [verbatim quotes actually present in the text, with source if given],\n'
        '  "cultural_themes": [themes/contradictions the artist embodies],\n'
        '  "comparison_artists": [named acts a writer can anchor to for "for fans of X"],\n'
        '  "sensory_motifs": [recurring images, textures, colours, or objects from the artist\'s world, if any],\n'
        '  "descriptors": [8-14 short clickable tags, 1-4 words each, capturing the record\'s genre, sonic qualities, themes, and scene - the toggles a user picks from],\n'
        '  "angle_options": [2-3 distinct one-line strategic angles the pitch could lead with],\n'
        '  "artist_voice": "1-2 sentences naming the artist\'s energy and register (confident? playful? austere? deadpan?) so the prose can match it. Keep it light; this is register, not a mood board",\n'
        '  "recommended_angle": "the single strongest one-line strategic angle (usually angle_options[0])"\n'
        "}\n\n"
        f"Choose {ARCHETYPE_A} ({ARCHETYPES[ARCHETYPE_A]['name']}) when: "
        f"{ARCHETYPES[ARCHETYPE_A]['when']}\n"
        f"Choose {ARCHETYPE_B} ({ARCHETYPES[ARCHETYPE_B]['name']}) when: "
        f"{ARCHETYPES[ARCHETYPE_B]['when']}\n\n"
        "Rules: momentum_points and press_quotes must appear verbatim in the text "
        "(else empty list); these are the credibility, so be thorough and pull "
        "every real outlet, number, co-sign, and tour fact. comparison_artists "
        "must be acts explicitly named in the source (as influences, tourmates, or "
        "reference points); do not invent comparisons. descriptors and artist_voice "
        "are read from the source; do not fabricate a personality the material "
        "doesn't support. descriptors should be crisp and human-readable (e.g. "
        "\"shoegaze trap\", \"hyperpop\", \"detroit electronic\").\n\n"
        "--- ARTIST BACKGROUND ---\n"
        f"{context}\n"
        "--- END ---"
    )


# --- Gold-standard examples (few-shot) ------------------------------------
# Seven real pitches that define the house voice: professional music one-sheets
# that lead with news and stack concrete achievements. The model imitates
# examples far more faithfully than it follows described rules, so these carry
# the register. They are kept verbatim as data so (a) the exemplar library can
# seed from them and (b) the feedback loop can recognise and skip a user "edit"
# that is really one of these pasted back in. They are calibration, not material:
# the prompt forbids reusing their specific facts, phrases, or openings.

GOLD_PITCH_1 = """Vancouver artist and producer Sophia Stel has just shared her new single "Molly In The Club". Self-produced and written by Stel, the track is highlighted by its playful music video, which she shot with her best friends earlier this summer at the Vancouver Aquarium, and arrives following heavy fan demand for the track throughout her recently wrapped headline international tour. "Molly In The Club" serves as her second release with A24 Music after April's "Bitches Talk Shit", which garnered praise from the likes of Pitchfork, NME, DAZED, CRACK, Pigeons & Planes, CLASH, and Gorilla vs. Bear, and follows her run opening for Lorde at the Kia Forum in Los Angeles last month. Recent months have also seen Stel make her runway debut at Ann Demeulemeester's Paris Fashion Week SS26 show, grace the covers of The Face and NME, and model spreads for Palace Skateboards and BASKETCASE following the release of her breakout EP, How to Win At Solitaire, the deluxe edition of which features collaborations with Mura Masa, Tommy Genesis, and Cecile Believe.

How to Win At Solitaire was produced, written, and recorded by Stel in a makeshift basement studio at Vancouver's since shuttered Paradise, the DIY club she worked in at the time. Released in September, it served as her second project following her 2024 debut EP, Object Permanence. The 2025 deluxe edition featured sleeper hit "I'll Take It", which rapidly caught fire on TikTok — and earned her co-signs from Troye Sivan and Megan Skiendiel of KATSEYE. Hailing from the Pacific Northwest, she first cut her teeth within Vancouver's local music scene, turning heads for her free-flowing prose, Y2K-indebted visuals, and mythos-tinted autobiography. Coupling lyricism inspired by her everyday life with patchwork aesthetics infused with the spontaneous, DIY ethos of homemade digicam videos, Stel has also been championed by PC Music legend A.G. Cook and was named to the The NME 100 in 2025. In addition to a performance at Pitchfork Festival in Paris, she was also recently selected for this year's DAZED 100 and Pigeons & Planes' 26 Artists To Watch In 2026 list, while earning spots on Best Of 2025 lists from The Face, Notion, Gorilla vs. Bear, and Hearing Things. She is currently working on her debut album."""

GOLD_PITCH_2 = """Thoom could have made two records: one rooted in American pop and another in experimental, punk-influenced Arabic music. Instead, she made Everyday, everything is at stake, because separating those sides of her music would have meant separating parts of herself. “I would be lying to my listeners if I tried to separate what seems the most natural to me,” she says. “The contradiction is the point.” You can hear that decision across the nine-song project with “December Forever” embracing the English pop songwriting she had long wanted to master, while “Janani,” the fully Arabic focus track, moves into more experimental territory. Executive-produced by Dylan Brady of 100 gecs and created between Los Angeles and Lebanon, the project takes its title from what she describes as “the immigrant mentality”: the reality of building a life in America while carrying family, history, and another part of herself in Lebanon, never fully integrating into either. Inspired by her travels, the project is “part diary, part mythology,” with each song written as its own intense, self-contained story. Less a confession than a record of survival, the result is, in Thoom’s words, “messy, pop, Arabic, experimental, and unapologetic.” That same instinct shapes how she writes: “Melody always comes before the lyrics for me. The emotion always comes before you have the words to express it.”

On “Towards the sky,” Thoom turns the rhetoric of exile into something triumphant. Released July 17 with an accompanying music video, the single captures the project's core tensions between displacement and belonging, tenderness and rage, girlhood and revolution. The single follows “December Forever” (500K+ streams) which appeared in an Instagram Story of Arca singing along last October, and serves as the final release ahead of the project’s arrival on July 31.

The project arrives amid growing international momentum for Thoom. Alongside recent shows in Cairo and Los Angeles, including a show with Cece Natalie, she has performed across the US and Europe with Bassvictim, Jockstrap, Yves Tumor, Underscores, Frost Children, Dorian Electra, and The Dare. Everyday, everything is at stake, Thoom’s first project since her 2023 debut EP Fantasy for Danger, is the fullest realization yet of a sound she has spent years developing. A separate full-length album will follow later this summer, ahead of an unannounced direct-support run across more than 20 North American cities this fall."""

GOLD_PITCH_3 = """Fresh off the release of her debut mixtape Lullabies, Glasgow-raised artist and producer heartcoregirl has just shared the video for her new single, "bloom". A hopeful, grunge-tinted anthem, "bloom" explores the tension of societal objectification while yearning for more and is highlighted by a playful visual that follows her around The Ritz-Carlton Hotel in London — dressed formally, interacting with the guests, and imagining what it would be like to one day live the high life, too. The song stamps her first outing since dropping the aforementioned Lullabies in February, which features 12 tracks and is rooted in themes of femininity and sensitivity, even amidst harsh environments. A self-confessional outing that invites listeners into the world heartcoregirl inhabits, the tape is inspired by her experience coming up within Europe's underground SoundCloud scene, often finding herself as the only woman on the lineup at the shows where she first cut her teeth. It arrived on the heels of previously released singles "cherry sundae", "no trace", "Little baby sweet", and "Glide" — as well as three years spent performing the collection of songs in clubs from Tokyo to Prague.

First earning a cult following online for her lullaby vocals and dollhouse aesthetics, the Glaswegian vocalist and visual artist is known for her dreamy, shoegaze trap sound, intimate live performances, and introspective lyricism that soundtracks life's softest (and hardest) moments. After breaking out with "no trace" in 2023, she continued to turn heads with a run of singles, recent shows alongside fakemink and Bassvictim, and frequent collaborations with buzzy NYC electronic duo Suzy Sheer. In addition to the release of Lullabies, she was also recently selected for the NME 100 in 2025."""

GOLD_PITCH_4 = """Tiffany Day has just announced her upcoming twelve-stop HALO TOUR EUROPE. Arriving ahead of her upcoming eight-stop HALO Tour, which was recently announced, sold out, upgraded, and sold out once again, the HALO TOUR EUROPE spans 10 countries over the span of two weeks, as Tiffany takes her blown-out, bass-heavy electro-pop sound to international audiences for the first time. Pre-sale starts today with general sale starting Friday, June 26th at 10 am BST. This tour comes on the heels of her link-up with underground rap phenom slayr for her first single of the summer, “Constantly”, marking Tiffany's first release since her breakthrough album HALO arrived in early April. Fans had been anticipating the collaboration since mid-April, when slayr alluded to an upcoming track with Tiffany on X, and excitement only grew when Tiffany brought him out during her set at Summer Smash this past weekend to perform the unreleased song live. With back-to-back tours on the horizon, Tiffany Day continues to build off the momentum of HALO while bringing her music to audiences around the world.

Over the past two years, Tiffany Day has emerged as one of the most compelling voices in hyper-digital pop. In 2024, she independently funded and sold out several headline shows across a North American tour. She later expanded into the DJ scene, launching BASSFLUFF, a series of standalone events that generated viral moments DJing everywhere from gyms to nail salons. Her 2025 releases marked a sharp sonic evolution, leaning into electroclash and hyperpop textures, with singles like “BREAKUP”, “TELL ME WHAT I DID”, and “START OVER” generating millions of views across platforms and earning coverage from NME, Ones to Watch, On The Radar, and beyond. That momentum culminated in her album HALO, released April 3rd, 2026 via Broke Records. The project debuted at #1 on the Apple Music Electronic chart and #25 on the Billboard Electronic/Dance Albums Chart, drawing early co-signs from artists like Laufey, Yunjin (LE SSERAFIM), and The Weeknd, alongside coverage from Pitchfork, The FADER, NYLON, LA Times, and more. HALO stands as Tiffany’s most cohesive and ambitious work to date, further establishing her as a defining voice in the next era of hyperpop while laying the foundation for her next chapter."""

GOLD_PITCH_5 = """Following her standout B2B performance with umru at Palomosa Festival in Montreal and the release of her first single of 2026, "Stereo", French pop artist and producer Cannelle has announced that her debut mixtape CINNA will be out June 26th, alongside the release of her newest video single, "Dis Moi" and the announcement of her headlining Los Angeles and New York City project release shows. "Dis Moi" weaves in and out of trap influences and bilingual lyrics, meshing English and French into a congruent, larger-than-life synth-pop hit. “Dis-Moi’ is sexy, and seductive. I wanted to make a fun song about a crush that sounds catchy, but still mysterious.” This arrives as the second single off her forthcoming debut mixtape CINNA, a record which was crafted after two years of near-daily studio sessions in New York and Los Angeles, plus a slate of buzzy live performances in Paris. Sung in both French and English and co-produced alongside Chicken, Oscar Scheller, and Warpstr, it’s more than just a collection of avant-garde, rave-ready earworms, as composed as they are boisterous. It’s a beacon for every brilliant Black woman determined to soundtrack her own life, regardless of genre stigma — and for every young creative who thrives when they let loose.

The 20-year-old Marseille-born, Los Angeles-based artist’s glitter-encrusted electronic pop has captivated in-the-know listeners since her 2024 breakout single “LUCKY”, a self-produced track that has since surpassed 1M streams across platforms. While juggling an established modeling career that’s seen her work with Valentino and Heaven by Marc Jacobs, she continued to thrill French and international fans alike with melt-in-your-mouth dance pop earworms like “CLOVER”, “DIAMOND CUTS”, “FILLE”, and “MP3”. Having packed out shows in Paris (where she distributed blue wigs across a crowd too rapt to take their phones out) and opened for Ninajirachi, Cannelle is now ready for the next step in her rise to stardom."""

GOLD_PITCH_6 = """Fresh off the release of her new mixtape Blue Angel Sparkling Silver 2, Austin artist and producer Quiet Light (AKA Riya Mahesh) has just announced that she'll be embarking on a headline European tour this fall. The 11-stop run kicks off on October 28th in Barcelona and concludes in London on November 11th. Artist pre-sale begins tomorrow at 10AM local time. Sign up now to receive early access to tickets (RSVP HERE). General tickets are on-sale this Wednesday at 10AM local time. Led by singles "Berlin", "Postinternetfame", and "Self Tape", Blue Angel Sparkling Silver 2 serves as a sister tape to Mahesh's 2023 project, Blue Angel Sparkling Silver. The self-written and produced record stamped her debut release with True Panther and garnered praise from the likes of Rolling Stone, Pitchfork, NPR, NME, The FADER, The Quietus, and Stereogum. Mahesh also recently played a slate of release shows in support of the project and launched a limited-edition vinyl, which features a 2-disc pressing of both Blue Angel Sparkling Silver and Blue Angel Sparkling Silver 2.

Hailing from Dallas, Mahesh first arrived on the scene with her 2020 self-titled debut EP, Quiet Light. The project kicked off a run of independent, self-produced records, with Quiet Light turning heads for her irresistible hooks and an unmistakable production style that bridges the gap between folk, electronic, and pop music. But as life started to get serious, and medical school and a record deal came knocking, Mahesh moved back to Texas, finding herself nostalgic for the freedom of recording Blue Angel Sparkling Silver — a time when the confines of a professional career never crossed her mind, and every creative choice was unfiltered, made simply out of love for the music. Enter Blue Angel Sparkling Silver 2, which finds its magic somewhere between suburban nostalgia and the uncertainty of a long, open road, bucking genre confines in search of unfettered emotion. The project is one of reconciling contradiction, as Mahesh oscillates between the sterility and carnage of the Massachusetts hospital where she’s currently completing her medical school training and the secluded softness of her bedroom studio in Austin. As she puts it: “This record is for people who dream about what their life could be like.”"""

GOLD_PITCH_7 = """Fresh off a standout performance at Rolling Loud Orlando, his latest EP Mastiff and the announcement of his headlining Mastiff: Pink Tiles Tour, New Detroit artist Lelo has just shared a new single, "Get Geeked". Fully diving into his Ghettotech influences (watch his recent set at The Lot Radio here), "Get Geeked" blends upbeat rap bars with the sonics of classic Detroit Electronic music –– resulting in a groovy, dancefloor-ready anthem. This new single arrives ahead of what's about to be a busy summer for Lelo as he hits the road for his headlining Mastiff: Pink Tiles Tour, kicking off on July 6th in Toronto after Lelo's debut Rolling Loud set in Orlando this weekend, Summerfest in June. Performing alongside Groovepill and comprised of 13 tour dates and two festivals, as well as a Boiler Room performance in NYC alongside JID, Kenny Beats and TiaCorine, the forthcoming Mastiff: Pink Tiles Tour will bring Lelo's New Detroit sound to the masses after a breakout year in 2025. After Lelo's biggest streaming debut yet with recent single "Monetize" (7M+ Streams), the release of "Yoppenheimer Remix" with Joey Bada$$ and the Mastiff EP, "Get Geeked" is the latest move in a momentous start to 2026 for Lelo and serves as a prime example of how he's continuing to evolve his New Detroit sound –– which he's contextualized in recent profiles with Pitchfork, Highsnobiety and The FADER. After being stamped by both Billboard and COMPLEX as a 2026 Artist to Watch to kick off the year, Lelo has lived up to the name, keeping the momentum going after a triumphant 2025 debut album, New Detroit (7.8 rating + 7th Best Rap Album of the year from Pitchfork) and a subsequent sold-out four city headlining New Detroit Tour.

While new to a more national spotlight, Lelo has been a consistent standout within the regional Detroit scene. Early works such as "Hughes" (10M+ Streams) and "Daybreakers" grabbed immediate attention from new listeners, bolstering a rocket-like ascent for the young lyricist. Listeners have had the opportunity to witness Lelo reimagine the Detroit sound in real time, with each new output offering a unique sonic experience within the usually familiar sound. More experimental production choices, like the inclusion of 80s Detroit House music within his instrumentals, are responsible for the undeniable intrigue that his music brings. The bold, Sade-sampling "Main Event" (28M+ Streams) in tandem with his other 2025 singles earned him strong praise from fellow artists such as Earl Sweatshirt, Pi'erre Bourne, LUCKI, and Brent Faiyaz, just to name a few. Though the voice of many through his growing "New Detroit" movement, the young standout prefers to operate alone on his projects, impressively surpassing over a million monthly listeners before ever releasing a song with a feature. The Motor City has much to look forward to with their very own Lelo leading the charge."""

GOLD_PITCHES = [GOLD_PITCH_1, GOLD_PITCH_2, GOLD_PITCH_3, GOLD_PITCH_4,
                GOLD_PITCH_5, GOLD_PITCH_6, GOLD_PITCH_7]

# Static fallback for the generator when the exemplar library is empty (normally
# retrieval in logic/exemplars.py picks the 2-3 most relevant instead). One
# established/press example and one emerging/story example.
GOLD_EXAMPLES = (
    "GOLD-STANDARD EXAMPLES - real pitches written in exactly the voice to aim "
    "for. Study how each leads with the news, stacks concrete achievements "
    "(press, numbers, co-signs, tours), and ends on forward momentum. Do NOT "
    "reuse their specific facts, phrases, or openings in your own pitches. They "
    "calibrate the voice, nothing more.\n"
    "\n"
    "EXAMPLE 1 (Authority & Press):\n"
    + GOLD_PITCH_1 + "\n"
    "\n"
    "EXAMPLE 2 (Story & Momentum):\n"
    + GOLD_PITCH_3
)


# --- Stage 2: pitch generator ---------------------------------------------

# Pitches are multi-paragraph prose, which does not survive a JSON array (the
# model emits real newlines inside the strings and breaks the parse). So the
# generator returns plain text with pitches split by this delimiter line.
PITCH_DELIM = "===PITCH==="

# Persona + voice brief, without examples: the pipeline appends the retrieved
# gold exemplars (logic/exemplars.py) and the team's before/after edit pairs.
GENERATOR_BASE = (
    "You are an elite music publicist writing a pitch to a specific editor. "
    "You write with concrete detail and a distinct point of view.\n\n"
    + VOICE_BRIEF
)

# Static fallback (base + built-in examples) for callers without a db handle.
GENERATOR_SYSTEM = GENERATOR_BASE + "\n\n" + GOLD_EXAMPLES


def generator_prompt(*, context: str, strategy: dict, num_options: int,
                     length: str, style: str, angle: str,
                     descriptors: list[str], learning: str = "",
                     avoid_openings: list[str] | None = None) -> str:
    arch = strategy.get("archetype", ARCHETYPE_A)
    meta = ARCHETYPES.get(arch, ARCHETYPES[ARCHETYPE_A])
    lead_angle = angle.strip() or strategy.get("recommended_angle", "")
    voice = strategy.get("artist_voice", "")
    desc_line = (
        f"Angles/themes the user wants foregrounded (weave in naturally, do not "
        f"paste verbatim unless a proper noun): {descriptors}\n" if descriptors else ""
    )
    news_hook = strategy.get("news_hook", "")
    hook_line = f"News hook to lead with: {news_hook}\n" if news_hook else ""
    learn_line = f"{learning}\n" if learning else ""
    avoid_line = (
        "These pitches already exist for this artist; make the new ones clearly "
        "DIFFERENT (a different lead, a different opening, a different set of facts "
        f"foregrounded), not variations on them:\n{[o[:160] for o in avoid_openings]}\n"
        if avoid_openings else ""
    )
    return (
        f"Strategic archetype: {arch}, {meta['name']}.\n"
        f"{meta['fill_with']}\n\n"
        f"{style_guidance(style, voice)}\n\n"
        f"{learn_line}"
        f"{avoid_line}"
        f"{hook_line}"
        f"Strategic angle to lead with: {lead_angle}\n"
        f"{desc_line}"
        f"MOMENTUM TO STACK (the credibility; use verbatim, and surface as many as "
        f"fit naturally, do not trim them away): {strategy.get('momentum_points', [])}\n"
        f"Comparison artists to anchor an editor (use only these, verbatim): "
        f"{strategy.get('comparison_artists', [])}\n"
        f"Key anchors: {strategy.get('key_anchors', [])}\n"
        f"Press quotes available (use verbatim, never invent): "
        f"{strategy.get('press_quotes', [])}\n"
        f"Cultural themes: {strategy.get('cultural_themes', [])}\n\n"
        f"OPEN each pitch by leading with the news: the artist as the subject and "
        f"the immediate reason for the pitch (the new single, video, tour, or "
        f"announcement), stated plainly like the gold examples (\"<Artist> has just "
        f"shared...\", \"Fresh off <X>, <Artist> has announced...\"). Never open "
        f"with a metaphor, mood, or scene. Then stack the momentum.\n"
        f"Write {num_options} DISTINCT pitch options. Each foregrounds a genuinely "
        f"different angle or lead, not paraphrases of one pitch.\n"
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
        "Rejected entries may carry 'reasons' (and the signal may include "
        "reject_reason_counts): those are the user naming the problem in their "
        "own words when they hit reject. Treat them like comments, the most "
        "direct evidence there is.\n\n"
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
        "them heaviest, alongside reject_reason_counts if present (the reasons "
        "the user tapped when rejecting drafts). If the evidence is thin, return "
        "fewer rules rather than inventing any.\n\n"
        "RESPECT THE USER'S CURATION. If the signal lists user_rejected_rules, "
        "the user explicitly deleted those inferences as wrong: never restate "
        "them or close paraphrases of them. If it lists user_pinned_rules, those "
        "are ground truth the user wrote; do not contradict or duplicate them.\n\n"
        f"--- LABEL-WIDE FEEDBACK ---\n{signal}\n--- END ---"
    )


# --- exemplar auto-tagging (the gold-pitch library) ------------------------

TAG_EXEMPLAR_SYSTEM = (
    "You catalogue reference pitches for a music PR team. You read one pitch "
    "and return the short retrieval handles that describe it. You never invent "
    "facts."
)


def tag_exemplar_prompt(text: str) -> str:
    return (
        "Read the reference pitch below and return ONLY a JSON object:\n"
        "{\n"
        f'  "archetype": "{ARCHETYPE_A}" | "{ARCHETYPE_B}",\n'
        '  "tags": [6-10 short handles, 1-3 words each: genres, moods, era, '
        'energy, "emerging artist" or "established artist", notable techniques]\n'
        "}\n\n"
        f"Choose {ARCHETYPE_A} ({ARCHETYPES[ARCHETYPE_A]['name']}) when the pitch "
        "is for an emerging artist and leads with the release and origin story; "
        f"choose {ARCHETYPE_B} ({ARCHETYPES[ARCHETYPE_B]['name']}) when it leads "
        "with heavy press, co-signs, chart or streaming numbers.\n\n"
        "--- PITCH ---\n"
        f"{text}\n"
        "--- END ---"
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


# --- Stage 3: surgical self-revision ---------------------------------------
# The old Stage 3 handed the whole draft to a cheap model with a 12-point rewrite
# brief; it chopped flowing sentences into fragments and deleted the best lines
# (the exact damage the user kept rejecting). Now revision only runs when the
# deterministic scan actually flags something, it is done by the SAME writer
# model that produced the draft, and it may touch only the flagged sentences.

REVISE_SYSTEM = (
    "You are the publicist who wrote this pitch, giving it one last pass before "
    "it goes out. You fix only the specific problems you are given and reproduce "
    "every other sentence exactly as written, preserving the rhythm and voice."
)


def revise_prompt(draft: str, flagged: list[str],
                  tag_phrases: list[str] | None = None) -> str:
    problems = []
    if flagged:
        problems.append(
            f"These clichés appear in the draft and must go: {flagged}. Rewrite "
            "each sentence containing one so the idea stays but the cliché is "
            "replaced with a concrete detail already in the pitch."
        )
    if tag_phrases:
        problems.append(
            f"These briefing tags leaked into the prose verbatim: {tag_phrases}. "
            "Unless the tag is a proper noun (an album, song, or genre name), "
            "rewrite the sentence carrying it so the idea stays but the exact "
            "wording goes."
        )
    problem_block = "\n".join(f"- {p}" for p in problems)
    return (
        "Fix ONLY the problems listed below. Every sentence that does not contain "
        "one of these problems must be reproduced word for word; keep the "
        "paragraph breaks, every fact, and every verbatim quote. Do not add "
        "facts, and do not otherwise rewrite, tighten, or improve the pitch.\n\n"
        f"{problem_block}\n\n"
        "Return ONLY the pitch text, no preamble, no explanation.\n\n"
        "--- DRAFT ---\n"
        f"{draft}\n"
        "--- END ---"
    )

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from dataclasses import dataclass

from app.data.genre_taxonomy import INTERNAL_BROAD_CLUSTERS, INTERNAL_GENRES


@dataclass(frozen=True)
class ArtistGenreProfile:
    canonical_genres: tuple[str, ...]
    broad_clusters: tuple[str, ...]
    sonic_traits: tuple[str, ...] = ()
    confidence: str = "high"
    source: str = "curated genre mapping"
    taste_role_hint: str | None = None


BROAD_CLUSTER_GENRES: dict[str, set[str]] = {
    "Alternative / Indie Rock": {
        "alternative rock",
        "indie rock",
        "britpop",
        "dream pop",
        "shoegaze",
        "shoegaze-influenced alternative rock",
        "garage rock",
        "post-punk revival",
        "art rock",
        "indie pop",
        "post-punk",
        "new wave",
        "noise rock",
        "psychedelic rock",
    },
    "Emo / Pop Punk / Post-Hardcore": {
        "emo",
        "pop punk",
        "post-hardcore",
        "screamo",
        "emo pop",
        "alternative punk",
        "punk rock",
        "punk",
        "hardcore punk",
    },
    "Heavy Alternative / Metalcore": {
        "metalcore",
        "alternative metal",
        "nu metal",
        "hard rock",
        "electronic rock",
        "post-metal",
        "heavy alternative",
        "metal",
        "heavy metal",
        "deathcore",
        "death metal",
        "progressive metal",
    },
    "Pop / Pop Rock Crossover": {
        "pop rock",
        "alternative pop",
        "synth-pop",
        "electropop",
        "indie pop",
        "pop",
        "pop rap",
        "dance-pop",
        "teen pop",
        "art pop",
        "europop",
    },
    "Malay / Nusantara Pop": {"malay pop", "malaysian pop", "indo pop", "indonesian pop", "nusantara pop"},
    "Malay / Nusantara Rock & Indie": {"malay rock", "malaysian rock", "indo rock", "indonesian rock", "nusantara rock", "malay indie", "indonesian indie"},
    "Dangdut": {"dangdut", "koplo"},
    "Mandopop / C-pop": {"mandopop", "mandarin pop", "c-pop", "chinese pop"},
    "Cantopop": {"cantopop", "cantonese pop", "hong kong pop"},
    "K-pop": {"k-pop", "k pop", "korean pop"},
    "J-Pop / J-Rock": {"j-pop", "j pop", "j-rock", "j rock", "japanese pop", "japanese rock"},
    "Tamil / Indian Film & Pop": {"tamil", "kollywood", "indian film", "filmi", "bollywood", "desi pop", "indian pop"},
    "Cinematic / Soundtrack": {
        "film score",
        "orchestral soundtrack",
        "game soundtrack",
        "ambient orchestral",
        "cinematic classical",
        "soundtrack",
        "cinematic orchestral",
    },
    "Electronic / Atmospheric": {
        "electronic",
        "ambient",
        "synthwave",
        "downtempo",
        "atmospheric electronic",
        "dance",
        "house",
        "vaporwave",
        "phonk",
        "darkwave",
        "techno",
        "trance",
        "drum and bass",
        "edm",
    },
    "Hip-Hop / Rap": {
        "hip-hop",
        "rap",
        "trap",
        "alternative hip-hop",
        "pop rap",
    },
    "R&B / Soul / Funk": {
        "r&b",
        "rhythm and blues",
        "soul",
        "neo-soul",
        "funk",
        "contemporary r&b",
    },
    "Jazz / Classical": {
        "jazz",
        "classical",
        "classical music",
        "contemporary classical",
        "classical crossover",
        "orchestral",
    },
    "Folk / Country / Acoustic": {
        "folk",
        "folk rock",
        "country",
        "country pop",
        "singer-songwriter",
        "acoustic",
        "americana",
    },
    "Rock / Classic Rock": {
        "rock",
        "classic rock",
        "progressive rock",
        "glam rock",
        "arena rock",
        "blues rock",
        "soft rock",
    },
    "Latin / Reggaeton": {
        "latin",
        "latin pop",
        "latin trap",
        "reggaeton",
        "urbano latino",
    },
    "Reggae / Dancehall": {
        "reggae",
        "dancehall",
        "roots reggae",
    },
}


ARTIST_GENRES: dict[str, ArtistGenreProfile] = {
    "bring me the horizon": ArtistGenreProfile(
        canonical_genres=("alternative rock", "metalcore", "post-hardcore", "electronic rock", "pop rock"),
        broad_clusters=("Alternative / Indie Rock", "Emo / Pop Punk / Post-Hardcore", "Heavy Alternative / Metalcore", "Pop / Pop Rock Crossover"),
        sonic_traits=("emotionally intense", "dramatic", "cathartic", "polished heavy production", "anthemic", "high-energy"),
        taste_role_hint="Core heavy-alt anchor",
    ),
    "my chemical romance": ArtistGenreProfile(
        canonical_genres=("emo", "pop punk", "alternative rock", "post-hardcore"),
        broad_clusters=("Emo / Pop Punk / Post-Hardcore", "Alternative / Indie Rock"),
        sonic_traits=("theatrical", "cathartic", "dramatic vocals", "melodic", "nostalgic"),
        taste_role_hint="Emo and pop-punk spine",
    ),
    "wisp": ArtistGenreProfile(
        canonical_genres=("shoegaze", "dream pop", "alternative rock"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("atmospheric", "hazy", "guitar-driven", "dreamy", "melancholic"),
        taste_role_hint="Shoegaze atmosphere",
    ),
    "oasis": ArtistGenreProfile(
        canonical_genres=("britpop", "alternative rock", "rock"),
        broad_clusters=("Alternative / Indie Rock",),
        sonic_traits=("nostalgic", "melodic", "anthemic", "british rock", "singalong"),
        taste_role_hint="Nostalgic British rock anchor",
    ),
    "deftones": ArtistGenreProfile(
        canonical_genres=("alternative metal", "nu metal", "shoegaze-influenced alternative rock"),
        broad_clusters=("Heavy Alternative / Metalcore", "Alternative / Indie Rock"),
        sonic_traits=("atmospheric", "heavy", "guitar-driven", "sensual tension", "textural"),
        taste_role_hint="Atmospheric heavy-alt pressure",
    ),
    "hans zimmer": ArtistGenreProfile(
        canonical_genres=("film score", "cinematic orchestral", "soundtrack", "ambient orchestral"),
        broad_clusters=("Cinematic / Soundtrack", "Electronic / Atmospheric"),
        sonic_traits=("cinematic", "orchestral", "dramatic", "wide-screen", "ambient tension"),
        taste_role_hint="Cinematic side quest",
    ),
    "radiohead": ArtistGenreProfile(
        canonical_genres=("alternative rock", "art rock", "electronic", "experimental rock"),
        broad_clusters=("Alternative / Indie Rock", "Electronic / Atmospheric"),
        sonic_traits=("experimental", "melancholic", "atmospheric", "introspective", "uneasy"),
    ),
    "linkin park": ArtistGenreProfile(
        canonical_genres=("nu metal", "alternative rock", "rap rock", "electronic rock"),
        broad_clusters=("Heavy Alternative / Metalcore", "Alternative / Indie Rock", "Hip-Hop / Rap"),
        sonic_traits=("cathartic", "high-energy", "melodic aggression", "electronic textures"),
    ),
    "foo fighters": ArtistGenreProfile(
        canonical_genres=("alternative rock", "post-grunge", "hard rock"),
        broad_clusters=("Alternative / Indie Rock", "Heavy Alternative / Metalcore"),
        sonic_traits=("guitar-driven", "anthemic", "high-energy", "classic rock momentum"),
    ),
    "the killers": ArtistGenreProfile(
        canonical_genres=("alternative rock", "indie rock", "post-punk revival", "synth-pop"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("anthemic", "nostalgic", "melodic", "glossy", "night-drive"),
    ),
    "cigarettes after sex": ArtistGenreProfile(
        canonical_genres=("dream pop", "ambient pop", "indie pop"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("hazy", "slow-burn", "atmospheric", "intimate", "melancholic"),
    ),
    "joji": ArtistGenreProfile(
        canonical_genres=("alternative r&b", "lo-fi", "indie pop", "trip hop"),
        broad_clusters=("Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("melancholic", "late-night", "minimal", "soft-focus"),
    ),
    "don toliver": ArtistGenreProfile(
        canonical_genres=("pop rap", "trap", "r&b"),
        broad_clusters=("Hip-Hop / Rap", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "slick", "rhythmic", "cinematic pop energy"),
    ),
    "fifty fifty": ArtistGenreProfile(
        canonical_genres=("k-pop", "pop", "dance pop"),
        broad_clusters=("Pop / Pop Rock Crossover",),
        sonic_traits=("polished", "bright", "melodic", "lightweight pop sheen"),
    ),
    "the strokes": ArtistGenreProfile(
        canonical_genres=("garage rock", "indie rock", "post-punk revival"),
        broad_clusters=("Alternative / Indie Rock",),
        sonic_traits=("cool-toned", "guitar-driven", "urban", "concise"),
    ),
    "tv girl": ArtistGenreProfile(
        canonical_genres=("indie pop", "hypnagogic pop", "lo-fi"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("nostalgic", "sample-heavy", "hazy", "wry"),
    ),
    "arctic monkeys": ArtistGenreProfile(
        canonical_genres=("indie rock", "garage rock", "alternative rock"),
        broad_clusters=("Alternative / Indie Rock",),
        sonic_traits=("guitar-driven", "stylish", "rhythmic", "sharp-edged"),
    ),
    "green day": ArtistGenreProfile(
        canonical_genres=("pop punk", "punk rock", "alternative rock"),
        broad_clusters=("Emo / Pop Punk / Post-Hardcore", "Alternative / Indie Rock"),
        sonic_traits=("energetic", "anthemic", "direct", "punk melodic"),
    ),
    "the smashing pumpkins": ArtistGenreProfile(
        canonical_genres=("alternative rock", "shoegaze", "dream pop"),
        broad_clusters=("Alternative / Indie Rock",),
        sonic_traits=("guitar-driven", "textural", "dreamy", "melancholic"),
    ),
    "kanye west": ArtistGenreProfile(
        canonical_genres=("hip-hop", "rap", "pop rap", "experimental hip-hop"),
        broad_clusters=("Hip-Hop / Rap", "Pop / Pop Rock Crossover"),
        sonic_traits=("maximalist", "sample-driven", "melodic", "ambitious production"),
    ),
    "thirty seconds to mars": ArtistGenreProfile(
        canonical_genres=("alternative rock", "emo", "post-grunge", "hard rock"),
        broad_clusters=("Alternative / Indie Rock", "Emo / Pop Punk / Post-Hardcore", "Heavy Alternative / Metalcore"),
        sonic_traits=("dramatic", "anthemic", "cinematic", "guitar-driven"),
    ),
    "coldplay": ArtistGenreProfile(
        canonical_genres=("alternative rock", "pop rock", "post-britpop"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "anthemic", "sentimental", "wide-screen"),
    ),
    "muse": ArtistGenreProfile(
        canonical_genres=("alternative rock", "progressive rock", "space rock", "electronic rock"),
        broad_clusters=("Alternative / Indie Rock", "Heavy Alternative / Metalcore", "Electronic / Atmospheric"),
        sonic_traits=("dramatic", "theatrical", "high-energy", "sci-fi scale"),
    ),
    "ramin djawadi": ArtistGenreProfile(
        canonical_genres=("film score", "orchestral soundtrack", "cinematic classical"),
        broad_clusters=("Cinematic / Soundtrack",),
        sonic_traits=("cinematic", "orchestral", "dramatic", "epic"),
    ),
    "maroon 5": ArtistGenreProfile(
        canonical_genres=("pop rock", "funk pop", "dance pop"),
        broad_clusters=("Pop / Pop Rock Crossover",),
        sonic_traits=("polished", "hook-driven", "radio-friendly", "groove-led"),
    ),
    "the kid laroi": ArtistGenreProfile(
        canonical_genres=("pop rap", "emo rap", "pop"),
        broad_clusters=("Hip-Hop / Rap", "Pop / Pop Rock Crossover", "Emo / Pop Punk / Post-Hardcore"),
        sonic_traits=("melodic", "confessional", "pop-polished", "youthful"),
    ),
    "yungblud": ArtistGenreProfile(
        canonical_genres=("pop punk", "alternative rock", "emo pop"),
        broad_clusters=("Emo / Pop Punk / Post-Hardcore", "Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("restless", "high-energy", "angsty", "anthemic"),
    ),
    "paramore": ArtistGenreProfile(
        canonical_genres=("pop punk", "emo pop", "alternative rock", "pop rock"),
        broad_clusters=("Emo / Pop Punk / Post-Hardcore", "Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("cathartic", "melodic", "high-energy", "sharp vocals"),
    ),
    "jay chou": ArtistGenreProfile(
        canonical_genres=("mandopop", "pop", "r&b", "pop rock"),
        broad_clusters=("Pop / Pop Rock Crossover",),
        sonic_traits=("melodic", "romantic", "cinematic pop", "piano-led"),
    ),
    "周杰倫": ArtistGenreProfile(
        canonical_genres=("mandopop", "pop", "r&b", "pop rock"),
        broad_clusters=("Pop / Pop Rock Crossover",),
        sonic_traits=("melodic", "romantic", "cinematic pop", "piano-led"),
    ),
    "hoobastank": ArtistGenreProfile(
        canonical_genres=("post-grunge", "alternative rock", "pop rock"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "earnest", "guitar-driven", "radio rock"),
    ),
    "post malone": ArtistGenreProfile(
        canonical_genres=("pop rap", "hip-hop", "pop rock"),
        broad_clusters=("Hip-Hop / Rap", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "genre-blending", "laid-back", "hook-heavy"),
    ),
    "strawberry guy": ArtistGenreProfile(
        canonical_genres=("dream pop", "indie pop", "bedroom pop"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("dreamy", "soft-focus", "nostalgic", "gentle"),
    ),
    "ludwig goransson": ArtistGenreProfile(
        canonical_genres=("film score", "orchestral soundtrack", "cinematic orchestral"),
        broad_clusters=("Cinematic / Soundtrack",),
        sonic_traits=("cinematic", "orchestral", "textural", "dramatic"),
    ),
    "ludwig göransson": ArtistGenreProfile(
        canonical_genres=("film score", "orchestral soundtrack", "cinematic orchestral"),
        broad_clusters=("Cinematic / Soundtrack",),
        sonic_traits=("cinematic", "orchestral", "textural", "dramatic"),
    ),
    "onerepublic": ArtistGenreProfile(
        canonical_genres=("pop rock", "alternative pop", "pop"),
        broad_clusters=("Pop / Pop Rock Crossover", "Alternative / Indie Rock"),
        sonic_traits=("anthemic", "polished", "melodic", "radio-ready"),
    ),
    "tate mcrae": ArtistGenreProfile(
        canonical_genres=("pop", "dance pop", "alt-pop"),
        broad_clusters=("Pop / Pop Rock Crossover",),
        sonic_traits=("sleek", "melodic", "danceable", "modern pop"),
    ),
    "beach house": ArtistGenreProfile(
        canonical_genres=("dream pop", "indie rock", "shoegaze"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("hazy", "atmospheric", "dreamy", "slow-burn"),
    ),
    "novo amor": ArtistGenreProfile(
        canonical_genres=("indie folk", "ambient folk", "indie pop"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("fragile", "atmospheric", "introspective", "acoustic"),
    ),
    "goo goo dolls": ArtistGenreProfile(
        canonical_genres=("alternative rock", "pop rock", "post-grunge"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "earnest", "guitar-driven", "nostalgic"),
    ),
    "the chainsmokers": ArtistGenreProfile(
        canonical_genres=("electropop", "dance pop", "electronic"),
        broad_clusters=("Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("polished", "danceable", "melodic", "festival-pop"),
    ),
    "the cranberries": ArtistGenreProfile(
        canonical_genres=("alternative rock", "dream pop", "post-punk"),
        broad_clusters=("Alternative / Indie Rock",),
        sonic_traits=("melancholic", "guitar-driven", "distinctive vocals", "nostalgic"),
    ),
    "sum 41": ArtistGenreProfile(
        canonical_genres=("pop punk", "punk rock", "alternative metal"),
        broad_clusters=("Emo / Pop Punk / Post-Hardcore", "Heavy Alternative / Metalcore"),
        sonic_traits=("high-energy", "bratty", "guitar-driven", "punchy"),
    ),
    "the weeknd": ArtistGenreProfile(
        canonical_genres=("r&b", "synth-pop", "pop"),
        broad_clusters=("Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("sleek", "nighttime", "melodic", "cinematic pop"),
    ),
    "keane": ArtistGenreProfile(
        canonical_genres=("piano rock", "alternative rock", "pop rock"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "sentimental", "piano-led", "british rock"),
    ),
    "avoure": ArtistGenreProfile(
        canonical_genres=("melodic house", "progressive house", "electronic"),
        broad_clusters=("Electronic / Atmospheric",),
        sonic_traits=("atmospheric", "melodic", "driving", "late-night"),
    ),
    "simple plan": ArtistGenreProfile(
        canonical_genres=("pop punk", "emo pop", "alternative rock"),
        broad_clusters=("Emo / Pop Punk / Post-Hardcore", "Alternative / Indie Rock"),
        sonic_traits=("nostalgic", "melodic", "teenage catharsis", "high-energy"),
    ),
    "noel gallagher's high flying birds": ArtistGenreProfile(
        canonical_genres=("britpop", "alternative rock", "rock"),
        broad_clusters=("Alternative / Indie Rock",),
        sonic_traits=("nostalgic", "melodic", "british rock", "anthemic"),
    ),
    "tame impala": ArtistGenreProfile(
        canonical_genres=("psychedelic pop", "indie rock", "synth-pop"),
        broad_clusters=("Alternative / Indie Rock", "Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("psychedelic", "glossy", "groove-led", "dreamy"),
    ),
    "lane 8": ArtistGenreProfile(
        canonical_genres=("melodic house", "deep house", "electronic"),
        broad_clusters=("Electronic / Atmospheric",),
        sonic_traits=("atmospheric", "melodic", "patient", "night-drive"),
    ),
    "alan walker": ArtistGenreProfile(
        canonical_genres=("electronic", "electropop", "progressive house"),
        broad_clusters=("Electronic / Atmospheric", "Pop / Pop Rock Crossover"),
        sonic_traits=("cinematic electronic", "melodic", "polished", "anthemic"),
    ),
    "david guetta": ArtistGenreProfile(
        canonical_genres=("dance pop", "edm", "house"),
        broad_clusters=("Electronic / Atmospheric", "Pop / Pop Rock Crossover"),
        sonic_traits=("festival-ready", "polished", "high-energy", "hook-driven"),
    ),
    "the script": ArtistGenreProfile(
        canonical_genres=("pop rock", "soft rock", "alternative pop"),
        broad_clusters=("Pop / Pop Rock Crossover", "Alternative / Indie Rock"),
        sonic_traits=("earnest", "melodic", "radio-friendly", "sentimental"),
    ),
    "imagine dragons": ArtistGenreProfile(
        canonical_genres=("pop rock", "alternative rock", "electronic rock"),
        broad_clusters=("Pop / Pop Rock Crossover", "Alternative / Indie Rock", "Heavy Alternative / Metalcore"),
        sonic_traits=("anthemic", "percussive", "polished", "arena-sized"),
    ),
    "blink-182": ArtistGenreProfile(
        canonical_genres=("pop punk", "punk rock", "alternative rock"),
        broad_clusters=("Emo / Pop Punk / Post-Hardcore", "Alternative / Indie Rock"),
        sonic_traits=("fast", "nostalgic", "melodic", "punk-pop"),
    ),
    "u2": ArtistGenreProfile(
        canonical_genres=("rock", "alternative rock", "post-punk"),
        broad_clusters=("Alternative / Indie Rock",),
        sonic_traits=("anthemic", "wide-screen", "earnest", "guitar-driven"),
    ),
    "taylor swift": ArtistGenreProfile(
        canonical_genres=("pop", "country pop", "singer-songwriter"),
        broad_clusters=("Pop / Pop Rock Crossover",),
        sonic_traits=("narrative", "melodic", "polished", "songwriting-led"),
    ),
    "robbie doherty": ArtistGenreProfile(
        canonical_genres=("deep house", "minimal house", "house"),
        broad_clusters=("Electronic / Atmospheric",),
        sonic_traits=("club-focused", "groove-led", "minimal"),
    ),
    "clovis reyes": ArtistGenreProfile(
        canonical_genres=("electronic", "dance pop", "edm"),
        broad_clusters=("Electronic / Atmospheric", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "danceable", "polished"),
    ),
    "fifa sound": ArtistGenreProfile(
        canonical_genres=("film score", "soundtrack", "cinematic orchestral"),
        broad_clusters=("Cinematic / Soundtrack",),
        sonic_traits=("cinematic", "anthemic", "orchestral"),
    ),
    "guns n' roses": ArtistGenreProfile(
        canonical_genres=("hard rock", "classic rock", "glam metal"),
        broad_clusters=("Rock / Classic Rock", "Heavy Alternative / Metalcore"),
        sonic_traits=("guitar-driven", "arena-sized", "dramatic"),
    ),
    "empire of the sun": ArtistGenreProfile(
        canonical_genres=("synth-pop", "indie pop", "electronic"),
        broad_clusters=("Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("glossy", "psychedelic", "danceable"),
    ),
    "don miguelo": ArtistGenreProfile(
        canonical_genres=("dembow", "reggaeton", "latin urban"),
        broad_clusters=("Latin / Reggaeton",),
        sonic_traits=("rhythmic", "club-focused", "high-energy"),
    ),
    "skai isyourgod": ArtistGenreProfile(
        canonical_genres=("chinese hip-hop", "hip-hop", "memphis rap", "trap"),
        broad_clusters=("Hip-Hop / Rap",),
        sonic_traits=("bass-heavy", "rhythmic", "dark"),
    ),
    "nickthereal": ArtistGenreProfile(
        canonical_genres=("mandopop", "dance pop", "edm"),
        broad_clusters=("Mandopop / C-pop", "Electronic / Atmospheric"),
        sonic_traits=("danceable", "polished", "high-energy"),
    ),
    "gareth.t": ArtistGenreProfile(
        canonical_genres=("cantopop", "r&b", "pop"),
        broad_clusters=("Cantopop", "R&B / Soul / Funk"),
        sonic_traits=("melodic", "intimate", "smooth"),
    ),
    "mayday": ArtistGenreProfile(
        canonical_genres=("mandopop", "pop rock", "rock"),
        broad_clusters=("Mandopop / C-pop", "Rock / Classic Rock"),
        sonic_traits=("anthemic", "melodic", "guitar-driven"),
    ),
    "eric chou": ArtistGenreProfile(
        canonical_genres=("mandopop", "pop", "r&b"),
        broad_clusters=("Mandopop / C-pop", "R&B / Soul / Funk"),
        sonic_traits=("romantic", "melodic", "vocal-led"),
    ),
    "wanting": ArtistGenreProfile(
        canonical_genres=("mandopop", "pop", "singer-songwriter"),
        broad_clusters=("Mandopop / C-pop",),
        sonic_traits=("melodic", "piano-led", "introspective"),
    ),
    "firdhaus": ArtistGenreProfile(
        canonical_genres=("mandopop", "pop"),
        broad_clusters=("Mandopop / C-pop",),
        sonic_traits=("melodic", "romantic", "vocal-led"),
    ),
    "lane 8 & massane": ArtistGenreProfile(
        canonical_genres=("melodic house", "progressive house", "electronic"),
        broad_clusters=("Electronic / Atmospheric",),
        sonic_traits=("atmospheric", "melodic", "patient"),
    ),
    "lane 8 & yotto": ArtistGenreProfile(
        canonical_genres=("melodic house", "progressive house", "electronic"),
        broad_clusters=("Electronic / Atmospheric",),
        sonic_traits=("atmospheric", "melodic", "driving"),
    ),
    "vegedream": ArtistGenreProfile(
        canonical_genres=("french hip-hop", "hip-hop", "afro-trap"),
        broad_clusters=("Hip-Hop / Rap",),
        sonic_traits=("rhythmic", "anthemic", "celebratory"),
    ),
    "mc l da vinte": ArtistGenreProfile(
        canonical_genres=("baile funk", "funk carioca", "latin urban"),
        broad_clusters=("Latin / Reggaeton",),
        sonic_traits=("percussive", "club-focused", "high-energy"),
    ),
    "aaron hibell": ArtistGenreProfile(
        canonical_genres=("electronica", "trance", "ambient"),
        broad_clusters=("Electronic / Atmospheric",),
        sonic_traits=("cinematic", "atmospheric", "building"),
    ),
    "gala": ArtistGenreProfile(
        canonical_genres=("eurodance", "dance pop", "house"),
        broad_clusters=("Electronic / Atmospheric", "Pop / Pop Rock Crossover"),
        sonic_traits=("danceable", "anthemic", "high-energy"),
    ),
    "the beatles": ArtistGenreProfile(
        canonical_genres=("pop rock", "classic rock", "psychedelic rock"),
        broad_clusters=("Rock / Classic Rock", "Pop / Pop Rock Crossover"),
        sonic_traits=("melodic", "songwriting-led", "classic"),
    ),
    "mr.kitty": ArtistGenreProfile(
        canonical_genres=("synthwave", "darkwave", "synth-pop"),
        broad_clusters=("Electronic / Atmospheric", "Alternative / Indie Rock"),
        sonic_traits=("dark", "atmospheric", "synth-led"),
    ),
    "pastel ghost": ArtistGenreProfile(
        canonical_genres=("synth-pop", "darkwave", "electronic"),
        broad_clusters=("Electronic / Atmospheric", "Alternative / Indie Rock"),
        sonic_traits=("ethereal", "dark", "synth-led"),
    ),
    "g.e.m.": ArtistGenreProfile(
        canonical_genres=("mandopop", "c-pop", "pop", "r&b"),
        broad_clusters=("Pop / Pop Rock Crossover",),
        sonic_traits=("melodic", "vocal-led", "polished"),
    ),
    "nicholas britell": ArtistGenreProfile(
        canonical_genres=("film score", "orchestral soundtrack"),
        broad_clusters=("Cinematic / Soundtrack",),
        sonic_traits=("cinematic", "orchestral", "dramatic"),
    ),
    "hiroyuki sawano": ArtistGenreProfile(
        canonical_genres=("soundtrack", "cinematic orchestral", "electronic rock"),
        broad_clusters=("Cinematic / Soundtrack", "Electronic / Atmospheric", "Heavy Alternative / Metalcore"),
        sonic_traits=("cinematic", "dramatic", "high-energy"),
    ),
    "michael jackson": ArtistGenreProfile(
        canonical_genres=("pop", "dance", "funk"),
        broad_clusters=("Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
        sonic_traits=("rhythmic", "melodic", "polished"),
    ),
    "邓紫棋": ArtistGenreProfile(canonical_genres=("mandopop", "c-pop", "pop", "r&b"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "周杰伦": ArtistGenreProfile(canonical_genres=("mandopop", "c-pop", "pop", "r&b"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "周杰倫": ArtistGenreProfile(canonical_genres=("mandopop", "c-pop", "pop", "r&b"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "告五人": ArtistGenreProfile(canonical_genres=("mandopop", "pop rock", "indie pop"), broad_clusters=("Pop / Pop Rock Crossover", "Alternative / Indie Rock")),
    "王力宏": ArtistGenreProfile(canonical_genres=("mandopop", "r&b", "pop"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "林俊杰": ArtistGenreProfile(canonical_genres=("mandopop", "pop", "r&b"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "林俊傑": ArtistGenreProfile(canonical_genres=("mandopop", "pop", "r&b"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "陈奕迅": ArtistGenreProfile(canonical_genres=("cantopop", "mandopop", "pop"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "陳奕迅": ArtistGenreProfile(canonical_genres=("cantopop", "mandopop", "pop"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "五月天": ArtistGenreProfile(canonical_genres=("mandopop", "pop rock"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "bts": ArtistGenreProfile(canonical_genres=("k-pop", "pop", "hip-hop"), broad_clusters=("Pop / Pop Rock Crossover", "Hip-Hop / Rap")),
    "blackpink": ArtistGenreProfile(canonical_genres=("k-pop", "pop", "dance pop"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "twice": ArtistGenreProfile(canonical_genres=("k-pop", "pop", "dance pop"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "newjeans": ArtistGenreProfile(canonical_genres=("k-pop", "r&b", "pop"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "yoasobi": ArtistGenreProfile(canonical_genres=("j-pop", "pop rock"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "ado": ArtistGenreProfile(canonical_genres=("j-pop", "pop rock"), broad_clusters=("Pop / Pop Rock Crossover",)),
    "kenshi yonezu": ArtistGenreProfile(canonical_genres=("j-pop", "pop rock"), broad_clusters=("Pop / Pop Rock Crossover",)),
}


ARTIST_ALIASES: dict[str, str] = {
    "30 seconds to mars": "thirty seconds to mars",
    "blink 182": "blink-182",
    "bmth": "bring me the horizon",
    "mcr": "my chemical romance",
    "one republic": "onerepublic",
    "sawano hiroyuki": "hiroyuki sawano",
    "gem tang": "g.e.m.",
    "周湯豪": "nickthereal",
    "周湯豪 nickthereal": "nickthereal",
    "揽佬skai isyourgod": "skai isyourgod",
    "攬佬skai isyourgod": "skai isyourgod",
    "五月天": "mayday",
    "五月天 (mayday)": "mayday",
    "周興哲": "eric chou",
    "曲婉婷": "wanting",
    "菲道尔": "firdhaus",
    "菲道尔 firdhaus": "firdhaus",
    "邓紫棋": "g.e.m.",
    "周杰倫": "jay chou",
    "周杰伦": "jay chou",
    "林俊傑": "林俊杰",
    "陳奕迅": "陈奕迅",
    "周杰伦": "周杰倫",
}


@lru_cache(maxsize=16_384)
def _normalise_punctuation_and_spacing(name: str) -> str:
    value = unicodedata.normalize("NFKC", str(name or "")).casefold()
    value = value.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-").replace("−", "-")
    return " ".join(value.strip().split())


@lru_cache(maxsize=16_384)
def normalise_artist_name(name: str) -> str:
    value = _normalise_punctuation_and_spacing(name)
    value = re.sub(r"\s*-\s*topic$", "", value)
    value = re.sub(r"(?:\s+|[\[(]\s*)(?:feat\.?|ft\.?|featuring)\s+.+?(?:[\])])?$", "", value)
    return " ".join(value.strip().split())


def canonical_artist_key(name: str) -> str:
    """Return a stable artist identity while keeping alias matching conservative."""

    key = normalise_artist_name(name)
    original = key
    seen: set[str] = set()
    while key and key not in seen:
        seen.add(key)
        target = ARTIST_ALIASES.get(key)
        if not target:
            break
        key = normalise_artist_name(target)
    if key != original or key in ARTIST_GENRES:
        return key

    # Exports commonly carry a bilingual display name such as
    # "周杰倫 Jay Chou". Merge it only when one side is a known exact artist
    # identity and the other side contains non-ASCII script; ordinary
    # collaborations and similarly named Latin artists remain untouched.
    if any(ord(character) > 127 for character in original):
        for candidate in sorted({*ARTIST_GENRES, *ARTIST_ALIASES}, key=len, reverse=True):
            if original == candidate or not (original.startswith(f"{candidate} ") or original.endswith(f" {candidate}")):
                continue
            resolved = candidate
            alias_seen: set[str] = set()
            while resolved not in alias_seen and ARTIST_ALIASES.get(resolved):
                alias_seen.add(resolved)
                resolved = normalise_artist_name(ARTIST_ALIASES[resolved])
            if resolved in ARTIST_GENRES:
                return resolved
    return key


def get_exact_curated_artist_profile(name: str) -> ArtistGenreProfile | None:
    return ARTIST_GENRES.get(_normalise_punctuation_and_spacing(name))


def get_curated_artist_profile(name: str) -> ArtistGenreProfile | None:
    return ARTIST_GENRES.get(canonical_artist_key(name))


def clusters_for_genres(genres: list[str] | tuple[str, ...]) -> list[str]:
    clusters: list[str] = []
    lower_genres = {" ".join(unicodedata.normalize("NFKC", str(genre)).casefold().split()) for genre in genres if genre}
    regional_genres = {
        "malay pop", "malaysian pop", "indo pop", "indonesian pop", "nusantara pop",
        "malay rock", "malaysian rock", "indo rock", "indonesian rock", "nusantara rock", "malay indie", "indonesian indie",
        "dangdut", "koplo", "mandopop", "mandarin pop", "c-pop", "chinese pop",
        "cantopop", "cantonese pop", "hong kong pop", "k-pop", "k pop", "korean pop",
        "j-pop", "j pop", "j-rock", "j rock", "japanese pop", "japanese rock",
        "tamil", "kollywood", "indian film", "filmi", "bollywood", "desi pop", "indian pop",
    }
    # Providers commonly add generic Pop/Dance Pop beside a regional label.
    # Preserve the more informative regional identity in report clusters.
    if lower_genres & regional_genres:
        lower_genres -= {"pop", "dance pop", "dance-pop", "pop rock", "pop-rock"}
    for cluster, cluster_genres in BROAD_CLUSTER_GENRES.items():
        if lower_genres & {genre.casefold() for genre in cluster_genres}:
            clusters.append(cluster)
    for genre in genres:
        for internal_name, internal_clusters in INTERNAL_BROAD_CLUSTERS.items():
            if " ".join(unicodedata.normalize("NFKC", str(genre)).casefold().split()) != internal_name.casefold():
                continue
            for cluster in internal_clusters:
                if cluster not in clusters:
                    clusters.append(cluster)
    return clusters


# Keep the granular names users recognise in the UI.  Broad clusters are still
# useful for taste-model scoring, but are deliberately not used as the Insights
# chart labels.
GENRE_ALIASES: dict[str, tuple[str, str]] = {
    "k pop": ("k-pop", "K-pop"), "k-pop": ("k-pop", "K-pop"), "korean pop": ("k-pop", "K-pop"),
    "mandopop": ("mandopop", "Mandopop"), "mandarin pop": ("mandopop", "Mandopop"),
    "cantopop": ("cantopop", "Cantopop"), "cantonese pop": ("cantopop", "Cantopop"),
    "c pop": ("c-pop", "C-pop"), "c-pop": ("c-pop", "C-pop"), "chinese pop": ("c-pop", "C-pop"),
    "j pop": ("j-pop", "J-pop"), "j-pop": ("j-pop", "J-pop"), "japanese pop": ("j-pop", "J-pop"),
    "rnb": ("r-b", "R&B"), "r&b": ("r-b", "R&B"), "rhythm and blues": ("r-b", "R&B"),
    "alt rock": ("alternative-rock", "Alternative rock"), "alternative rock": ("alternative-rock", "Alternative rock"),
    "indie rock": ("indie-rock", "Indie rock"), "pop punk": ("pop-punk", "Pop punk"),
    "hip hop": ("hip-hop", "Hip-hop"), "hip-hop": ("hip-hop", "Hip-hop"),
    "film score": ("film-score", "Film score"), "soundtrack": ("soundtrack", "Soundtrack"),
}


def normalise_genre(genre: str) -> tuple[str, str] | None:
    """Return a stable key and a meaningful display label for genre metadata."""
    value = " ".join(unicodedata.normalize("NFKC", str(genre or "")).casefold().replace("/", " ").split())
    if not value:
        return None
    internal_labels = {
        " ".join(label.casefold().replace("/", " ").split()): label
        for label in INTERNAL_GENRES
    }
    if value in internal_labels:
        label = internal_labels[value]
        return re.sub(r"[^a-z0-9]+", "-", value).strip("-"), label
    if value in GENRE_ALIASES:
        return GENRE_ALIASES[value]
    key = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not key or key in {"music", "other", "unknown", "various", "spoken-word", "comedy", "podcast", "audiobook", "talk", "made-up-genre"}:
        return None
    return key, " ".join(part.capitalize() for part in value.split())

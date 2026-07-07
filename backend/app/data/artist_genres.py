from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtistGenreProfile:
    canonical_genres: tuple[str, ...]
    broad_clusters: tuple[str, ...]
    sonic_traits: tuple[str, ...]
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
    },
    "Emo / Pop Punk / Post-Hardcore": {
        "emo",
        "pop punk",
        "post-hardcore",
        "screamo",
        "emo pop",
        "alternative punk",
        "punk rock",
    },
    "Heavy Alternative / Metalcore": {
        "metalcore",
        "alternative metal",
        "nu metal",
        "hard rock",
        "electronic rock",
        "post-metal",
        "heavy alternative",
    },
    "Pop / Pop Rock Crossover": {
        "pop rock",
        "alternative pop",
        "synth-pop",
        "electropop",
        "indie pop",
        "pop",
        "pop rap",
    },
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
    },
    "Hip-Hop / Rap": {
        "hip-hop",
        "rap",
        "trap",
        "alternative hip-hop",
        "pop rap",
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
}


def normalise_artist_name(name: str) -> str:
    return " ".join(name.strip().casefold().split())


def get_curated_artist_profile(name: str) -> ArtistGenreProfile | None:
    return ARTIST_GENRES.get(normalise_artist_name(name))


def clusters_for_genres(genres: list[str] | tuple[str, ...]) -> list[str]:
    clusters: list[str] = []
    lower_genres = {genre.casefold() for genre in genres}
    for cluster, cluster_genres in BROAD_CLUSTER_GENRES.items():
        if lower_genres & {genre.casefold() for genre in cluster_genres}:
            clusters.append(cluster)
    return clusters

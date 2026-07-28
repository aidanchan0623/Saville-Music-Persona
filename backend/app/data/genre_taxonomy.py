from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


TAXONOMY_VERSION = 1

# Stable product-facing buckets. External provider labels remain available as
# evidence; these names are deliberately broad enough to work across users.
INTERNAL_GENRES: tuple[str, ...] = (
    "Mainstream Pop",
    "Dance Pop / Europop",
    "Alternative / Indie Pop",
    "Pop Rock",
    "Alternative / Indie Rock",
    "Classic Rock / Hard Rock",
    "Punk / Pop Punk",
    "Emo / Post-Hardcore",
    "Metal / Metalcore",
    "Shoegaze / Dream Pop",
    "Post-Punk / Goth / Darkwave",
    "Hip-Hop / Rap",
    "R&B / Soul",
    "House",
    "Techno / Trance",
    "EDM / Bass Music",
    "Ambient / Experimental Electronic",
    "Latin Urban",
    "Afrobeat / Amapiano / Dancehall",
    "Country / Folk",
    "Jazz / Blues / Funk",
    "Classical / Cinematic / Soundtrack",
    "Malay / Nusantara Pop",
    "Malay / Nusantara Rock & Indie",
    "Dangdut",
    "Mandopop",
    "Cantopop",
    "K-pop",
    "J-Pop / J-Rock",
    "Tamil / Indian Film & Pop",
)

INTERNAL_BROAD_CLUSTERS: dict[str, tuple[str, ...]] = {
    "Mainstream Pop": ("Pop / Pop Rock Crossover",),
    "Dance Pop / Europop": ("Pop / Pop Rock Crossover", "Electronic / Atmospheric"),
    "Alternative / Indie Pop": ("Pop / Pop Rock Crossover", "Alternative / Indie Rock"),
    "Pop Rock": ("Pop / Pop Rock Crossover", "Rock / Classic Rock"),
    "Alternative / Indie Rock": ("Alternative / Indie Rock",),
    "Classic Rock / Hard Rock": ("Rock / Classic Rock", "Heavy Alternative / Metalcore"),
    "Punk / Pop Punk": ("Emo / Pop Punk / Post-Hardcore", "Alternative / Indie Rock"),
    "Emo / Post-Hardcore": ("Emo / Pop Punk / Post-Hardcore",),
    "Metal / Metalcore": ("Heavy Alternative / Metalcore",),
    "Shoegaze / Dream Pop": ("Alternative / Indie Rock", "Pop / Pop Rock Crossover"),
    "Post-Punk / Goth / Darkwave": ("Alternative / Indie Rock", "Electronic / Atmospheric"),
    "Hip-Hop / Rap": ("Hip-Hop / Rap",),
    "R&B / Soul": ("R&B / Soul / Funk",),
    "House": ("Electronic / Atmospheric",),
    "Techno / Trance": ("Electronic / Atmospheric",),
    "EDM / Bass Music": ("Electronic / Atmospheric",),
    "Ambient / Experimental Electronic": ("Electronic / Atmospheric",),
    "Latin Urban": ("Latin / Reggaeton",),
    "Afrobeat / Amapiano / Dancehall": ("Reggae / Dancehall", "Electronic / Atmospheric"),
    "Country / Folk": ("Folk / Country / Acoustic",),
    "Jazz / Blues / Funk": ("Jazz / Classical", "R&B / Soul / Funk"),
    "Classical / Cinematic / Soundtrack": ("Cinematic / Soundtrack", "Jazz / Classical"),
    "Malay / Nusantara Pop": ("Pop / Pop Rock Crossover",),
    "Malay / Nusantara Rock & Indie": ("Alternative / Indie Rock",),
    "Dangdut": ("Pop / Pop Rock Crossover",),
    "Mandopop": ("Pop / Pop Rock Crossover",),
    "Cantopop": ("Pop / Pop Rock Crossover",),
    "K-pop": ("Pop / Pop Rock Crossover",),
    "J-Pop / J-Rock": ("Pop / Pop Rock Crossover", "Alternative / Indie Rock"),
    "Tamil / Indian Film & Pop": ("Pop / Pop Rock Crossover", "Cinematic / Soundtrack"),
}


@dataclass(frozen=True)
class TaxonomyMatch:
    primary_genre: str
    secondary_genres: tuple[str, ...]
    normalisation_confidence: float
    matched_labels: tuple[str, ...]


RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Malay / Nusantara Rock & Indie", ("malay rock", "malaysian rock", "indo rock", "indonesian rock", "nusantara rock", "malay indie", "indonesian indie")),
    ("Malay / Nusantara Pop", ("malay pop", "malaysian pop", "indo pop", "indonesian pop", "nusantara pop")),
    ("Tamil / Indian Film & Pop", ("tamil", "kollywood", "indian film", "filmi", "bollywood", "desi pop", "indian pop")),
    ("Mandopop", ("mandopop", "mandarin pop", "chinese pop", "c-pop")),
    ("Cantopop", ("cantopop", "cantonese pop", "hong kong pop")),
    ("K-Pop", ("k-pop", "k pop", "korean pop")),
    ("J-Pop / J-Rock", ("j-pop", "j pop", "j-rock", "j rock", "japanese pop", "japanese rock", "anime song")),
    ("Dangdut", ("dangdut", "koplo")),
    ("Emo / Post-Hardcore", ("post-hardcore", "post hardcore", "screamo", "emo")),
    ("Punk / Pop Punk", ("pop punk", "punk rock", "hardcore punk", "punk")),
    ("Metal / Metalcore", ("metalcore", "deathcore", "nu metal", "heavy metal", "death metal", "black metal", "progressive metal", "alternative metal", "metal")),
    ("Shoegaze / Dream Pop", ("shoegaze", "dream pop", "ethereal wave")),
    ("Post-Punk / Goth / Darkwave", ("post-punk", "post punk", "darkwave", "gothic rock", "goth", "new wave")),
    ("Alternative / Indie Rock", ("alternative rock", "indie rock", "britpop", "garage rock", "post-grunge", "art rock", "psychedelic rock")),
    ("Classic Rock / Hard Rock", ("classic rock", "hard rock", "arena rock", "glam rock", "blues rock", "progressive rock", "rock")),
    ("Pop Rock", ("pop rock", "soft rock")),
    ("Alternative / Indie Pop", ("alternative pop", "indie pop", "art pop", "bedroom pop", "hyperpop")),
    ("Dance Pop / Europop", ("dance-pop", "dance pop", "europop", "eurodance", "italo dance")),
    ("Mainstream Pop", ("synth-pop", "synthpop", "electropop", "teen pop", "pop")),
    ("Hip-Hop / Rap", ("hip-hop", "hip hop", "rap", "trap", "drill", "grime", "memphis rap")),
    ("R&B / Soul", ("alternative r&b", "contemporary r&b", "r&b", "rnb", "rhythm and blues", "neo-soul", "soul")),
    ("House", ("melodic house", "deep house", "progressive house", "tech house", "afro house", "house")),
    ("Techno / Trance", ("melodic techno", "techno", "trance", "psytrance")),
    ("EDM / Bass Music", ("drum and bass", "dubstep", "future bass", "electro house", "edm", "electronic dance music")),
    ("Ambient / Experimental Electronic", ("ambient", "electronica", "downtempo", "experimental electronic", "synthwave", "vaporwave", "IDM")),
    ("Latin Urban", ("reggaeton", "latin trap", "urbano latino", "dembow", "latin urban", "baile funk", "funk carioca")),
    ("Afrobeat / Amapiano / Dancehall", ("afrobeats", "afrobeat", "amapiano", "dancehall", "reggae", "afro-trap")),
    ("Country / Folk", ("country", "americana", "folk", "singer-songwriter", "bluegrass")),
    ("Jazz / Blues / Funk", ("jazz", "blues", "funk", "bebop", "fusion")),
    ("Classical / Cinematic / Soundtrack", ("film score", "soundtrack", "cinematic", "orchestral", "classical", "new age", "video game music")),
)


def _clean(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"[_/]+", " ", value)
    return " ".join(value.split())


def normalise_external_genres(labels: Iterable[str]) -> TaxonomyMatch | None:
    cleaned = tuple(dict.fromkeys(_clean(label) for label in labels if _clean(label)))
    scores: dict[str, float] = {}
    matched: list[str] = []
    for label in cleaned:
        candidates: list[tuple[bool, int, int, str]] = []
        for rule_index, (genre, aliases) in enumerate(RULES):
            for alias in aliases:
                exact = label == alias
                if exact or re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", label):
                    candidates.append((exact, -rule_index, len(alias), genre))
        if not candidates:
            continue
        exact, _, _, genre = max(candidates, key=lambda item: (item[0], item[1], item[2]))
        score = 0.98 if exact else 0.84
        scores[genre] = max(scores.get(genre, 0.0), score)
        matched.append(label)
    if not scores:
        return None
    ordered = sorted(scores, key=lambda genre: (-scores[genre], INTERNAL_GENRES.index(genre)))
    primary = ordered[0]
    return TaxonomyMatch(
        primary_genre=primary,
        secondary_genres=tuple(ordered[1:4]),
        normalisation_confidence=scores[primary],
        matched_labels=tuple(dict.fromkeys(matched)),
    )

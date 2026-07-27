from app.analysis.music_character import CHARACTER_DEFINITIONS, score_personalities, select_habits


def signals(*terms: str, **values: float) -> dict:
    return {"canonical": list(terms), "traits": [], "clusters": [], "repeat": 0, "artist_loyalty": 0, "single_dominance": 0, "album_depth": 0, "mainstream_niche": 50, "late_night_share": 0, "top_artist_share": 0, "top_track_share": 0, "discovery": 50, "broad_cluster_diversity": 0, "top_cluster_share": 100, **values}


def test_catalogue_has_exactly_twelve_primary_personalities() -> None:
    assert len(CHARACTER_DEFINITIONS) == 12
    assert {item["name"] for item in CHARACTER_DEFINITIONS} >= {"The Main Character in a Rain Scene", "The Jazz-Bar Overthinker"}


def test_each_personality_has_a_representative_winner() -> None:
    examples = {
        "divorced_dad_rock_station": ("classic rock", "arena rock", "guitar-driven"), "never_a_phase": ("emo", "pop-punk", "screamo"),
        "classical_supremacist": ("classical", "orchestral", "opera"), "girly_pop_commander": ("dance-pop", "synth-pop", "electropop"),
        "club_closing_time_resident": ("house", "techno", "trance"), "main_character_rain_scene": ("shoegaze", "dream pop", "atmospheric"),
        "heavy_music_therapist": ("metalcore", "alternative metal", "heavy"), "late_night_rnb_philosopher": ("r&b", "neo-soul", "smooth"),
        "aux_cord_menace": ("rap", "trap", "drill"), "campfire_lore_keeper": ("folk", "country", "acoustic"), "jazz_bar_overthinker": ("jazz", "bebop", "swing"),
    }
    for expected, terms in examples.items():
        assert score_personalities(signals(*terms))[0]["id"] == expected
    assert score_personalities(signals(single_dominance=90, album_depth=5, mainstream_niche=20))[0]["id"] == "tiktok_slop_connoisseur"


def test_documented_genre_boundaries() -> None:
    assert score_personalities(signals("shoegaze", "dream pop", "atmospheric"))[0]["id"] == "main_character_rain_scene"
    assert score_personalities(signals("jazz", "bebop"))[0]["id"] != "classical_supremacist"
    assert score_personalities(signals("classical", "orchestral"))[0]["id"] != "jazz_bar_overthinker"
    assert score_personalities(signals("folk", "country", "acoustic"))[0]["id"] != "divorced_dad_rock_station"


def test_habits_rank_and_cap_at_three() -> None:
    result = select_habits(signals(top_artist_share=25, artist_loyalty=75, album_depth=80, repeat=78, discovery=30, broad_cluster_diversity=80, top_cluster_share=35))
    assert result[0] == "Artist-Focused"
    assert {"Album Loyalist", "Genre Explorer"}.issubset(result)
    assert len(result) <= 3

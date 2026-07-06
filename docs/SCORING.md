# Scoring rules

All Saville Music Persona scores are calculated locally in the FastAPI backend. The Ollama model may explain results, but it never decides counts, rankings, or numeric scores.

## Analysis coverage

History items are filtered to the latest 365 days when parseable play dates are available. If no dates can be parsed, the app labels the result as available-history analysis and does not claim a full year.

Full 365-day analysis is marked **Yes** only when dated history covers at least 350 represented days and at least 80% of returned history items have parseable dates.

## Repeat score

```text
repeat_score = 100 * (1 - unique_tracks / total_track_plays)
```

Bands:

- 0-25: explorer
- 26-50: balanced
- 51-75: comfort listener
- 76-100: emotional loop specialist

## Artist loyalty

```text
artist_loyalty = top_5_artist_plays / total_track_plays * 100
```

The app also shows top artist share, top 5 artist share, and unique artists listened.

## Discovery score

When enough dated history exists:

1. Find the latest detected play date.
2. Treat the last 30 dated days as the recent segment.
3. Treat earlier dated plays as the baseline segment.
4. Count recent plays from tracks and artists that did not appear in the baseline.

```text
discovery_score = (new_recent_track_share * 0.6 + new_recent_artist_share * 0.4) * 100
```

If the dataset is too short, the score is labelled as insufficient dated history.

## Nostalgia score

Only tracks with real release-year metadata are used.

```text
track_age_score = min((current_year - release_year) / 30 * 100, 100)
nostalgia_score = average(track_age_score), weighted by detected plays
```

The app also shows favourite release decade, decade percentages, oldest frequently played song, and newest frequently played song where metadata supports it.

## Mainstream-Niche Estimate

This is a cautious proxy, not an objective judgement. It uses available artist subscriber counts from YouTube Music metadata.

Subscriber buckets:

- 10M or more: 10
- 1M to 9.99M: 30
- 100K to 999K: 55
- 10K to 99K: 75
- under 10K: 90

```text
mainstream_niche_score = play-weighted average artist subscriber bucket
```

Higher means more niche-leaning. The confidence note is lowered when subscriber metadata is sparse.

## Genre diversity

Genre clusters are gathered from explicit metadata where present and inferred from playlist, artist, album, and track text when needed. Sparse results are labelled as inferred clusters.

```text
genre_diversity = normalised Shannon entropy of play-weighted genre cluster counts
```

If fewer than two usable clusters exist, diversity is 0 with low confidence.

## Mood profile

Mood tags are heuristic and evidence-based. The app uses playlist names, song titles, album titles, genre clusters, and repeat behaviour. It does not claim YouTube Music provides factual mood labels for every song.

Supported tags include:

- introspective
- high-energy
- romantic
- nostalgic
- late-night
- comfort-listening
- indie-leaning
- melancholic
- party-oriented

Every mood tag includes a short evidence note.

## Taste confidence

```text
taste_confidence =
  date_coverage_component
  + play_volume_component
  + unique_artist_component
  + release_year_metadata_component
  + genre_data_component
  + date_availability_component
```

Weights:

- Date coverage: 20
- Track play volume: 20
- Unique artists: 15
- Release-year metadata: 15
- Genre data availability: 15
- Date availability: 15

Uncertainty is shown directly in the dashboard instead of being hidden.


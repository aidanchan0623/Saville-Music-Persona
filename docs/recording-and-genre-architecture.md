# Recording identity and sustainable genre enrichment

Saville keeps listening occurrences and recordings as separate concepts. A listening event is one historical play. Three timestamps for the same song are three events. Event deduplication removes only overlapping-import copies using the established hierarchy: source event ID, provider track/video ID plus timestamp, then title and artist plus timestamp. The recording catalog never changes those totals.

Each reusable recording can have several strong identifiers (YouTube video ID, Spotify track ID, ISRC, MusicBrainz recording ID, or another provider ID), aliases, and many linked listening events. Exact identifiers are trusted first. A normalized title and primary artist are only medium evidence when album or duration also agrees and version modifiers match. Title and artist alone are weak search evidence and are not persisted as a canonical identity. Live, remix, remaster, slowed, sped-up, instrumental, acoustic, cover, and radio-edit markers therefore remain separate; presentation-only variants such as official audio, lyric video, and music video can resolve together when duration or album corroborates them.

Genre enrichment uses a strict hierarchy:

1. Use Saville's existing curated or trusted provider genres immediately.
2. Check the local recording catalog for an already approved assignment.
3. Only for still-unclassified high-impact tracks, query MusicBrainz at recording level.
4. Preserve the provider's raw labels as evidence and map them into Saville's stable 30-genre taxonomy.
5. Automatically apply a result only when recording identity, evidence quality, and taxonomy-normalisation confidence clear the safety threshold.

The three confidence values remain separate and inspectable. Their product is an application gate, not a replacement for the components. A result can therefore be retained for review without affecting analytics. Provider failures are cached with retry metadata so repeated Takeout imports do not keep issuing the same failed lookup.

The catalog is stored in the existing local SQLite database in `recordings`, `recording_identifiers`, `recording_aliases`, `listening_events`, `genre_evidence`, `genre_assignments`, and `lookup_failures`. New Takeout files reuse strong identifiers and approved assignments. Growth is proportional to unique recordings and evidence, not play count; listening-event rows are a replaceable index of the current local profile. `GET /api/data/genre-catalog` exposes safe aggregate diagnostics, while `GET /api/data/genre-catalog/{recording_id}` exposes the separate confidence and evidence fields for one recording without returning its listening history.

Gemma may describe or roast the completed deterministic analysis, but it is not a genre authority and cannot write automatic assignments.

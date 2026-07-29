# Recording identity and sustainable genre enrichment

Saville keeps listening occurrences and recordings as separate concepts. A listening event is one historical play. Three timestamps for the same song are three events. Event deduplication removes only overlapping-import copies using the established hierarchy: source event ID, provider track/video ID plus timestamp, then title and artist plus timestamp. The recording catalog never changes those totals.

Each reusable recording can have several strong identifiers (YouTube video ID, Spotify track ID, ISRC, MusicBrainz recording ID, or another provider ID), aliases, and many linked listening events. Exact identifiers are trusted first. A normalized title and primary artist are only medium evidence when album or duration also agrees and version modifiers match. Title and artist alone are weak search evidence and are not persisted as a canonical identity. Live, remix, remaster, slowed, sped-up, instrumental, acoustic, cover, and radio-edit markers therefore remain separate; presentation-only variants such as official audio, lyric video, and music video can resolve together when duration or album corroborates them.

Genre enrichment uses a strict hierarchy:

1. Use Saville's existing curated or trusted provider genres immediately.
2. Reuse durable exact-artist and recording assignments from the local caches.
3. Resolve still-unclassified artists through a bounded exact MusicBrainz artist lookup; this has the highest coverage per request.
4. Use recording-level MusicBrainz identity only for high-impact tracks whose artist still has no trusted genres.
5. Preserve the provider's raw labels as evidence and map them into Saville's stable 30-genre taxonomy.
6. Automatically apply a result only when recording identity, evidence quality, and taxonomy-normalisation confidence clear the safety threshold.

For analytics, one listening event maps to one primary internal genre and contributes exactly one count. Secondary genres remain attached to the recording or artist as evidence, but they do not divide a play into fractional chart weights. Near-synonyms such as C-pop, Chinese pop, Mandarin pop, and Mandopop resolve to the single Mandopop bucket. This keeps chart counts integer-valued and ensures repeated listening has proportional influence.

The three confidence values remain separate and inspectable. Their product is an application gate, not a replacement for the components. A result can therefore be retained for review without affecting analytics. Provider failures are cached with retry metadata and loaded once per batch, so repeated Takeout imports do not keep issuing the same failed lookup. Provider tag vote order is retained when several internal genres have equal mapping confidence.

The catalog is stored in the existing local SQLite database in `recordings`, `recording_identifiers`, `recording_aliases`, `listening_events`, `genre_evidence`, `genre_assignments`, and `lookup_failures`. New Takeout files reuse strong identifiers and approved assignments. Growth is proportional to unique recordings and evidence, not play count; listening-event rows are a replaceable index of the current local profile. `GET /api/data/genre-catalog` exposes safe aggregate diagnostics, while `GET /api/data/genre-catalog/{recording_id}` exposes the separate confidence and evidence fields for one recording without returning its listening history.

Gemma may describe or roast the completed deterministic analysis, but it is not a genre authority and cannot write automatic assignments.

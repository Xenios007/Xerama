# Module 12 — Editor, Subtitles & Final Export

## Mission
Turn accepted production assets into a deterministic finished vertical episode.

## Build
Create timeline/edit models describing ordered clips, trims, transitions, dialogue/audio, ambience/music/SFX, subtitles and output settings. Implement FFmpeg/ffprobe adapter/service; do not make generative AI responsible for deterministic assembly.

Initial export target: 1080x1920 vertical MP4 with validated duration/aspect, mixed audio and subtitles. Add loudness normalization and safe subtitle layout where practical. Preserve render command/spec and resulting asset lineage for reproducibility.

Implement render job integration with Module 10 and final media-health QC with Module 11.

## Tests
Use tiny generated fixture media to test concatenation, trim, subtitle timing, audio mix, ffprobe validation, deterministic timeline serialization and failed render handling. Skip gracefully only if FFmpeg is unavailable in test environment.

## Acceptance
Xerama can render a complete Trial-01 episode from accepted shot/audio assets into a durable final MP4 and validate it.

## Agent instructions
Update APIs/tests/docs/changelog, run suite, commit, proceed to Module 13.
# MODULE-048 — Vertical Export

**Status:** BUILD
**Depends on:** 039,046

## Objective
Produce platform-ready vertical microdrama files with validated technical properties.

## Requirements
- Default 9:16, target 1080x1920 when source quality allows.
- Configurable codec/bitrate/FPS/audio settings.
- ffprobe validation for duration, aspect, streams and corruption.
- Subtitle/UI safe-area validation where measurable.

## Verification
Export profile and ffprobe validation tests.

## Done when
Rendered episodes produce validated vertical deliverables plus metadata; commit/push.
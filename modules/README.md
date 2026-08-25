# Xerama Architecture Module Queue — MODULE-001 to MODULE-080

_Last architecture freeze: 2026-08-25._

## Authority
This file is the authoritative continuous implementation queue for Claude Code/Codex. The older numbered files `01_*.md` through `14_*.md` were superseding legacy planning briefs; they were removed from the repository (see git history: "docs: remove duplicate legacy module briefs") once MODULE-001..080 fully superseded them, so history/research on that phase lives in `git log` rather than in the working tree. Similarly, `docs/ROADMAP.md` predates this queue and is marked superseded at its own top rather than kept current - `docs/IMPLEMENTATION_STATUS.md` is the live source of truth for what is actually built.

## Execution rule
Start at the first module whose acceptance criteria are not fully implemented and verified. `AUDIT/EXTEND` means substantial code may already exist: inspect and reuse it, fill gaps, test, update status, commit and push. `BUILD` means the capability was missing or incomplete at architecture freeze. Do not reimplement working functionality merely to match filenames.

For every module: read dependencies and relevant ADR/docs/research; inspect current code; implement missing requirements; add migrations/contracts/tests as needed; run targeted then full tests; run configured lint/type/format/build checks; update `docs/IMPLEMENTATION_STATUS.md` and `CHANGELOG.md`; review diff; commit and push; immediately continue.

Missing optional credentials are not a blocker: implement contracts, fake providers and non-live tests, mark only live verification pending, then continue. Stop only for completion, genuine unrecoverable dependency with no safe later work, or risk of destructive data/repository damage.

## Source priority
1. `docs/DECISIONS.md`
2. `docs/ARCHITECTURE.md`
3. current `MODULE-xxx_*.md`
4. `docs/DATA_MODEL.md` / `docs/JSON_CONTRACTS.md`
5. `docs/IMPLEMENTATION_STATUS.md`
6. current code/tests
7. `research/`

If reality disproves a lower-priority document, update documentation instead of silently diverging.

## Queue

### Foundation & story — 001–020
001 Core Platform Architecture; 002 Configuration & Environment; 003 Domain Contract System; 004 Database & Persistence; 005 Repository Architecture; 006 AI Gateway; 007 Model Registry & Routing; 008 Provider Health/Fallback; 009 Creative Brief Engine; 010 Concept Generation; 011 AI Judge & Merge; 012 Series Bible; 013 Character Engine; 014 Canon & Memory; 015 Season Architecture; 016 Reveal/Mystery Engine; 017 Episode Planning; 018 Script Generation; 019 Continuity Engine; 020 Story Quality Engine.

### Directing & media — 021–040
021 Director Engine; 022 Scene Blocking; 023 Shot Planning; 024 Prompt Compiler; 025 Style Bible; 026 Character Visual Identity; 027 Reference Asset System; 028 Storyboard Engine; 029 Image Generation; 030 Image Editing/Regeneration; 031 Media Provider Router; 032 Video Generation; 033 Character Motion/Performance; 034 Voice Generation; 035 Dialogue/Audio Pipeline; 036 Lip Sync; 037 Music Engine; 038 Sound Effects; 039 Subtitle Engine; 040 Media Asset Storage.

### Production platform & UI — 041–060
041 Job Queue; 042 Worker Architecture; 043 Retry/Recovery; 044 Multimodal QC; 045 Automatic Retakes; 046 FFmpeg Assembly; 047 Episode Versioning; 048 Vertical Export; 049 Production Cost Engine; 050 Production Observability; 051 Project API; 052 Generation API; 053 Asset API; 054 Job/Progress API; 055 Frontend Architecture; 056 Project Dashboard; 057 Story Studio; 058 Character Studio; 059 Production Studio; 060 Review/Approval Studio.

### Learning, security, release — 061–080
061 Analytics Ingestion; 062 Retention Analytics; 063 Story Performance Learning; 064 Recommendation/Optimization; 065 Human Feedback; 066 Security; 067 Authentication/Authorization; 068 Rate Limits/Abuse Protection; 069 Deployment Architecture; 070 Production Hardening; 071 Testing Architecture; 072 AI Evaluation Framework; 073 Media Evaluation Framework; 074 Integration Testing; 075 End-to-End Production Testing; 076 Failure Simulation; 077 Backup/Recovery; 078 Migration Strategy; 079 Documentation/Developer Experience; 080 Release & Operations.

## Completion definition
The architecture queue is complete only when all 80 module requirements and acceptance criteria are represented in working code/tests/docs, the full regression suite and configured static/build checks pass, application/worker/frontend start correctly, the fake-provider E2E production succeeds, migrations verify, no module-related unfinished placeholders remain, final status docs are truthful, and all completed work is committed and pushed.
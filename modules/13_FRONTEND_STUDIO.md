# Module 13 — Xerama Frontend Studio

## Mission
Build the production UI on top of the now-stable backend instead of turning Xerama into a chatbot.

## Technology
First inspect the repo; if no frontend exists, create a separate `frontend/` app using a mainstream TypeScript React stack (prefer Next.js unless repository constraints justify Vite). Keep backend API authoritative.

## Core screens
Dashboard; Projects; Project Overview; Story/Season; Series Bible/Canon; Episodes; Characters/Casting; Locations/Assets; Storyboard; Production; Audio; Editor/Render; QC; Jobs; Costs/Settings.

The Production screen is highest priority: episode shots with storyboard/keyframe/video thumbnails, status, current take, QC, retry/approve/reject controls, job progress and provider/model information.

## UX requirements
Support create/open project, generate next stage, inspect AI outputs, approve/reject/regenerate, upload manual assets, poll job progress, recover after refresh, and display actionable errors. Never expose API secrets to browser code.

## Tests
Frontend typecheck/lint/build plus critical component/API-flow tests. Backend tests remain green.

## Acceptance
A user can operate the complete Trial-01 pipeline from browser without CLI or direct API calls.

## Agent instructions
Do not build decorative complexity before functional studio workflows. Update root README/dev instructions/status/changelog, commit logical units, proceed to Module 14.
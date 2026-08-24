# MODULE-066 — Security

**Status:** BUILD
**Depends on:** 002,051-055

## Objective
Harden Xerama against common application, file, subprocess and secret-handling risks.

## Requirements
- Threat-model API, uploads, asset serving, FFmpeg subprocesses, provider secrets and logs.
- Validate paths/MIME/size; prevent traversal and unsafe command construction.
- Secret redaction and secure defaults.
- Dependency/security scanning hooks where practical.

## Verification
Security regression tests for path traversal, invalid uploads, command injection and secret leakage.

## Done when
Known high-risk surfaces have explicit controls and tests; commit/push.
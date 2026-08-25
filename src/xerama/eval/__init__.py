"""Versioned AI evaluation dataset + harness (MODULE-072).

Distinct from `pipeline/provider_ranking.py` (MODULE-064), which ranks
providers from *passive production telemetry* (real `CostRecord`/
`MediaQCAttempt` rows accumulated during normal use). This package is a
*deliberate benchmark*: a fixed, versioned set of prompts run on demand
against a specific model, before promoting a paid or replacement model
for a role - "model changes can be justified by benchmark evidence
rather than intuition."
"""

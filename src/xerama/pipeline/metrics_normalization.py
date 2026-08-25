"""Manual/import metrics adapter (MODULE-061).

"Support manual/import adapter first; platform APIs later" - this module
IS the manual adapter: it accepts a source-agnostic dict already using
`EpisodeMetric`'s normalized field names and validates/passes them
through. A future platform-API adapter (TikTok/YouTube/etc.) would map
that platform's raw response into this same shape before handing it to
`AnalyticsIngestionService.import_metrics` - no second ingestion path
needed, just another function producing this dict shape.
"""

NORMALIZED_FIELDS = (
    "impressions",
    "views",
    "avg_watch_seconds",
    "completion_rate",
    "three_second_retention_rate",
    "rewatch_rate",
    "continuation_rate",
)


def normalize_manual_payload(payload: dict) -> dict:
    normalized = {field: payload.get(field) for field in NORMALIZED_FIELDS}
    normalized["engagement"] = payload.get("engagement", {})
    return normalized

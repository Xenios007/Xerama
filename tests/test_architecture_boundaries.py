"""Import-boundary checks (MODULE-001 - Core Platform Architecture).

"Domain must not depend on providers, HTTP, or persistence implementations."
Static, text-based check rather than executing the modules - fast, has no
import-order sensitivity, and catches the boundary violation this test was
written to prevent (domain/asset.py once imported `xerama.db.base.utcnow`).
"""

import re
from pathlib import Path

DOMAIN_DIR = Path(__file__).resolve().parents[1] / "src" / "xerama" / "domain"
FORBIDDEN_PACKAGES = ("db", "api", "repositories", "providers", "pipeline", "services")
IMPORT_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+xerama\.(" + "|".join(FORBIDDEN_PACKAGES) + r")\b", re.MULTILINE
)


def test_domain_modules_do_not_import_infrastructure_packages() -> None:
    violations = []
    for path in DOMAIN_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for match in IMPORT_PATTERN.finditer(text):
            violations.append(f"{path.name} imports xerama.{match.group(1)}")
    assert violations == [], "domain/ must stay independent of infra layers:\n" + "\n".join(violations)

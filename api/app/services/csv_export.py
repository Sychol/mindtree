from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@")


@dataclass(frozen=True)
class CsvExportFile:
    content: str
    filename: str
    content_type: str = "text/csv; charset=utf-8-sig"


def sanitize_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    if text.startswith(DANGEROUS_CSV_PREFIXES):
        return f"'{text}"
    return text


def _csv_text(headers: list[str], rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([sanitize_csv_cell(row.get(header)) for header in headers])
    return "\ufeff" + output.getvalue()


def _safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    return cleaned.strip("-") or "event"


class CsvExportService:
    def build_wide_csv(
        self,
        *,
        event_slug: str,
        headers: list[str],
        rows: list[dict[str, Any]],
        now: datetime | None = None,
    ) -> CsvExportFile:
        return CsvExportFile(
            content=_csv_text(headers, rows),
            filename=self.build_filename(event_slug=event_slug, now=now),
        )

    def build_long_csv(
        self,
        *,
        event_slug: str,
        headers: list[str],
        rows: list[dict[str, Any]],
        now: datetime | None = None,
    ) -> CsvExportFile:
        return CsvExportFile(
            content=_csv_text(headers, rows),
            filename=self.build_filename(event_slug=event_slug, now=now),
        )

    def build_filename(self, *, event_slug: str, now: datetime | None = None) -> str:
        timestamp = (now or datetime.now(UTC)).strftime("%Y%m%d_%H%M%S")
        safe_slug = _safe_filename_part(event_slug)
        return f"maeumnamu_{safe_slug}_responses_{timestamp}.csv"

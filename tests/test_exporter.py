from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from singer_core.config import AppConfig
from singer_core.exporter import CsvExporter


def _default_fields() -> list[str]:
    return AppConfig(
        base_url="https://example.com",
        detail_url="https://example.com",
        request_url="https://example.com",
        auth_key="k",
        auth_secret="s",
    ).export_fields


def _default_headers() -> dict[str, str]:
    return AppConfig(
        base_url="https://example.com",
        detail_url="https://example.com",
        request_url="https://example.com",
        auth_key="k",
        auth_secret="s",
    ).export_headers


def _read_csv(filepath: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with Path(filepath).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def test_creates_file_with_headers(tmp_path: object) -> None:
    fp = str(tmp_path) + "/out.csv"  # type: ignore[arg-type]
    with CsvExporter(fp, _default_fields(), _default_headers()):
        pass
    lines = Path(fp).read_text(encoding="utf-8-sig").strip().split("\n")
    header = lines[0]
    assert "名称" in header
    assert "地址" in header


def test_write_batch_writes_rows(
    tmp_path: object, sample_records: list[dict[str, Any]]
) -> None:
    fp = str(tmp_path) + "/out.csv"  # type: ignore[arg-type]
    with CsvExporter(fp, _default_fields(), _default_headers()) as exporter:
        exporter.write_batch(sample_records)
    rows = _read_csv(fp)
    assert len(rows) == 2
    assert rows[0]["名称"] == "Test Org A"
    assert rows[1]["名称"] == "Test Org B"


def test_write_batch_ignores_extra_fields(tmp_path: object) -> None:
    fp = str(tmp_path) + "/out.csv"  # type: ignore[arg-type]
    records: list[dict[str, Any]] = [
        {"axbe0003": "Name", "extra_field": "ignored"},
    ]
    with CsvExporter(fp, _default_fields(), _default_headers()) as exporter:
        exporter.write_batch(records)
    rows = _read_csv(fp)
    assert len(rows) == 1
    assert "extra_field" not in rows[0]


def test_write_batch_handles_missing_fields(tmp_path: object) -> None:
    fp = str(tmp_path) + "/out.csv"  # type: ignore[arg-type]
    records: list[dict[str, Any]] = [
        {"axbe0003": "Name Only"},
    ]
    with CsvExporter(fp, _default_fields(), _default_headers()) as exporter:
        exporter.write_batch(records)
    rows = _read_csv(fp)
    assert len(rows) == 1
    assert rows[0]["名称"] == "Name Only"


def test_close_flushes_data(
    tmp_path: object, sample_records: list[dict[str, Any]]
) -> None:
    fp = str(tmp_path) + "/out.csv"  # type: ignore[arg-type]
    exporter = CsvExporter(fp, _default_fields(), _default_headers())
    exporter.write_batch(sample_records)
    exporter.close()
    rows = _read_csv(fp)
    assert len(rows) == 2


def test_context_manager(
    tmp_path: object, sample_records: list[dict[str, Any]]
) -> None:
    fp = str(tmp_path) + "/out.csv"  # type: ignore[arg-type]
    with CsvExporter(fp, _default_fields(), _default_headers()) as exporter:
        exporter.write_batch(sample_records)
    rows = _read_csv(fp)
    assert len(rows) == 2


def test_utf8_sig_encoding(tmp_path: object) -> None:
    fp = str(tmp_path) + "/out.csv"  # type: ignore[arg-type]
    with CsvExporter(fp, _default_fields(), _default_headers()) as exporter:
        exporter.write_batch(
            [{"axbe0003": "Test", "axbe0013": "Addr"}]
        )
    content = Path(fp).read_bytes()
    assert content[:3] == b"\xef\xbb\xbf"


def test_creates_parent_directories(tmp_path: object) -> None:
    fp = str(tmp_path) + "/nested/deep/out.csv"  # type: ignore[arg-type]
    with CsvExporter(fp, _default_fields(), _default_headers()) as exporter:
        exporter.write_batch([{"axbe0003": "Test"}])
    assert Path(fp).exists()

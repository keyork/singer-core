"""CSV 数据导出：将采集到的记录批量写入 UTF-8 BOM 编码的 CSV 文件。

特性：
    - 自动创建输出目录（含父目录）
    - UTF-8 BOM (utf-8-sig) 编码，Excel 直接打开无乱码
    - 支持字段映射：从 API 原始字段名映射为可读列标题
    - 自动忽略记录中的多余字段（extrasaction="ignore"）
    - 支持上下文管理器（with 语句）自动关闭文件
"""

from __future__ import annotations

import csv
import types
from pathlib import Path
from typing import Any


class CsvExporter:
    """流式 CSV 写入器，适用于分页采集场景下逐批写入。

    Args:
        filepath:     输出文件路径（父目录不存在时自动创建）。
        fields:       要写入的字段名列表，控制列顺序。
        headers:      字段名 → 可读列标题 的映射，缺失时回退到字段名本身。
        write_header: 是否写入表头行，断点恢复追加时传 False。
    """

    def __init__(
        self,
        filepath: str,
        fields: list[str],
        headers: dict[str, str],
        *,
        write_header: bool = True,
    ) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("a", encoding="utf-8-sig", newline="")

        self._writer = csv.DictWriter(
            self._file,
            fieldnames=fields,
            extrasaction="ignore",
        )
        if write_header:
            header_row = [headers.get(f, f) for f in fields]
            self._writer.writerow(
                dict(zip(fields, header_row, strict=True))
            )

    def write_batch(self, records: list[dict[str, Any]]) -> None:
        """批量写入记录。每条记录是一个字典，多余字段自动忽略。"""
        self._writer.writerows(records)

    def close(self) -> None:
        """刷新缓冲区并关闭文件。"""
        self._file.flush()
        self._file.close()

    def __enter__(self) -> CsvExporter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self.close()

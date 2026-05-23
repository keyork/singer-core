"""断点续抓：通过 progress.txt 记录已完成页码，支持中断恢复。

使用方式：
    tracker = ProgressTracker("progress.txt")
    start = tracker.load() + 1     # 从上次断点下一页开始
    tracker.save(page_num)         # 每页完成后保存进度
    tracker.reset()                # 重新开始时清除进度
"""

from __future__ import annotations

import logging
from pathlib import Path


class ProgressTracker:
    """基于文件的进度跟踪器，将页码持久化到纯文本文件。

    文件内容为单行整数，表示最后完成的页码。
    文件不存在或内容损坏时视为页码 0（从头开始）。
    """

    def __init__(self, filepath: str) -> None:
        self._filepath = Path(filepath)
        self._logger = logging.getLogger(__name__)

    def load(self) -> int:
        """读取最后完成的页码。文件不存在或损坏时返回 0。"""
        if not self._filepath.exists():
            return 0
        try:
            text = self._filepath.read_text(encoding="utf-8").strip()
            if not text:
                return 0
            return int(text)
        except (ValueError, OSError):
            self._logger.warning("Corrupt progress file, starting from 0")
            return 0

    def save(self, page: int) -> None:
        """将页码覆写入进度文件。"""
        self._filepath.write_text(str(page), encoding="utf-8")

    def reset(self) -> None:
        """删除进度文件。"""
        self._filepath.unlink(missing_ok=True)

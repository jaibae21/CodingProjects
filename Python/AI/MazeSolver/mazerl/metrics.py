from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass
class EpisodeMetrics:
    episode: int
    step: int
    return_: float
    length: int
    success: int
    epsilon: float
    loss: float | None


@dataclass
class EvalMetrics:
    step: int
    episode: int
    episodes: int
    success_rate: float
    avg_return: float
    avg_length: float


class CsvLogger:
    def __init__(self, path: str, fieldnames: Iterable[str]):
        self.path = path
        self.fieldnames = list(fieldnames)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._needs_header = not os.path.exists(path) or os.path.getsize(path) == 0

    def write(self, row):
        values = asdict(row) if hasattr(row, "__dataclass_fields__") else dict(row)
        if "return_" in values:
            values["return"] = values.pop("return_")

        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if self._needs_header:
                writer.writeheader()
                self._needs_header = False
            writer.writerow(values)

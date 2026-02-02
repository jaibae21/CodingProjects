from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppState:
    selected_collection_id: Optional[int] = None
    selected_collection_name: Optional[str] = None

    
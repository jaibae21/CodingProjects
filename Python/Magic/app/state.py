from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppState:
    selected_collection_id: Optional[int] = None
    selected_collection_name: Optional[str] = None

    auto_scan_enabled: bool = True
    foil_enabled: bool = False
    condition: Optional[str] = "NM"
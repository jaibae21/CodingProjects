from __future__ import annotations
import sqlite3
from typing import Any, Dict, List, Optional
from storage.db import create_collection, add_card_to_collection

def list_collections(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, name, created_at FROM collections ORDER BY created_at DESC, name ASC"
    ).fetchall()
    return [dict(r) for r in rows]

def list_collection_entries(
        conn: sqlite3.Connection,
        collection_id: int,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
          ce.id as entry_id,
          c.name as card_name,
          c.set_code,
          c.collector_number,
          ce.quantity,
          ce.is_foil,
          ce.condition,
          ce.notes,
          ce.added_at
        FROM collection_entries ce
        JOIN cards c ON c.id = ce.card_id
        WHERE ce.collection_id = ?
        ORDER BY c.name ASC
        """,
        (collection_id,),
    ).fetchall()
    return [dict(r) for r in rows]

def create_collection_service(conn: sqlite3.Connection, name: str) -> int:
    return create_collection(conn, name)

def add_card_to_collection_service(
        conn: sqlite3.Connection,
        *,
        collection_id: int,
        card: Dict[str, Any],
        quantity: int = 1, 
        is_foil: bool = False,
        condition: Optional[str] = None,
        notes: Optional[str] = None,
) -> tuple[int, int]:
    return add_card_to_collection(
        conn,
        collection_id=collection_id,
        card=card,
        quantity=quantity,
        is_foil=is_foil,
        condition=condition,
        notes=notes,
    )
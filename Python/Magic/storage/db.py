from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

# ----------------------------
# Errors
# ----------------------------

class StorageError(Exception):
    pass

class MigrationError(StorageError):
    pass

class NotFoundError(StorageError):
    pass

class UniqueConstraintError(StorageError):
    pass


# ----------------------------
# Migration registry
# ----------------------------

@dataclass(frozen=True)
class Migration:
    version: int
    filename: str


MIGRATIONS: Sequence[Migration] = (
    Migration(1, "0001_init.sql"),
)


# ----------------------------
# Core helpers
# ----------------------------

def connect(db_path: str | Path) -> sqlite3.Connection:
    """
    Open a SQLite connection with sensible defaults.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def apply_migrations(conn: sqlite3.Connection, migrations_dir: str | Path) -> None:
    """
    Apply any pending migrations in order.

    Uses schema_migrations(version) to track applied versions.
    """
    migrations_dir = Path(migrations_dir)

    # Ensure the migrations table exists (bootstrapped without relying on migration 1)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )

    applied = {
        row["version"]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }

    for mig in MIGRATIONS:
        if mig.version in applied:
            continue

        sql_path = migrations_dir / mig.filename
        if not sql_path.exists():
            raise MigrationError(f"Missing migration file: {sql_path}")

        sql = sql_path.read_text(encoding="utf-8")
        try:
            with conn:
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)",
                    (mig.version,),
                )
        except sqlite3.DatabaseError as e:
            raise MigrationError(f"Failed applying migration v{mig.version}: {e}") from e


def init_db(db_path: str | Path, migrations_dir: str | Path) -> None:
    """
    Convenience initializer: opens connection, applies migrations, closes.
    """
    conn = connect(db_path)
    try:
        apply_migrations(conn, migrations_dir)
    finally:
        conn.close()


# ----------------------------
# CRUD operations requested
# ----------------------------

def create_collection(conn: sqlite3.Connection, name: str) -> int:
    """
    Create a collection and return its id.
    """
    if not name or not name.strip():
        raise ValueError("Collection name cannot be empty.")

    try:
        cur = conn.execute(
            "INSERT INTO collections(name) VALUES (?)",
            (name.strip(),),
        )
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError as e:
        # Unique constraint on collections.name
        raise UniqueConstraintError(f"Collection '{name}' already exists.") from e


def add_card(conn: sqlite3.Connection, card: Dict[str, Any]) -> int:
    """
    Insert/update a card printing record (cached from Scryfall) and return cards.id.

    Required keys:
      - scryfall_id, name, set_code, collector_number

    Optional keys:
      - rarity, lang, layout, image_uri_normal, oracle_id
    """
    required = ("scryfall_id", "name", "set_code", "collector_number")
    missing = [k for k in required if not card.get(k)]
    if missing:
        raise ValueError(f"Missing required card fields: {missing}")

    # Normalize fields
    scryfall_id = str(card["scryfall_id"])
    name = str(card["name"])
    set_code = str(card["set_code"]).lower()
    collector_number = str(card["collector_number"])

    rarity = card.get("rarity")
    lang = card.get("lang")
    layout = card.get("layout")
    image_uri_normal = card.get("image_uri_normal")
    oracle_id = card.get("oracle_id")

    with conn:
        # Upsert on scryfall_id
        conn.execute(
            """
            INSERT INTO cards (
              scryfall_id, name, set_code, collector_number,
              rarity, lang, layout, image_uri_normal, oracle_id, last_fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(scryfall_id) DO UPDATE SET
              name=excluded.name,
              set_code=excluded.set_code,
              collector_number=excluded.collector_number,
              rarity=excluded.rarity,
              lang=excluded.lang,
              layout=excluded.layout,
              image_uri_normal=excluded.image_uri_normal,
              oracle_id=excluded.oracle_id,
              last_fetched_at=datetime('now')
            """,
            (
                scryfall_id, name, set_code, collector_number,
                rarity, lang, layout, image_uri_normal, oracle_id
            ),
        )

        row = conn.execute(
            "SELECT id FROM cards WHERE scryfall_id = ?",
            (scryfall_id,),
        ).fetchone()

    if not row:
        raise StorageError("Upsert succeeded but could not re-select card id.")
    return int(row["id"])


def increment_quantity(
    conn: sqlite3.Connection,
    *,
    collection_id: int,
    card_id: int,
    delta: int = 1,
    is_foil: bool = False,
    condition: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """
    Increment quantity for a (collection_id, card_id, is_foil, condition) variant.
    Creates an entry if none exists.
    Returns the new quantity.

    delta can be negative, but quantity will never go below 0.
    """
    if delta == 0:
        # Return current quantity
        row = conn.execute(
            """
            SELECT quantity FROM collection_entries
            WHERE collection_id=? AND card_id=? AND is_foil=? AND IFNULL(condition,'') = IFNULL(?, '')
            """,
            (collection_id, card_id, int(is_foil), condition),
        ).fetchone()
        return int(row["quantity"]) if row else 0

    with conn:
        # Ensure parent rows exist (clearer error than FK sometimes)
        c = conn.execute("SELECT 1 FROM collections WHERE id=?", (collection_id,)).fetchone()
        if not c:
            raise NotFoundError(f"Collection id {collection_id} not found.")
        k = conn.execute("SELECT 1 FROM cards WHERE id=?", (card_id,)).fetchone()
        if not k:
            raise NotFoundError(f"Card id {card_id} not found.")

        # Try update first
        cur = conn.execute(
            """
            UPDATE collection_entries
            SET
              quantity = MAX(quantity + ?, 0),
              notes = COALESCE(?, notes)
            WHERE
              collection_id=? AND card_id=? AND is_foil=? AND IFNULL(condition,'') = IFNULL(?, '')
            """,
            (delta, notes, collection_id, card_id, int(is_foil), condition),
        )

        if cur.rowcount == 0:
            # Insert new (quantity cannot be negative)
            qty = max(delta, 0)
            conn.execute(
                """
                INSERT INTO collection_entries(
                  collection_id, card_id, quantity, is_foil, condition, notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (collection_id, card_id, qty, int(is_foil), condition, notes),
            )

        row = conn.execute(
            """
            SELECT quantity FROM collection_entries
            WHERE collection_id=? AND card_id=? AND is_foil=? AND IFNULL(condition,'') = IFNULL(?, '')
            """,
            (collection_id, card_id, int(is_foil), condition),
        ).fetchone()


    if not row:
        raise StorageError("Failed to read back quantity after increment.")
    return int(row["quantity"])

def add_card_to_collection(
    conn: sqlite3.Connection,
    *,
    collection_id: int,
    card: Dict[str, Any],
    quantity: int = 1,
    is_foil: bool = False,
    condition: Optional[str] = None,
    notes: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Convenience function:
      - upserts the card into `cards` (via add_card)
      - increments quantity in `collection_entries` (via increment_quantity)

    Returns: (card_id, new_quantity)

    quantity can be negative, but the stored quantity will never go below 0.
    """
    if quantity == 0:
        # still ensure card exists / is cached
        card_id = add_card(conn, card)
        new_qty = increment_quantity(
            conn,
            collection_id=collection_id,
            card_id=card_id,
            delta=0,
            is_foil=is_foil,
            condition=condition,
            notes=notes,
        )
        return card_id, new_qty

    card_id = add_card(conn, card)
    new_qty = increment_quantity(
        conn,
        collection_id=collection_id,
        card_id=card_id,
        delta=quantity,
        is_foil=is_foil,
        condition=condition,
        notes=notes,
    )
    return card_id, new_qty


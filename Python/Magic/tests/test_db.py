from __future__ import annotations

from pathlib import Path

import pytest

from storage.db import (
    connect,
    apply_migrations,
    create_collection,
    add_card,
    add_card_to_collection,
    increment_quantity,
    UniqueConstraintError,
    NotFoundError,
)

@pytest.fixture()
def db_conn(tmp_path: Path):
    db_path = tmp_path / "test.sqlite"
    migrations_dir = Path(__file__).resolve().parents[1] / "storage" / "migrations"
    conn = connect(db_path)
    apply_migrations(conn, migrations_dir)
    yield conn
    conn.close()


def test_create_collection_unique(db_conn):
    cid = create_collection(db_conn, "My Binder")
    assert isinstance(cid, int) and cid > 0

    with pytest.raises(UniqueConstraintError):
        create_collection(db_conn, "My Binder")


def test_add_card_upsert(db_conn):
    card = {
        "scryfall_id": "11111111-1111-1111-1111-111111111111",
        "name": "Lightning Bolt",
        "set_code": "lea",
        "collector_number": "162",
        "rarity": "common",
        "lang": "en",
        "layout": "normal",
        "image_uri_normal": "https://example.com/bolt.jpg",
        "oracle_id": "22222222-2222-2222-2222-222222222222",
    }

    card_id_1 = add_card(db_conn, card)
    assert card_id_1 > 0

    # Update some fields, same scryfall_id => same cards.id
    card2 = dict(card)
    card2["rarity"] = "uncommon"
    card_id_2 = add_card(db_conn, card2)
    assert card_id_2 == card_id_1

    row = db_conn.execute("SELECT rarity FROM cards WHERE id=?", (card_id_1,)).fetchone()
    assert row["rarity"] == "uncommon"


def test_increment_quantity_creates_then_increments(db_conn):
    cid = create_collection(db_conn, "C1")
    card_id = add_card(
        db_conn,
        {
            "scryfall_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "name": "Opt",
            "set_code": "dom",
            "collector_number": "60",
        },
    )

    q1 = increment_quantity(db_conn, collection_id=cid, card_id=card_id, delta=1, is_foil=False, condition=None)
    assert q1 == 1

    q2 = increment_quantity(db_conn, collection_id=cid, card_id=card_id, delta=3, is_foil=False, condition=None)
    assert q2 == 4

    # Different variant (foil) => separate row
    q3 = increment_quantity(db_conn, collection_id=cid, card_id=card_id, delta=2, is_foil=True, condition=None)
    assert q3 == 2

    # Negative delta floors at 0
    q4 = increment_quantity(db_conn, collection_id=cid, card_id=card_id, delta=-99, is_foil=True, condition=None)
    assert q4 == 0


def test_increment_quantity_missing_parents(db_conn):
    # No collection / card
    with pytest.raises(NotFoundError):
        increment_quantity(db_conn, collection_id=999, card_id=1, delta=1)

    cid = create_collection(db_conn, "C1")
    with pytest.raises(NotFoundError):
        increment_quantity(db_conn, collection_id=cid, card_id=999, delta=1)

def test_add_card_to_collection_happy_path(db_conn):
    cid = create_collection(db_conn, "Binder A")

    card = {
        "scryfall_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "name": "Counterspell",
        "set_code": "2ed",
        "collector_number": "53",
        "rarity": "uncommon",
        "lang": "en",
    }

    card_id, qty1 = add_card_to_collection(
        db_conn,
        collection_id=cid,
        card=card,
        quantity=2,
        is_foil=False,
        condition="NM",
        notes="first batch",
    )
    assert card_id > 0
    assert qty1 == 2

    # same printing + same variant => increments same row
    card_id2, qty2 = add_card_to_collection(
        db_conn,
        collection_id=cid,
        card=card,
        quantity=3,
        is_foil=False,
        condition="NM",
    )
    assert card_id2 == card_id
    assert qty2 == 5

    # different variant (foil) => separate row
    _, qty3 = add_card_to_collection(
        db_conn,
        collection_id=cid,
        card=card,
        quantity=1,
        is_foil=True,
        condition="NM",
    )
    assert qty3 == 1

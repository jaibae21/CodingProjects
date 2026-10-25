from datetime import date

import pytest

from skinflow.seed import seed


def test_seed_is_complete_idempotent_and_unverified(db, inventory):
    seed(db)
    products = inventory.list()
    assert len(products) == 24
    assert all(not p.ingredients and not p.ingredients_verified for p in products)
    assert any(p.brand == "Avène" for p in products)
    assert not inventory.list(category="Sunscreen")


def test_create_edit_archive_and_search(inventory):
    product = inventory.save(
        {
            "brand": "Example",
            "name": "Test gel",
            "category": "Moisturizer",
            "actives": "Example active",
            "opened_on": date(2026, 1, 1),
        }
    )
    assert product.date_added == date.today()
    assert inventory.list(search="EXAMPLE ACTIVE")[0].id == product.id
    edited = inventory.save(
        {
            "name": "Updated gel",
            "status": "Testing",
            "ingredients": "Water",
            "ingredients_verified": True,
        },
        product.id,
    )
    assert edited.name == "Updated gel" and edited.ingredients_verified
    inventory.archive(product.id)
    assert inventory.list(status="Archived")[0].id == product.id
    assert not inventory.list(search="Updated gel", status="Active")
    assert inventory.list(search="Updated gel", category="Moisturizer")


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"category": "Invalid"},
        {"status": "Invalid"},
        {"suitability": "Evening"},
        {"opened_on": date(2026, 5, 1), "expires_on": date(2026, 4, 1)},
        {"ingredients_verified": True},
        {"deleted": True},
    ],
)
def test_invalid_edits_are_atomic(inventory, changes):
    product = inventory.list()[0]
    with pytest.raises(ValueError):
        inventory.save(changes, product.id)
    assert inventory.get(product.id).name == product.name
    assert inventory.get(product.id).status == "Active"


def test_delete_preserves_history_and_is_not_reseeded(db, inventory, schedule):
    day = date(2026, 10, 26)
    step = schedule.routine(day, "AM")["steps"][0]
    schedule.mark(day, "AM", step, True)
    inventory.delete(step["product_id"])
    seed(db)
    assert len(inventory.list()) == 23
    assert schedule.history()[0].label == step["label"]
    assert schedule.routine(day, "AM")["steps"][0] == step
    with pytest.raises(ValueError):
        inventory.get(step["product_id"])

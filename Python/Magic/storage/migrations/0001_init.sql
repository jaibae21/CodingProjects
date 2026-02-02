-- 0001_init.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS collections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scryfall_id TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  set_code TEXT NOT NULL,
  collector_number TEXT NOT NULL,
  rarity TEXT,
  lang TEXT,
  layout TEXT,
  image_uri_normal TEXT,
  oracle_id TEXT,
  last_fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name);

CREATE TABLE IF NOT EXISTS collection_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id INTEGER NOT NULL,
  card_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity >= 0),
  is_foil INTEGER NOT NULL DEFAULT 0 CHECK (is_foil IN (0, 1)),
  condition TEXT,
  notes TEXT,
  added_at TEXT NOT NULL DEFAULT (datetime('now')),

  FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
  FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_card_variant
ON collection_entries(collection_id, card_id, is_foil, IFNULL(condition, ''));

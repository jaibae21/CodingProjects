package com.chess.engine.board;

import java.util.HashMap;
import java.util.Map;

import com.chess.engine.pieces.Piece;
import com.google.common.collect.ImmutableMap;

public abstract class Tile {

    //mutable object
    protected final int tileCoords; //once the field is set it can't be set again and is protected from other classes messing with it

    private static final Map<Integer, EmptyTile> EMPTY_TILES_CACHE = createAllPossibleEmptyTiles();

    public abstract boolean isTileOccupied();

    public abstract Piece getPiece();

    private static Map<Integer, EmptyTile> createAllPossibleEmptyTiles() {
        final Map<Integer, EmptyTile> emptyTileMap = new HashMap<>();

        //store empty tiles
        for (int i = 0; i < BoardUtils.NUM_TILES; i++) {
            emptyTileMap.put(i, new EmptyTile(i));
        }

        return ImmutableMap.copyOf(emptyTileMap);
    }

    //create tiles
    public static Tile creaTile(final int tileCoords, final Piece piece) {
        return piece != null ? new OccupiedTile(tileCoords, piece) : EMPTY_TILES_CACHE.get(tileCoords);
    }

    //settersrc/com/chess/engine/board/Tile.java
    private Tile(final int tileCoords) {
        this.tileCoords = tileCoords;
    }

    //subclass
    public static final class EmptyTile extends Tile {

        private EmptyTile(final int coordinate) {
            super(coordinate);
        }

        @Override
        public boolean isTileOccupied() {
            return false;
        }

        @Override
        public Piece getPiece() {
            return null;
        }

    }
    
    //subclass
    public static final class OccupiedTile extends Tile {

        private final Piece pieceOnTile;    //no way to ref variable outside without calling getPiece

        private OccupiedTile(int tileCoords, final Piece pieceOnTile) {
            super(tileCoords);
            
            this.pieceOnTile = pieceOnTile;
        }

        @Override
        public boolean isTileOccupied() {
            
            return true;
        }

        @Override
        public Piece getPiece() {
            return this.pieceOnTile;
        }
    }

}
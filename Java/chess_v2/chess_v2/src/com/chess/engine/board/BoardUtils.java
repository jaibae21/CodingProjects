package com.chess.engine.board;

public class BoardUtils {

    public static final boolean[] FIRST_COL = initColumn(0);
    public static final boolean[] SECOND_COL = initColumn(1);
    public static final boolean[] SEVENTH_COL = initColumn(6);
    public static final boolean[] EIGHT_COL = initColumn(7);

    public static final int NUM_TILES = 64;
    public static final int NUM_TILES_PER_ROW = 8;

    private BoardUtils() {
        throw new RuntimeException("You cannot instatntiate");
    }

    private static boolean[] initColumn(int columnNumber) {
        
        final boolean[] column = new boolean[64];
        do{
            column[columnNumber] = true;
            columnNumber += NUM_TILES_PER_ROW;
        } while(columnNumber < NUM_TILES);
        return column;
    }

    public static boolean isValidTileCoord(final int coord) {
        return coord >= 0 && coord < NUM_TILES;
    }
}

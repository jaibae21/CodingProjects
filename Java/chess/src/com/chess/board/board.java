package com.chess.board;

import java.util.HashMap;
import java.util.Map;

import com.chess.common.File;
import com.chess.common.Location;
import com.chess.squares.Sqaurecolor;
import com.chess.squares.Square;

public class board {
    private static final Integer BOARD_LENGTH = 8;
    private final Map<Location, Square> locationSquareMap;

    Square[][] boardSquares = new Square[BOARD_LENGTH][BOARD_LENGTH];

    public board() {
        locationSquareMap = new HashMap<>();
        for (int i = 0; i < boardSquares.length; i++) {
            int col = 0;
            Sqaurecolor currentColor = (i % 2 == 0) ? Sqaurecolor.LIGHT : Sqaurecolor.DARK;
            for (File file : File.values()) {
                Square newSqaure = new Square(currentColor, new Location(file, BOARD_LENGTH - i));
                locationSquareMap.put(newSqaure.getLocation(), newSqaure);
                boardSquares[i][col] = newSqaure;
                currentColor = (currentColor == Sqaurecolor.DARK) ? Sqaurecolor.LIGHT : Sqaurecolor.DARK;
                col++;
            }
        }
    }

    public Map<Location, Square> getLocationSquareMap() {
        return locationSquareMap;
    }
    public void printBoard() {
        for(Square[] row : boardSquares) {
            for (Square square : row) {
                System.out.println(square);
            }
            System.out.println();
        }
    }
}
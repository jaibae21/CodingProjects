package com.chess.piece;

import java.util.List;

import com.chess.board.board;
import com.chess.common.Location;
import com.chess.squares.Square;

public interface Moveable {
    List<Location> getValidMoves(board board);
    List<Location> getValidMoves(board board, Square sqaure);
    void makeMove(Square square);
}

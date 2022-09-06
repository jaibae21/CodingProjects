package com.chess.runner;

import com.chess.board.board;
import com.chess.piece.AbstractPiece;
import com.chess.piece.Moveable;
import com.chess.piece.Pawn;
import com.chess.piece.PieceColor;
import com.chess.piece.Queen;

public class Game {
    public static void main(String[] args) {
        //board board = new board();
        PieceColor color = PieceColor.DARK;
        Moveable pawn = new Pawn(color);
        Queen queen = new Queen(color);
        Game.printPieces(pawn);
        Game.printPieces(queen);
        //board.printBoard();
    }
    public static void printPieces(Moveable piece) {
        piece.getValidMoves(null);
    }
}

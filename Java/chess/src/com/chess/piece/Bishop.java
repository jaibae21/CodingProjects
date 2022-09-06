package com.chess.piece;

import java.util.List;

import com.chess.board.board;
import com.chess.common.Location;
import com.chess.squares.Square;

public class Bishop extends AbstractPiece implements Moveable{
    public Bishop(PieceColor pieceColor) {
        super(pieceColor);
        this.name = "Bishop";
    }

    @Override
    public List<Location> getValidMoves(board board) {
        System.out.println(this.getName() + "-> getValidMoves()");
        return null;
    }

    @Override
    public void makeMove(Square square) {
        System.out.println(this.getName() + "-> makeMove()");
        
    }

    @Override
    public List<Location> getValidMoves(board board, Square sqaure) {
        // TODO Auto-generated method stub
        return null;
    }
}

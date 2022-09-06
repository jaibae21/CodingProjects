package com.chess.piece;

import java.util.Collections;
import java.util.List;

import com.chess.board.board;
import com.chess.common.Location;
import com.chess.squares.Square;

public class Queen extends AbstractPiece implements Moveable{
    
    private Moveable bishop;
    private Moveable rook;
    public Queen(PieceColor pieceColor) {
        super(pieceColor);
        this.name = "Queen";
    }

    public Queen(PieceColor pieceColor, Moveable bishop, Moveable rook) {
        super(pieceColor);
        this.bishop = bishop;
        this.rook = rook;
    }

    //composes queen to multiple moveable pieces
    @Override
    public List<Location> getValidMoves(board board) {
        List<Location> moveCandidates = Collections.emptyList();
        moveCandidates.addAll(bishop.getValidMoves(board, this.getCurrentSquare()));
        moveCandidates.addAll(rook.getValidMoves(board, this.getCurrentSquare()));
        return moveCandidates;
    }

    @Override
    public void makeMove(Square square) {
        Square current = this.getCurrentSquare();
        this.setCurrentSquare(square);
        current.reset();
        
    }

    @Override
    public List<Location> getValidMoves(board board, Square sqaure) {
        // TODO Auto-generated method stub
        return null;
    }
}

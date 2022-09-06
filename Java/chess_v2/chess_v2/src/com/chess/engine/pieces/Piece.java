package com.chess.engine.pieces;

import java.util.Collection;

import com.chess.engine.Alliance;
import com.chess.engine.board.Board;
import com.chess.engine.board.Move;

public abstract class Piece {
    
    protected final int piecePostition;
    protected final Alliance pieceAlliance;

    Piece(final int piecePostition, final Alliance pieceAlliance) {
        this.pieceAlliance = pieceAlliance;
        this.piecePostition = piecePostition;
    }

    //calculate leagal moves - returns a list
    public abstract Collection<Move> calculateLegalMoves(final Board board);

    public Alliance getPieceAlliance() {
        return this.pieceAlliance;
    }

}

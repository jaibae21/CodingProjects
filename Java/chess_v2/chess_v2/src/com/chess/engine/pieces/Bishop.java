package com.chess.engine.pieces;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import com.chess.engine.Alliance;
import com.chess.engine.board.Board;
import com.chess.engine.board.BoardUtils;
import com.chess.engine.board.Move;
import com.chess.engine.board.Tile;
import com.google.common.collect.ImmutableList;

public class Bishop extends Piece {

    private final static int[] CANDIDATE_MOVE_VCOORDS = {-9, -7, 7, 9};

    Bishop(int piecePostition, Alliance pieceAlliance) {
        super(piecePostition, pieceAlliance);
    }

    @Override
    public Collection<Move> calculateLegalMoves(final Board board) {
        
        final List<Move> legalMoves = new ArrayList<>();
        
        for (final int candidateCoordOffset: CANDIDATE_MOVE_VCOORDS) {

            int candidateDestCoord = this.piecePostition;

            while(BoardUtils.isValidTileCoord(candidateDestCoord)) {
                
                if(isFirstColExclusion(this.piecePostition, candidateCoordOffset) || isEighthColExclusion(this.piecePostition, candidateCoordOffset)) {
                        break;
                    }

                candidateDestCoord += candidateCoordOffset;

                if(BoardUtils.isValidTileCoord(candidateDestCoord)) {
                
                    final Tile candidateDestCoordTile = board.gtTile(candidateDestCoord);
                    //if its not occupied add nonattacking move
                    if(!candidateDestCoordTile.isTileOccupied()) {
                        legalMoves.add(new Move.MajorMove(board, this, candidateDestCoord));
                    }
                    else {
                        //figure out alliance of piece at coord
                        final Piece pieceAtDest = candidateDestCoordTile.getPiece();
                        final Alliance pieceAlliance = pieceAtDest.getPieceAlliance();
    
                        //if its an enemy - add attacking move
                        if(this.pieceAlliance != pieceAlliance) {
                            legalMoves.add(new Move.AttackMove(board,this, candidateDestCoord, pieceAtDest));
                        }
                        break;
                    }
                }
            }
        }
        return ImmutableList.copyOf(legalMoves);
    }

    private static boolean isFirstColExclusion(final int currentPos, final int candidateOffset) {
        return BoardUtils.FIRST_COL[currentPos] && (candidateOffset == -9 || candidateOffset == 7);
    }

    private static boolean isEighthColExclusion(final int currentPos, final int candidateOffset) {
        return BoardUtils.EIGHT_COL[currentPos] && (candidateOffset == -7 || candidateOffset == 9);
    }
}

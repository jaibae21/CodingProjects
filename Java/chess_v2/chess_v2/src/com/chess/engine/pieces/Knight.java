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

public class Knight extends Piece {

    private final static int[] CANDIDATE_MOVE_COORDS = {-17, -15, -10, -6, 6, 10, 15, 17};
    
    Knight(int piecePostition, Alliance pieceAlliance) {
        super(piecePostition, pieceAlliance);
    }

    @Override
    public Collection<Move> calculateLegalMoves(final Board board) {

        final List<Move> legalMoves = new ArrayList<>();

        //go through list of moves
        for(final int currentCandidateOffset : CANDIDATE_MOVE_COORDS) {
            //add the offset
            final int candidateDestCoord = this.piecePostition +  currentCandidateOffset;
            //if valid coord
            if(BoardUtils.isValidTileCoord(candidateDestCoord)) {
                
                if(isFirstColExclusion(this.piecePostition, currentCandidateOffset) || isSecondColExclusion(this.piecePostition, currentCandidateOffset) || isSeventhColExclusion(this.piecePostition, currentCandidateOffset) || isEighthColExclusion(this.piecePostition, currentCandidateOffset)) {
                    continue;
                }

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
                }
            }
        }
        return ImmutableList.copyOf(legalMoves);
    }

    //edge cases
    private static boolean isFirstColExclusion(final int currentPos, final int candidateOffset) {
       return BoardUtils.FIRST_COL[currentPos] && (candidateOffset == -17 || candidateOffset == -10 || candidateOffset == 6 || candidateOffset == 15);
    }

    private static boolean isSecondColExclusion(final int currentPos, final int candidateOffset) {
        return BoardUtils.SECOND_COL[currentPos] && (candidateOffset == -10 || candidateOffset == -6);
    }

    private static boolean isSeventhColExclusion(final int currentPos, final int candidateOffset) {
        return BoardUtils.SEVENTH_COL[currentPos] && (candidateOffset == -6 || candidateOffset == 10);
    }

    private static boolean isEighthColExclusion(final int currentPos, final int candidateOffset) {
        return BoardUtils.EIGHT_COL[currentPos] && (candidateOffset == -15 || candidateOffset == -6 || candidateOffset == 10 || candidateOffset == 17);
    }

}

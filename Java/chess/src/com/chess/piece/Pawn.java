package com.chess.piece;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.chess.board.board;
import com.chess.common.Location;
import com.chess.common.LocationFactory;
import com.chess.squares.Square;

public class Pawn extends AbstractPiece implements Moveable{
    private boolean isFirstMove = true;


    public Pawn(PieceColor pieceColor) {
        super(pieceColor);
        this.name = "Pawn";
    }

    @Override
    public List<Location> getValidMoves(board board) {
        List<Location> moveCandidates = Collections.emptyList();
        Location current = this.getCurrentSquare().getLocation();
        //can always move forward by one
        moveCandidates.add(LocationFactory.build(current, 0, 1));
        if(isFirstMove) {
            
            moveCandidates.add(LocationFactory.build(current, 0, 2));
            return moveCandidates;
        }

        moveCandidates.add(LocationFactory.build(current, 1, 1));
        moveCandidates.add(LocationFactory.build(current, -1, 1));
        
        Map<Location, Square> squareMap = board.getLocationSquareMap();
        List<Location> validMoves = moveCandidates.stream().filter(squareMap::containsKey).collect(Collectors.toList());
        
        return validMoves.stream().filter((candidate) -> {
            if(candidate.getFile().equals(this.getCurrentSquare().getLocation().getFile()) && squareMap.get(candidate).isOccupied()) {
                return false;
            }

            return !squareMap.get(candidate).getCurrentPiece().pieceColor.equals(this.getPieceColor());
        }).collect(Collectors.toList());

        
    }

    @Override
    public void makeMove(Square square) {
        System.out.println(this.getName() + "-> makeMove()");
        
    }

    @Override
    public List<Location> getValidMoves(board board, Square sqaure) {
        
        return null;
    }

}

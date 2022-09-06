package com.chess.piece;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import com.chess.board.board;
import com.chess.common.Location;
import com.chess.common.LocationFactory;
import com.chess.squares.Square;

public class Rook extends AbstractPiece implements Moveable{
    public Rook(PieceColor pieceColor) {
        super(pieceColor);
        this.name = "Rook";
    }

    @Override
    public List<Location> getValidMoves(board board) {
        List<Location> moveCandidates = new ArrayList<>();
        Map<Location, Square> squareMap = board.getLocationSquareMap();
        Location current = this.getCurrentSquare().getLocation();
        Location nextLeft = LocationFactory.build(current, -1, 0);
        while(squareMap.containsKey(nextLeft)) {
            if(squareMap.get(nextLeft).isOccupied()) {
                if(squareMap.get(nextLeft).getCurrentPiece().pieceColor.equals(this.pieceColor)){
                    break;
                }
                moveCandidates.add(nextLeft);
                break;
            }
            moveCandidates.add(nextLeft);
            nextLeft = LocationFactory.build(nextLeft, -1, 0);
        }

        Location nextRight = LocationFactory.build(current, 1, 0);
        while(squareMap.containsKey(nextRight)) {
            if(squareMap.get(nextRight).isOccupied()) {
                if(squareMap.get(nextRight).getCurrentPiece().pieceColor.equals(this.pieceColor)){
                    break;
                }
                moveCandidates.add(nextRight);
                break;
            }
            moveCandidates.add(nextRight);
            nextLeft = LocationFactory.build(nextRight, -1, 0);
        }
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

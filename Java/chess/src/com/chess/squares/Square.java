package com.chess.squares;

import com.chess.common.Location;
import com.chess.piece.AbstractPiece;

public class Square {
    private final Sqaurecolor sqaurecolor;
    private final Location location;
    private boolean isOccupied;
    private AbstractPiece currentPiece;

    public Square(Sqaurecolor sqaurecolor, Location location) {
        this.sqaurecolor = sqaurecolor;
        this.location = location;
        this.isOccupied = false;
    }

    //resets square after piece moves
    public void reset() {
        this.isOccupied = false;
        this.currentPiece = null;
    }

    //getter/setter methods
    public boolean isOccupied() {
        return isOccupied;
    }

    public void setOccupied(boolean occupied) {
        isOccupied = occupied;
    }

    public Sqaurecolor getSqaurecolor() {
        return sqaurecolor;
    }

    public Location getLocation() {
        return location;
    }

    public AbstractPiece getCurrentPiece() {
        return currentPiece;
    }

    public void setCurrentPiece(AbstractPiece currentPiece) {
        this.currentPiece = currentPiece;
    }
    
    @Override public String toString() {
        return "Square{" + "squareColor=" + sqaurecolor + " location={" + location + " isOccupied=" + isOccupied + '}';
    }


}


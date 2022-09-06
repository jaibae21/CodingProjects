'''
Author: Jaiden
Start Date: 8/24/22
End Date: 
Source: Python Artificial Intelligence Tutorial: 
        https://www.youtube.com/watch?v=XIrOM9oP3pA
'''

import cv2
from random import randrange

#Using Webcam

# Load some pre-trained data on face frontals from opencv github (haar cascade algorithm)
trained_face_data = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

#Choose video source- 0 means default cam or 'video_name.mp4' 
cam = cv2.VideoCapture(0)

#Iterate over frames
while True:

    #Read frame
    cv2.imshow()
    key = cv2.waitKey(1)

#From and image
'''
    

    #Choose an image to detect faces in 
    img = cv2.imread('Pictures/multi.jpg')

    #convert to grayscale
    grayscale_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    #detect faces
    faceCoords = trained_face_data.detectMultiScale(grayscale_img)
    print(faceCoords) #debug/info

    # draw rectangle around face- img, (top left point), (width,height), color, thickness
    for (x, y, w, h) in faceCoords:
        cv2.rectangle(img, (x,y), (x+w, y+h), (randrange(256), randrange(256), randrange(256)), 3)

    # Show the image- Face Detector is name of window that pops up 
    cv2.imshow('Face Detector', img)
    cv2.waitKey()   #pauses code execution so window doesn't open and close immediately until any key pressed

    print("Code Completed")

'''

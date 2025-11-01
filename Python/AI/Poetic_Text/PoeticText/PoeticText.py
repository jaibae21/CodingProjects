"""
Author: Jaiden Gann
Start Date: 10/3/2022
Finish Date: 
Source: https://www.youtube.com/watch?v=QM5XDc4NQJo&list=PL7yh-TELLS1G9mmnBN3ZSY8hYgJ5kBOg-&index=1
Changes: 
"""

import random
import numpy as np
import tensorflow as tf
from keras.models import Sequential
from keras.layers import LSTM, Dense, Activation
from keras.optimizers import RMSprop

#filepath = '/shakespeare.txt'
filepath = tf.keras.utils.get_file('shakespeare.txt', 'https://storage.googleapis.com/download.tensorflow.org/data/shakespeare.txt')

#open file in read binary, decode, and change to all lowercase
text = open(filepath, 'rb').read().decode(encoding='utf-8').lower()

#train on part of the text, character x to x 
text = text[300000:800000] 

#filter out unique characters
characters = sorted(set(text))

#create 2 dictionaries to convert to num format and back
char_to_index = dict((c, i) for i, c in enumerate(characters))  #ex {'a': 1,'f':27}
index_to_char = dict((i, c) for i, c in enumerate(characters))

#

print("test")
import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use('Agg')  # fix error RuntimeError: main thread is not in main loop
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

import os
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.utils import to_categorical

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv2D, MaxPool2D, Flatten

(in_train, out_train), (in_test, out_test) = cifar10.load_data()
out_cat_train = to_categorical(out_train, 10)
out_cat_test = to_categorical(out_test, 10)

# Create Sequential Model
model = Sequential()
# Layer 1: Convolutional Layer
model.add(Conv2D(filters=32, kernel_size=(4,4), input_shape=(32,32,3), activation='relu',))
# Layer 2: Pooling Layer
model.add(MaxPool2D(pool_size=(2,2)))
# Layer 3: Convolutional Layer
model.add(Conv2D(filters=32, kernel_size=(4,4), input_shape=(32,32,3), activation='relu',))
# Layer 4: Pooling Layer
model.add(MaxPool2D(pool_size=(2,2)))
# Layer 5: Flatten Layer
model.add(Flatten())
# Layer 6: Dense Layer (Hidden Layer)
model.add(Dense(256, activation='relu'))
# Layer 7: Dense Layer (Output Layer)
model.add(Dense(10, activation='softmax'))

model.summary()

model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

model.fit(in_train, out_cat_train, epochs=15, validation_data=(in_test, out_cat_test))

metrics = pd.DataFrame(model.history.history)
print(f'Metrics: {metrics}')
metrics[['loss', 'val_loss']].plot()
metrics[['accuracy', 'val_accuracy']].plot()

test_loss, test_acc = model.evaluate(in_test, out_cat_test, verbose=0)
print(f'Test loss: {test_loss:.4f}')
print(f'Test accuracy: {test_acc:.4f}')

model.save('cifar10_model.keras')

my_image = in_test[10]
plt.imshow(my_image)



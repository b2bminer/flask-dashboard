import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # fix error RuntimeError: main thread is not in main loop
from matplotlib import pyplot as plt

import os
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPool2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.utils import to_categorical

# สร้างโมเดล CNN
def create_cnn_model(input_shape, num_classes):
    model = Sequential()
    
    # Layer 1: Convolutional Layer
    model.add(Conv2D(filters=32, kernel_size=(3,3), input_shape=input_shape, activation='relu'))
    # Layer 2: Pooling Layer
    model.add(MaxPool2D(pool_size=(2,2)))
    # Layer 3: Convolutional Layer
    model.add(Conv2D(filters=64, kernel_size=(3,3), activation='relu'))
    # Layer 4: Pooling Layer
    model.add(MaxPool2D(pool_size=(2,2)))
    # Layer 5: Convolutional Layer
    model.add(Conv2D(filters=128, kernel_size=(3,3), activation='relu'))
    # Layer 6: Flatten Layer
    model.add(Flatten())
    # Layer 7: Dense Layer (Hidden Layer)
    model.add(Dense(128, activation='relu'))
    # Layer 8: Dropout Layer
    model.add(Dropout(0.5))
    # Layer 9: Dense Layer (Output Layer)
    model.add(Dense(num_classes, activation='softmax'))
    
    model.compile(optimizer='adam',
                 loss='categorical_crossentropy',
                 metrics=['accuracy'])
    
    return model

def create_improved_model(input_shape, num_classes):
    model = Sequential([
        Conv2D(32, (3,3), activation='relu', input_shape=input_shape),
        #BatchNormalization(),
        MaxPool2D((2,2)),
        
        Conv2D(64, (3,3), activation='relu'),
        #BatchNormalization(),
        MaxPool2D((2,2)),
        
        Conv2D(128, (3,3), activation='relu'),
        #BatchNormalization(),
        MaxPool2D((2,2)),
        
        Flatten(),
        Dense(256, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(optimizer='adam',
                loss='categorical_crossentropy',
                metrics=['accuracy'])
    return model

# ตรวจสอบ dataset
dataset_path = 'dataset'
if not os.path.exists(dataset_path):
    raise Exception(f"Directory {dataset_path} does not exist")

classes = [d for d in os.listdir(dataset_path) 
          if os.path.isdir(os.path.join(dataset_path, d))]

if not classes:
    raise Exception("No class folders found in dataset directory")

print("Found classes:", classes)

for cls in classes:
    cls_path = os.path.join(dataset_path, cls)
    num_files = len([f for f in os.listdir(cls_path) 
                    if os.path.isfile(os.path.join(cls_path, f))])
    print(f"Class {cls}: {num_files} images")

num_classes = len(classes)

# กำหนดพารามิเตอร์
IMG_SIZE = (224, 224)
INPUT_SHAPE = (*IMG_SIZE, 3)  # 3 channels (RGB)
batch_size = 32

# สร้าง data generator
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,       # เพิ่มจาก 10 เป็น 20
    width_shift_range=0.2,  # เพิ่มจาก 0.1 เป็น 0.2
    height_shift_range=0.2,
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    vertical_flip=True,      # เพิ่ม flip แนวตั้ง
    fill_mode='nearest',
    validation_split=0.2)

# สร้าง generator สำหรับข้อมูลฝึก
train_generator = train_datagen.flow_from_directory(
    dataset_path,
    target_size=IMG_SIZE,
    batch_size=batch_size,
    class_mode='categorical',
    subset='training')

validation_generator = train_datagen.flow_from_directory(
    dataset_path,
    target_size=IMG_SIZE,
    batch_size=batch_size,
    class_mode='categorical',
    subset='validation')

# สร้างและฝึกโมเดล
#model = create_cnn_model(INPUT_SHAPE, num_classes)
model = create_improved_model(INPUT_SHAPE, num_classes)
model.summary()

history = model.fit(
    train_generator,
    steps_per_epoch=train_generator.samples // batch_size,
    epochs=20,
    validation_data=validation_generator,
    validation_steps=validation_generator.samples // batch_size)

# บันทึกผลลัพธ์และแสดงกราฟเหมือนในไฟล์ CIFAR10
metrics = pd.DataFrame(history.history)
print(f'Metrics: {metrics}')
metrics[['loss', 'val_loss']].plot()
plt.savefig('loss_plot.png')
metrics[['accuracy', 'val_accuracy']].plot()
plt.savefig('accuracy_plot.png')

# ประเมินโมเดล
val_loss, val_acc = model.evaluate(validation_generator, verbose=0)
print(f'Validation loss: {val_loss:.4f}')
print(f'Validation accuracy: {val_acc:.4f}')

# บันทึกโมเดล
model.save('candlestick_pattern_recognition.keras')

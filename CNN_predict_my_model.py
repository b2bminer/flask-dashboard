import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import json
import os

def get_class_names(dataset_path):
    """ดึงชื่อคลาสจากไดเร็กทอรี่ dataset"""
    if not os.path.exists(dataset_path):
        raise Exception(f"Directory {dataset_path} does not exist")
    
    classes = [d for d in os.listdir(dataset_path) 
              if os.path.isdir(os.path.join(dataset_path, d))]
    
    if not classes:
        raise Exception("No class folders found in dataset directory")
    
    # เรียงลำดับตามตัวอักษรเพื่อให้แน่ใจว่าสอดคล้องกับลำดับที่โมเดลคาดหวัง
    classes.sort()
    return classes

def prepare_image(img_path, target_size=(224, 224)):
    """เตรียมภาพสำหรับทำนาย"""
    img = image.load_img(img_path, target_size=target_size)
    img_array = image.img_to_array(img)
    img_array = img_array / 255.0  # Normalize
    img_array = np.expand_dims(img_array, axis=0)  # เพิ่ม batch dimension
    return img_array

def predict_pattern(model, img_path, class_names, confidence_threshold=0.7):
    """ทำนายและแสดงผล"""
    # เตรียมภาพ
    img_array = prepare_image(img_path)
    
    # ทำนาย
    predictions = model.predict(img_array)
    predicted_class = np.argmax(predictions[0])
    confidence = np.max(predictions[0])
    
    #if confidence < confidence_threshold:
    #    return "uncertain", confidence

    # แสดงผล
    img = image.load_img(img_path)
    plt.imshow(img)
    plt.title(f"Predicted: {class_names[predicted_class]} ({confidence:.2%})")
    plt.axis('off')
    filename = f"prediction_my_model.png"
    plt.savefig(filename)
    plt.show()
    plt.close()
    
    return class_names[predicted_class], confidence

def predict_patternAPI(test_image_path):
    # กำหนดพารามิเตอร์
    dataset_path = 'dataset'
    model_path = 'candlestick_pattern_recognition.keras'
    #test_image_path = 'test_image.png'  # เปลี่ยนเป็น path ของภาพที่ต้องการทดสอบ
    
    try:
        # ดึงชื่อคลาสจากไดเร็กทอรี่ dataset
        class_names = get_class_names(dataset_path)
        print("Found classes:", class_names)
        
        # โหลดโมเดล
        model = load_model(model_path)
        print("Model loaded successfully")
        
        # ตรวจสอบว่าจำนวนคลาสตรงกับโมเดล
        num_model_classes = model.output_shape[1]
        if len(class_names) != num_model_classes:
            print(f"Warning: Number of classes in dataset ({len(class_names)}) "
                  f"does not match model's expected classes ({num_model_classes})")
        
        # ทดสอบทำนายภาพ
        if os.path.exists(test_image_path):
            predicted_class, confidence = predict_pattern(model, test_image_path, class_names)
            print(f"Predicted pattern: {predicted_class} with {confidence:.2%} confidence")
        else:
            print(f"Test image not found at {test_image_path}")
        return predicted_class, confidence
            
    except Exception as e:
        print(f"Error: {e}")

# ตัวอย่างการใช้งาน
if __name__ == "__main__":
    # กำหนดพารามิเตอร์
    dataset_path = 'dataset'
    model_path = 'candlestick_pattern_recognition.keras'
    test_image_path = 'images/BAM.png'  # เปลี่ยนเป็น path ของภาพที่ต้องการทดสอบ
    
    try:
        # ดึงชื่อคลาสจากไดเร็กทอรี่ dataset
        class_names = get_class_names(dataset_path)
        print("Found classes:", class_names)
        
        # โหลดโมเดล
        model = load_model(model_path)
        print("Model loaded successfully")
        
        # ตรวจสอบว่าจำนวนคลาสตรงกับโมเดล
        num_model_classes = model.output_shape[1]
        if len(class_names) != num_model_classes:
            print(f"Warning: Number of classes in dataset ({len(class_names)}) "
                  f"does not match model's expected classes ({num_model_classes})")
        
        # ทดสอบทำนายภาพ
        if os.path.exists(test_image_path):
            predicted_class, confidence = predict_pattern(model, test_image_path, class_names)
            print(f"Predicted pattern: {predicted_class} with {confidence:.2%} confidence")
        else:
            print(f"Test image not found at {test_image_path}")
            
    except Exception as e:
        print(f"Error: {e}")

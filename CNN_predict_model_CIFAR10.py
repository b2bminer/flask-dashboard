from tensorflow.keras.models import load_model
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.preprocessing import image
import matplotlib.pyplot as plt
import numpy as np

(in_train, out_train), (in_test, out_test) = cifar10.load_data()

# โหลดโมเดล
model = load_model('cifar10_model.keras')

# ตัวอย่างรูปภาพ (ต้องปรับขนาดและ normalize ให้เหมือนตอนฝึก)
img = in_test[20]  # ใช้ข้อมูลทดสอบเป็นตัวอย่าง (หรือโหลดรูปใหม่)
img = np.expand_dims(img, axis=0)  # เพิ่ม batch dimension -> (1, 32, 32, 3)

# ทำนาย
predictions = model.predict(img)
predicted_class = np.argmax(predictions, axis=1)

# แปลงเลขคลาสเป็นชื่อ (CIFAR-10 classes)
class_names = ['airplane', 'automobile', 'bird', 'cat', 'deer', 
               'dog', 'frog', 'horse', 'ship', 'truck']

plt.figure(figsize=(5, 5)) # กำหนดขนาดของ figure
plt.title(f"Predicted: {class_names[predicted_class[0]]}")
plt.imshow(in_test[20]) # ใช้รูปภาพเดียวกับที่ใช้ทำนาย
plt.axis('off') # ปิดแสดงแกน
plt.savefig('prediction_model_CIFAR10.png')
plt.show()

print("Predicted class:", class_names[predicted_class[0]])

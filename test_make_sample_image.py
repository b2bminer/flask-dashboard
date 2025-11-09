import numpy as np
from PIL import Image, ImageEnhance
import os
def augment_single_image(image_path, output_dir, num_variations=200):
    img = Image.open(image_path)
    os.makedirs(output_dir, exist_ok=True)
    
    for i in range(num_variations):
        # สร้างการเปลี่ยนแปลงแบบสุ่ม
        enhancer = ImageEnhance.Brightness(img)
        img_var = enhancer.enhance(np.random.uniform(0.7, 1.3))
        
        enhancer = ImageEnhance.Contrast(img_var)
        img_var = enhancer.enhance(np.random.uniform(0.7, 1.3))
        
        # หมุนและพลิกภาพ
        angle = np.random.uniform(-40, 40)
        img_var = img_var.rotate(angle)
        
        if np.random.rand() > 0.5:
            img_var = img_var.transpose(Image.FLIP_LEFT_RIGHT)
        
        # บันทึกภาพใหม่
        img_var.save(os.path.join(output_dir, f'variation_{i}.png'))

# ใช้งาน
augment_single_image(
    'dataset/harmonic/img400.png',
    'dataset/harmonic_augmented',
    num_variations=200)

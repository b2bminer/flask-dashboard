import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import threading

device_index = 2  # Stereo Mix (Realtek Audio)
output_filename = "system_audio.wav"

# ดึงข้อมูลอุปกรณ์
device_info = sd.query_devices(device_index)
sample_rate = int(device_info['default_samplerate'])
channels = device_info['max_input_channels']

print(f"🎧 Using device: {device_info['name']}")
print("เริ่มบันทึกเสียงจากลำโพง...")
print("กด Enter เพื่อหยุดบันทึก\n")

frames = []
stop_flag = False

def input_listener():
    global stop_flag
    input()  # กด Enter เพื่อหยุด
    stop_flag = True

listener = threading.Thread(target=input_listener)
listener.start()

with sd.InputStream(device=device_index, channels=channels, samplerate=sample_rate, dtype='float32') as stream:
    while not stop_flag:
        data, _ = stream.read(1024)
        frames.append(data)

# รวม buffer เป็น array
recording = np.concatenate(frames, axis=0)

# บันทึกไฟล์
write(output_filename, sample_rate, recording)

print(f"\n✅ บันทึกสำเร็จ: {output_filename}")

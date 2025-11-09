import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import talib

DATA_DIR = "D:/python_prog/Flask/Odoo/data"

def get_stock_data(symbol, tf, from_ts=None, to_ts=None):
    # โหลดไฟล์ข้อมูลตาม timeframe
    file_map = {
        '15m': f"{DATA_DIR}/{symbol.split('.')[0]}_15m.csv",
        '1h': f"{DATA_DIR}/{symbol.split('.')[0]}_60m.csv",
        'D': f"{DATA_DIR}/{symbol.split('.')[0]}_1d.csv",
        'W': f"{DATA_DIR}/{symbol.split('.')[0]}_1w.csv",
        'M': f"{DATA_DIR}/{symbol.split('.')[0]}_1M.csv"
    }
    
    if tf not in file_map:
        return None
    
    try:
        df = pd.read_csv(file_map[tf])
    except FileNotFoundError:
        return None

    # ประมวลผลคอลัมน์เวลา
    if tf == 'D':
        df['time'] = pd.to_datetime(df['date'])
    else:
        df['time'] = pd.to_datetime(df['time'])

    # กรองข้อมูลตามช่วงเวลาที่ระบุ
    if from_ts and to_ts:
        from_dt = pd.to_datetime(from_ts, unit='s')
        to_dt = pd.to_datetime(to_ts, unit='s')
        df = df[(df['time'] >= from_dt) & (df['time'] <= to_dt)]

    # คำนวณ EMA
    df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()

    # แปลงเวลาเป็น Unix timestamp
    df['time'] = (df['time'] + pd.Timedelta(hours=7)).astype(np.int64) // 10**9

    # เรียงลำดับข้อมูลตามเวลา
    df = df.sort_values('time')
    
    return df

def fetch_stock_data(symbol):
    stock_data = get_stock_data(symbol, 'D' )
    if stock_data is None:
        print("ไม่สามารถโหลดข้อมูลหุ้นได้ ", ticker)
        return None, "ไม่สามารถโหลดข้อมูลหุ้นได้"

    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.get_level_values(0)
    df = stock_data
    df.sort_values('time', inplace=True)
    df['RSI'] = talib.RSI(df['close'])
    df['MACD'], df['MACD_signal'], _ = talib.MACD(df['close'])
    return df

# โหลดข้อมูล (ตัวอย่าง: ราคาปิด)
symbol = "AOT"
look_back = 60
data = fetch_stock_data(symbol)
print(data.columns)
prices = data['close'].values.reshape(-1, 1)

# ปรับสเกลข้อมูลให้อยู่ในช่วง [0, 1]
scaler = MinMaxScaler()
scaled_prices = scaler.fit_transform(prices)

# สร้างชุดข้อมูลสำหรับ LSTM (X = ข้อมูลย้อนหลัง 60 วัน, y = ราคาวันถัดไป)
def create_dataset(data, look_back=60):
    X, y = [], []
    for i in range(len(data)-look_back-1):
        X.append(data[i:(i+look_back), 0])  # ข้อมูลจาก t-look_back ถึง t
        y.append(data[i + look_back + 1, 0])  # ราคาใน t+1 (ล่วงหน้า 1 วัน)
    return np.array(X), np.array(y)

X, y = create_dataset(scaled_prices)
X = np.reshape(X, (X.shape[0], X.shape[1], 1))  # Reshape สำหรับ LSTM [samples, timesteps, features]



from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# สร้างโมเดล
model = Sequential()
model.add(LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)))  # LSTM ชั้นแรก
model.add(Dropout(0.2))  # ป้องกัน Overfitting
model.add(LSTM(50))  # LSTM ชั้นที่สอง
model.add(Dense(1))  # Output Layer

model.compile(optimizer='adam', loss='mean_squared_error')

# ฝึกโมเดล (ใช้ 20% ของข้อมูลเป็น Validation Set)
history = model.fit(X, y, epochs=50, batch_size=32, validation_split=0.2)


from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ทำนายราคา
y_pred = model.predict(X)

# ปรับสเกลกลับเป็นราคาจริง
y_true = scaler.inverse_transform(y.reshape(-1, 1))
y_pred = scaler.inverse_transform(y_pred)

# คำนวณ RMSE
rmse = np.sqrt(mean_squared_error(y_true, y_pred))
print(f"RMSE All: {rmse}")


import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pandas import to_datetime

# แปลงคอลัมน์ 'Date' เป็น datetime
data['date'] = pd.to_datetime(data['date'])  # หากคอลัมน์วันที่ชื่ออื่นให้เปลี่ยนตามนั้น
dates = data['date'].values[look_back+1:]    # เลือกวันที่ตั้งแต่ look_back+1 เป็นต้นไป
print('dates: ', dates)
print('len(data): ', len(data))
print('len(dates): ', len(dates))

# เลือกเฉพาะ 10 วันล่าสุด (ปรับ last_10_days ตามต้องการ)
last_10_days = -10  

# Actual Price (ตัดวันแรกออก เพราะไม่มีข้อมูลทำนายก่อนหน้า)
y_true_last10 = y_true[last_10_days:]  

# Predicted Price (ต้องจับคู่กับวันถัดไป)
y_pred_last10 = y_pred[last_10_days:]  

# วันที่สำหรับแกน X (เริ่มจากวันแรกที่ทำนายได้)
dates_last10 = dates[look_back+1:][last_10_days:]  # dates[look_back+1:] เพราะผลลัพธ์เริ่มที่ t+1

# วันที่สำหรับ Actual Price (t)
actual_dates = dates_last10  # 23/06/2025 ถึง 04/07/2025

# วันที่สำหรับ Predicted Price (t+1)
pred_dates = dates_last10[1:]  # 24/06/2025 ถึง 04/07/2025
pred_dates = np.append(pred_dates, np.datetime64('2025-07-05'))  # เพิ่มวันที่ 05/07/2025

rmse = np.sqrt(mean_squared_error(y_true_last10[1:], y_pred_last10[:-1]))
print(f"RMSE last10: {rmse:.4f}")

print('dates_last10: ', dates_last10)
print("Actual:", y_true_last10)
print("Predicted:", y_pred_last10)

# สร้างกราฟ
plt.figure(figsize=(12, 6))

# Actual Price (แสดงทุกวันที่มีข้อมูล)
plt.plot(actual_dates, y_true_last10, label='Actual Price', color='blue', marker='o')

# Predicted Price (แสดงสำหรับวันถัดไป)
plt.plot(pred_dates, y_pred_last10, label='Predicted (t+1)', color='red', linestyle='--', marker='x')

# ตั้งค่าแกน X
ax = plt.gca()
ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

plt.title('1-Day Ahead Stock Price Prediction (Including 2025-07-05)')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
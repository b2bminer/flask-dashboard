import numpy as np
import pandas as pd
import talib
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

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

symbol = "AOT"
look_back = 60
data = fetch_stock_data(symbol)
data['date'] = pd.to_datetime(data['date'])
data = data.set_index('date')

# เพิ่ม Features
data['MA_5'] = data['close'].rolling(5).mean()
data['RSI_14'] = talib.RSI(data['close'], timeperiod=14)
data['MACD'], _, _ = talib.MACD(data['close'])
data = data.dropna()
prices = data['close'].values.reshape(-1, 1)

# ปรับสเกลข้อมูล
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(prices)

# สร้างชุดข้อมูลสำหรับ LSTM (พยากรณ์ t+1)
look_back = 60
X, y = [], []
for i in range(look_back, len(scaled_data)-1):
    X.append(scaled_data[i-look_back:i, 0])  # ใช้เฉพาะคอลัมน์ close
    y.append(scaled_data[i+1, 0])           # ราคาในวันถัดไป
X, y = np.array(X).reshape(-1, look_back, 1), np.array(y)   # reshape ให้ถูกต้อง
#X, y = np.array(X), np.array(y)

# แบ่งข้อมูล Train/Test (แบ่งตามเวลา)
train_size = int(0.8 * len(X))
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]
test_dates = data.index[train_size+look_back+1:]  # วันที่ของ Test Set

# สร้างโมเดล
model = Sequential([
    LSTM(128, return_sequences=True, input_shape=(look_back, X.shape[2])),
    Dropout(0.3),
    LSTM(64),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')

# ฝึกโมเดล
history = model.fit(X_train, y_train, epochs=50, batch_size=32, 
                    validation_data=(X_test, y_test), verbose=1)

# ทำนายผล
y_pred = model.predict(X_test)

# ปรับสเกลกลับ
# วิธีที่ถูกต้องและง่ายกว่า
y_test_actual = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
y_pred_actual = scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()

# แสดงผลลัพธ์ (เฉพาะ 10 วันล่าสุด)
# แสดงผลรวมถึงการทำนายวันถัดไป
plt.figure(figsize=(15,6))

# Actual Price (วันที่ t+1)
plt.plot(test_dates[-10:], y_test_actual[-10:], 'b-o', label='Actual Price (t+1)')

# Predicted Price (ทำนายสำหรับ t+1)
plt.plot(test_dates[-10:], y_pred_actual[-10:], 'r--x', label='Predicted Price (t+1)')

# เพิ่มจุดทำนายล่วงหน้าสุดท้าย (ถ้ามี)
#if len(test_dates) > len(y_pred_actual):
#    last_pred_date = test_dates[-1] + pd.Timedelta(days=1)
#    plt.plot(last_pred_date, y_pred_actual[-1], 'ro', markersize=8, label='Next Day Prediction')

last_pred_date = test_dates[-1] + pd.Timedelta(days=1)
plt.plot(last_pred_date, y_pred_actual[-1], 'ro', markersize=8, label='Next Day Prediction')

# ปรับรูปแบบแกน X
ax = plt.gca()
ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.xticks(rotation=45)

plt.title('1-Day Ahead Stock Price Prediction (After Improvements)')
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()








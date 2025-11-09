import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import talib
from datetime import timedelta
import io
import os
import base64
import mplfinance as mpf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

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

def prepare_stock_image(symbol):
    df = fetch_stock_data(symbol)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df.columns = df.columns.str.lower()
    os.makedirs("candlestick_images/unknown", exist_ok=True)
    # วนลูปสร้างภาพจากหน้าต่าง rolling 20 วัน
    window_size = 20
    for i in range(len(df) - window_size):
        print('len(df):',len(df),' i:',i)
        window_df = df.iloc[i:i+window_size][['open', 'high', 'low', 'close', 'volume']]
        #window_df = df.iloc[i:i+window_size][['open', 'high', 'low', 'close', 'volume']]
        filename = f"candlestick_images/unknown/img_{i:03d}.png"
        mpf.plot(window_df, type='candle', style='charles', savefig=filename)    

def predict_pattern():
    # โหลดโมเดล CNN ที่ฝึกไว้แล้ว
    model = load_model('model_candlestick_pattern.h5')

    # label mapping
    label_map = {0: 'consolidation', 1: 'expansion', 2: 'retracement'}

    # ตรวจจับ pattern ของแต่ละภาพ
    img_dir = 'candlestick_images/unknown'

    for img_name in os.listdir(img_dir):
        img_path = os.path.join(img_dir, img_name)
        
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img) / 255.
        img_array = np.expand_dims(img_array, axis=0)

        prediction = model.predict(img_array)
        label_idx = np.argmax(prediction)
        pattern = label_map[label_idx]

        print(f'{img_name} → {pattern}')


symbol = "AOT"
#prepare_stock_image(symbol)
predict_pattern()

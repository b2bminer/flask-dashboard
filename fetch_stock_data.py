import numpy as np
import pandas as pd
import talib
from datetime import timedelta
import io
import os
import base64

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

def fetch_stock_data(symbol, tf="D"):
    stock_data = get_stock_data(symbol, tf )
    if stock_data is None:
        print("ไม่สามารถโหลดข้อมูลหุ้นได้ ", ticker)
        return None, "ไม่สามารถโหลดข้อมูลหุ้นได้"

    stock_data.set_index('time')
    stock_data['time'] = pd.to_datetime(stock_data['time'], unit='s')  # แปลงจาก Unix timestamp
    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.get_level_values(0)

    df = stock_data
    df.sort_values('time', inplace=True)
    df['RSI'] = talib.RSI(df['close'])
    df['MACD'], df['MACD_signal'], _ = talib.MACD(df['close'])
    df['vol_ma20'] = df["volume"].rolling(20).mean()
    return df, None



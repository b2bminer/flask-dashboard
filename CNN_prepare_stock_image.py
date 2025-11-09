import mplfinance as mpf
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import os
from datetime import datetime

from fetch_stock_data import get_stock_data, fetch_stock_data

# สร้างโฟลเดอร์เก็บข้อมูล
os.makedirs('dataset/bullish_engulfing', exist_ok=True)
os.makedirs('dataset/bearish_engulfing', exist_ok=True)
os.makedirs('dataset/hammer', exist_ok=True)
os.makedirs('dataset/harmonic', exist_ok=True)
os.makedirs('images', exist_ok=True)
# เพิ่มโฟลเดอร์สำหรับรูปแบบอื่นๆ ตามต้องการ

def generate_candlestick_image(data, filename):
    """สร้างกราฟแท่งเทียนและบันทึกเป็นภาพ"""
    mpf.plot(data, type='candle', style='charles', 
            savefig=filename, axisoff=True, closefig=True,
            figsize=(2.24, 2.24))  # ขนาด 224x224 พิกเซล

def prepare_stock_image(symbol, folder_name=None, file_name=None, single_image='Y', end_date=None):
    try:
        df,error = fetch_stock_data(symbol)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df.columns = df.columns.str.lower()

        if end_date is not None:
            end_date = pd.to_datetime(end_date)
            df = df[df.index <= end_date]

        created_files = []
        if single_image.upper() == 'Y':
            # โหมดสร้างภาพเดียว (30 แท่งสุดท้าย)
            last_30 = df.iloc[-30:][['open', 'high', 'low', 'close', 'volume']]
            #print('last_30')
            #print(last_30)
            #pattern_type = np.random.choice(['bullish_engulfing', 'bearish_engulfing', 'hammer', 'harmonic'])
            #pattern_type = "harmonic"
            filename = f'{folder_name}/{file_name}'     
            generate_candlestick_image(last_30, filename)
            created_files.append(filename)
        else:
            # วนลูปสร้างภาพจากหน้าต่าง rolling 30 วัน
            window_size = 30
            for i in range(len(df) - window_size):
                #print('len(df):',len(df),' i:',i)
                window_df = df.iloc[i:i+window_size][['open', 'high', 'low', 'close', 'volume']]
                pattern_type = np.random.choice(['bullish_engulfing', 'bearish_engulfing', 'hammer', 'harmonic'])
                #pattern_type = "harmonic"
                filename = f'{folder_name}/{pattern_type}/img_{i}.png'
                generate_candlestick_image(window_df, filename)
    except Exception as e:
        print(f"Error in inverse transform: {str(e)}")
        return None, f"Inverse transform error: {str(e)}"

try:
    symbol = "AOT"
    prepare_stock_image(symbol, folder_name='dataset/harmonic', file_name='img.png', single_image='Y', end_date='2025-01-14')
    #prepare_stock_image(symbol, folder_name='dataset', single_image='N', end_date='2025-07-18')
except Exception as e:
    print(f"Error: {str(e)}")

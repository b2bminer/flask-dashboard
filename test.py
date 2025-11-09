import pandas as pd
import matplotlib.pyplot as plt
from fetch_stock_data import fetch_stock_data

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import numpy as np
import io
import base64
from scipy.signal import argrelextrema
from localminima import detect_overbought_oversold, detect_bullish_bearish_divergence, detect_double_bottom, detect_gartley

from settrade_v2 import Investor
from settrade_v2.errors import SettradeError
from datetime import datetime, timedelta, timezone
import os
import time
from pathlib import Path
DATA_DIR = "data"

def portfolio():
    try:
        try:
            # ✅ ห่อการสร้าง Investor ด้วย try แยก
            investor = Investor(
                app_id="YW7O3YypvXgnkJhY",
                app_secret="DqYDrYEW0V/xwnO+BMaNOLmpU0dR84M9JPY2r4zNDL4=",
                broker_id="023",
                app_code="ALGO_EQ",
                is_auto_queue=False
            )
        except SettradeError as e:
            # ✅ ตรวจจับ error จาก SETTRADE โดยตรง
            err_msg = str(e)
            if "U-591" in err_msg or "System Unavailable" in err_msg:
                print("⚠️ SETTRADE API ไม่พร้อมใช้งาน (System Unavailable) — ข้ามการเชื่อมต่อ")
                return render_template(
                    'portfolio.html',
                    account_info=None,
                    portfolio_data=None,
                    set100=set100
                )
            else:
                raise  # ถ้าเป็น error อื่น ให้โยนต่อ
        
        # ✅ ถ้าเชื่อมต่อสำเร็จค่อยเรียกข้อมูลต่อ
        equity = investor.Equity(account_no="602068305")
        account_info = equity.get_account_info()
        print(f"account_info: {account_info}")
        portfolio_data = equity.get_portfolios()
        print('portfolio_data')
        print(portfolio_data)

    except Exception as e:
        print(f"\nเกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}")

def downloadStockdata():
    ticker = "AAV"
    if ticker:
        set100x = ticker
    investor = Investor(
        app_id="YW7O3YypvXgnkJhY",
        app_secret="DqYDrYEW0V/xwnO+BMaNOLmpU0dR84M9JPY2r4zNDL4=",
        broker_id="023",
        app_code="ALGO_EQ",
        is_auto_queue=False
    )

    mkt_data = investor.MarketData()
    current_date = datetime.now()
    start_date = (current_date - timedelta(days=365)).strftime("%Y-%m-%dT00:00")
    end_date = current_date.strftime("%Y-%m-%dT23:59")

    print(f"Downloading data from {start_date} to {end_date}")
    timeframes = [
        {'interval': '15m', 'days_limit': 30},  # 15 นาที เก็บได้ 7 วัน
        {'interval': '60m', 'days_limit': 60},    # 1 ชั่วโมง เก็บได้ 30 วัน
        {'interval': '1d', 'days_limit': 365*2},   # 1 วัน เก็บได้ 1 ปี
        {'interval': '1w', 'days_limit': 365*2}, # 1 สัปดาห์ เก็บได้ 2 ปี
        {'interval': '1M', 'days_limit': 365*5}  # 1 เดือน เก็บได้ 5 ปี
    ]

    results = {}

    for symbol in set100x:
        print(f"\n=== Downloading for {symbol} ===")
        results[symbol] = {}

        for tf in timeframes:
            try:
                print(f"  Processing {tf['interval']} timeframe...")
                res = mkt_data.get_candlestick(
                    symbol=symbol,
                    interval=tf['interval'],
                    limit=1000,
                    normalized=True,
                    start=start_date,
                    end=end_date
                )

                df = pd.DataFrame({
                    'time': pd.to_datetime(res['time'], unit='s'),
                    'open': res['open'],
                    'high': res['high'],
                    'low': res['low'],
                    'close': res['close'],
                    'volume': res['volume'],
                    'value': res['value']
                })

                df = df.sort_values('time')
                df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')

                if tf['interval'] in ['1d', '1w', '1M']:
                    df['date'] = df['time'].dt.date

                filename = f"{DATA_DIR}/{symbol}_{tf['interval']}.csv"
                df.to_csv(filename, index=False)
                print(f"  Saved {len(df)} rows to {filename}")

                results[symbol][tf['interval']] = {
                    'status': 'success',
                    'records': len(df),
                    'filename': filename
                }
                time.sleep(1)  # 1 วินาที หรือเปลี่ยนตามที่เหมาะสม

            except Exception as e:
                print(f"  Error: {str(e)}")
                results[symbol][tf['interval']] = {
                    'status': 'error',
                    'message': str(e)
                }

    # ทดสอบเรียกข้อมูลตลาด
    mkt_data = investor.MarketData()
    try:
        res = mkt_data.get_symbol_list()  # ดึงรายชื่อหุ้นทั้งหมด
        print("✅ API Active, user is valid")
        print(f"Symbols available: {len(res)}")
    except Exception as e:
        print("❌ API Error:", str(e))

    return jsonify({
        'overall_status': 'completed',
        'symbols': results
    })


if __name__ == "__main__":
    ticker = "AAV"

    #chart77, rsistatus, signal = detect_overbought_oversold(SYMBOL=ticker)
    #chart77, rsistatus, signal = detect_bullish_bearish_divergence(SYMBOL=ticker, confirm=False)
    #print(chart77)
    #chart79, defect_status, defect_signal = detect_double_bottom(SYMBOL=ticker)
    #detect_gartley(SYMBOL=ticker)
    #print(f"{defect_status}, {defect_signal}")

    portfolio()
    downloadStockdata()

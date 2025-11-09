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
from datetime import datetime, timedelta

SYMBOL = "AOT"
#END_DATE = '2025-07-30'
# ---- เลือกช่วงเวลา ----
start_date = "2024-01-01"
end_date   = None #"2025-08-05"

def prepare_stock_data(SYMBOL: str, tf: str = "D", end_date: str = None):
    df, error = fetch_stock_data(SYMBOL, tf=tf)
    if error:
        return None, error
    # แปลงคอลัมน์ date ให้เป็น datetime
    df['date'] = pd.to_datetime(df['time'])  
    #df['date'] = pd.to_datetime(df['date'])
    if end_date:
        end_date = pd.to_datetime(end_date)
        df = df[df['date'] <= end_date].copy()
        print(f"Columns: {df.columns.tolist()}")
    #print(f"last_date:{df['time'].iloc[-1]}")
    return df, None


def detect_overbought_oversold(SYMBOL: str):

    df, error = prepare_stock_data(SYMBOL, tf="D", end_date=end_date)

    # ---- Global Minimum ----
    global_min_value = df['RSI'].min()
    global_min_row = df.loc[df['RSI'].idxmin()]

    print("=== Global Minimum RSI ===")
    print("ค่า RSI ต่ำสุด:", global_min_value)
    print("ข้อมูลแถวที่ RSI ต่ำสุด:")
    print(global_min_row[['date', 'RSI']])
    print("\n")

    # ---- Local Minima ----
    order = 3  # ใช้ดูรอบข้าง 3 แท่งเทียน (ปรับได้ตามต้องการ)
    local_min_idx = argrelextrema(df['RSI'].values, np.less, order=order)[0]

    df['RSI_local_min'] = np.nan
    df.loc[local_min_idx, 'RSI_local_min'] = df.loc[local_min_idx, 'RSI']

    print("=== Local Minima RSI ===")
    print(df.dropna(subset=['RSI_local_min'])[['date', 'RSI_local_min']])

    df_check = df.loc[(df['date'] == "2024-10-25") |
                    (df['date'] == "2024-10-31") |
                    (df['date'] == "2024-11-07")]

    print(df_check)

    # ====== กำหนดกลยุทธ์ ======
    df['signal'] = None
    rsistatus = None
    signal = None
    for idx in local_min_idx:
        if df.loc[idx, 'RSI'] < 30:
            # ตรวจสอบว่าแท่งถัดไป RSI สูงกว่า local minima
            if idx + 1 < len(df) and df.loc[idx + 1, 'RSI'] > df.loc[idx, 'RSI']:
                df.loc[idx + 1, 'signal'] = 'BUY'  # ใส่สัญญาณที่แท่งถัดไป

    # Sell: เมื่อ RSI > 70 (จุดขายง่าย ๆ)
    #df.loc[df['RSI'] > 70, 'signal'] = 'SELL'
    sell_idx = df.index[df['RSI'] > 70]
    if not sell_idx.empty:
        df.loc[sell_idx, 'signal'] = 'SELL'

    # --- ตรวจสอบ RSI สถานะจากแท่งสุดท้าย ---
    last_rsi = df['RSI'].iloc[-1]
    if last_rsi > 70:
        rsistatus = "Overbought"
    elif last_rsi < 30:
        rsistatus = "Oversold"
    else:
        rsistatus = "-"

    # --- ตรวจสอบสัญญาณแท่งสุดท้าย ---
    last_idx = df.index[-1]
    last_signal = df.loc[last_idx, 'signal']

    if last_signal == "BUY":
        signal = "Buy"
    elif last_signal == "SELL":
        signal = "Sell"
    else:
        signal = "-"

    print("=== แสดงสัญญาณ ===")
    print(df[['date','close','RSI','RSI_local_min','signal']].dropna(subset=['signal']))
    if end_date:
        df_plot = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    else:
        df_plot = df[(df['date'] >= start_date)]

    # ====== กราฟราคา ======
    plt.figure(figsize=(14,8))

    plt.subplot(2,1,1)
    plt.plot(df_plot['date'], df_plot['close'], label='Close Price', color='blue')

    # Plot จุด BUY
    buy_signals = df_plot[df_plot['signal'] == 'BUY']
    plt.scatter(buy_signals['date'], buy_signals['close'], marker='^', color='green', s=120, label='BUY')

    # Plot จุด SELL
    sell_signals = df_plot[df_plot['signal'] == 'SELL']
    plt.scatter(sell_signals['date'], sell_signals['close'], marker='v', color='red', s=120, label='SELL')

    plt.title("Price with Buy/Sell Signals")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)

    # ====== กราฟ RSI ======
    plt.subplot(2,1,2)
    plt.plot(df_plot['date'], df_plot['RSI'], label='RSI', color='purple')

    # Plot เส้น Overbought/Oversold
    plt.axhline(70, color='red', linestyle='--', alpha=0.7)
    plt.axhline(30, color='green', linestyle='--', alpha=0.7)

    # Plot จุด Local Minima
    local_min_points = df_plot.dropna(subset=['RSI_local_min'])
    plt.scatter(local_min_points['date'], local_min_points['RSI_local_min'],
                color='orange', marker='o', s=100, label='Local Minima')

    plt.title("Overbought/Oversold with EMA20 & RSI")
    plt.xlabel("Date")
    plt.ylabel("RSI")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()

    # --- Plot by MPL Finance ---
    df_plot['date'] = pd.to_datetime(df_plot['date'], errors='coerce')   # แปลงเป็น datetime
    df_plot = df_plot.dropna(subset=['date'])                            # ลบแถวที่แปลงไม่ได้
    df_plot = df_plot.set_index('date')                                  # ตั้งเป็น DatetimeIndex
    df_plot = df_plot.sort_index()                                       # เรียงตามเวลา
    print(df_plot.head)
    print(df_plot.info())
    apds = [mpf.make_addplot(df_plot['ema20'], color='blue'),
            mpf.make_addplot(df_plot['RSI'], panel=1, color='purple', ylabel="RSI"),
            mpf.make_addplot([30]*len(df_plot), color='green', linestyle='--', panel=1),
            mpf.make_addplot([70]*len(df_plot), color='red', linestyle='--', panel=1),
            ]

    scatter_rsi_min = pd.Series(np.nan, index=df_plot.index)
    scatter_rsi_min.loc[df_plot['RSI_local_min'].notna()] = df_plot['RSI_local_min']
    # สร้าง addplot สำหรับ scatter จุด Local Minima
    apds_local_min = mpf.make_addplot(
        scatter_rsi_min,
        type='scatter',
        markersize=100,
        marker='o',
        color='orange',
        panel=1  # panel ของ RSI
    )
    scatter_buy = pd.Series(np.nan, index=df_plot.index)
    scatter_buy.loc[df_plot['signal'] == 'BUY'] = df_plot['close'] * 0.95
    # สร้าง addplot สำหรับ BUY signals
    apds_buy = mpf.make_addplot(
        scatter_buy,
        type='scatter',
        markersize=60,
        marker='^',
        color='green',
        panel=0  # candlestick panel
    )
    scatter_sell = pd.Series(np.nan, index=df_plot.index)
    scatter_sell.loc[df_plot['signal'] == 'SELL'] = df_plot['close'] * 1.05
    apds_sell = mpf.make_addplot(
        scatter_sell,
        type='scatter',
        markersize=60,
        marker='v',
        color='red',
        panel=0  # candlestick panel
    )

    # รวมกับ Local Minima และ addplot อื่น ๆ
    apds_all = apds + [apds_local_min, apds_buy, apds_sell]

    # --- Plot ---
    s = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.size':10})

    fig, axes = mpf.plot(
        df_plot,
        type='candle',
        style=s,
        addplot=apds_all,
        volume=True,
        title=f'{SYMBOL} - Overbought/Oversold with EMA20 & RSI',
        panel_ratios=(2,1),
        figratio=(14,8),
        figscale=1.2,
        xrotation=20,      # ให้แกน X เอียง 20°
        returnfig=True
    )

    print("จำนวน axes:", len(axes))
    for i, ax in enumerate(axes):
        print(f"axes[{i}] → {ax}")

    def find_rsi_panel(axes):
        """
        หาว่า RSI อยู่ที่ axes index ไหน
        คืนค่าเป็น index ถ้าเจอ, -1 ถ้าไม่เจอ
        """
        for i, ax in enumerate(axes):
            # 1) ถ้ามี ylabel เป็น RSI
            label = ax.get_ylabel()
            if label and "RSI" in label.upper():
                return i

            # 2) ถ้าช่วง y-limit อยู่ใน [0,100] → มักจะเป็น RSI
            ymin, ymax = ax.get_ylim()
            if 0 <= ymin <= 20 and 80 <= ymax <= 100:
                return i
        
        return -1  # ไม่เจอ

    rsi_index = find_rsi_panel(axes)
    print("rsi_index:", rsi_index)
    if rsi_index != -1:
        ax_rsi = axes[rsi_index]
        x_min, x_max = ax_rsi.get_xlim()  # หาค่าขอบแกน X
        ax_rsi.text(x_min, 70, 'Overbought (70)',
            color='red', ha='left', va='bottom', fontsize=9)
        ax_rsi.text(x_min, 30, 'Oversold (30)',
            color='green', ha='left', va='top', fontsize=9)

    # --- แก้ tick ให้แสดงทุก 7 วัน ---
    ax_main = axes[0]   # แกนหลัก (candlestick)
    dates = df_plot.index

    # เลือกทุก 7 วัน
    xticks = range(0, len(dates), 15)
    ax_main.set_xticks(xticks)
    ax_main.set_xticklabels([d.strftime('%Y-%m-%d') for d in dates[::15]], rotation=20)

    #plt.show()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64, rsistatus, signal


def detect_bullish_bearish_divergence(SYMBOL: str, confirm: bool = True):

    df, error = prepare_stock_data(SYMBOL, tf="D", end_date=end_date)
    if df is None or df.empty:
        return None, None, df

    # ====== หา local minima / maxima ======
    order = 3
    df['RSI_local_min'] = np.nan
    df['RSI_local_max'] = np.nan
    df['Price_local_min'] = np.nan
    df['Price_local_max'] = np.nan

    min_idx_rsi = argrelextrema(df['RSI'].values, np.less, order=order)[0]
    min_idx_price = argrelextrema(df['close'].values, np.less, order=order)[0]
    df.loc[min_idx_rsi, 'RSI_local_min'] = df.loc[min_idx_rsi, 'RSI']
    df.loc[min_idx_price, 'Price_local_min'] = df.loc[min_idx_price, 'close']

    max_idx_rsi = argrelextrema(df['RSI'].values, np.greater, order=order)[0]
    max_idx_price = argrelextrema(df['close'].values, np.greater, order=order)[0]
    df.loc[max_idx_rsi, 'RSI_local_max'] = df.loc[max_idx_rsi, 'RSI']
    df.loc[max_idx_price, 'Price_local_max'] = df.loc[max_idx_price, 'close']

    # ====== หา Divergence ======
    df['divergence'] = None
    df['signal'] = None  # เพิ่มคอลัมน์ signal
    bullish_pairs = []
    bearish_pairs = []

    # Bullish Divergence (ใช้ local minima)
    for i in range(1, len(min_idx_price)):
        p1, p2 = min_idx_price[i-1], min_idx_price[i]
        if df.loc[p2, 'close'] < df.loc[p1, 'close'] and df.loc[p2, 'RSI'] > df.loc[p1, 'RSI']:
            df.loc[p2, 'divergence'] = 'Bullish'
            df.loc[p2, 'signal'] = 'Buy'
            bullish_pairs.append((p1, p2))
            print("=== Bullish Divergence Pair Detected ===")
            print(f"Index: {p1} ({df.loc[p1, 'date']}) → {p2} ({df.loc[p2, 'date']})")
            print(f"Price: {df.loc[p1, 'close']} → {df.loc[p2, 'close']}")
            print(f"RSI  : {df.loc[p1, 'RSI']} → {df.loc[p2, 'RSI']}")
            print("-" * 50)

    # Bearish Divergence (ใช้ local maxima)
    for i in range(1, len(max_idx_price)):
        p1, p2 = max_idx_price[i-1], max_idx_price[i]
        if df.loc[p2, 'close'] > df.loc[p1, 'close'] and df.loc[p2, 'RSI'] < df.loc[p1, 'RSI']:
            df.loc[p2, 'divergence'] = 'Bearish'
            df.loc[p2, 'signal'] = 'Sell'
            bearish_pairs.append((p1, p2))
            print("=== Bearish Divergence Pair Detected ===")
            print(f"Index: {p1} ({df.loc[p1, 'date']}) → {p2} ({df.loc[p2, 'date']})")
            print(f"Price: {df.loc[p1, 'close']} → {df.loc[p2, 'close']}")
            print(f"RSI  : {df.loc[p1, 'RSI']} → {df.loc[p2, 'RSI']}")
            print("-" * 50)

    # ====== ตรวจแท่งล่าสุดด้วย (บังคับเช็ค row สุดท้าย) ======
    last_idx = len(df) - 1

    # Bearish Divergence ล่าสุด
    if len(max_idx_price) > 0:
        last_max = max_idx_price[-1]
        if df.loc[last_idx, 'close'] > df.loc[last_max, 'close'] and df.loc[last_idx, 'RSI'] < df.loc[last_max, 'RSI']:
            df.loc[last_idx, 'divergence'] = 'Bearish'
            df.loc[last_idx, 'signal'] = 'Sell'
            bearish_pairs.append((last_max, last_idx))

    # Bullish Divergence ล่าสุด
    if len(min_idx_price) > 0:
        last_min = min_idx_price[-1]
        if df.loc[last_idx, 'close'] < df.loc[last_min, 'close'] and df.loc[last_idx, 'RSI'] > df.loc[last_min, 'RSI']:
            df.loc[last_idx, 'divergence'] = 'Bullish'
            df.loc[last_idx, 'signal'] = 'Buy'
            bullish_pairs.append((last_min, last_idx))

    # ====== หาสัญญาณล่าสุด ======
    print("checking data: df date=2025-07-30")
    print(df[df['date'] == "2025-07-30"])

    rsistatus = None
    signal = None
    last_divergence = None
    last_date = None

    if confirm:
        # ✅ รอ confirm → ต้องเอา divergence ล่าสุด + คอนเฟิร์มวันถัดไป
        last_idx = df['divergence'].last_valid_index()
        if last_idx is not None:
            # divergence ต้องไม่ใช่แท่งสุดท้าย → ต้องมีแท่งถัดไปให้ confirm
            if last_idx + 1 < len(df):
                confirm_row = df.iloc[last_idx + 1]
                last_divergence = df.loc[last_idx, 'divergence']
                last_signal = df.loc[last_idx, 'signal']
                last_date = confirm_row['date']   # ใช้วันถัดไปเป็นวันยืนยัน
                rsistatus = last_divergence
                signal = last_signal
            else:
                # ถ้า divergence อยู่ที่แท่งล่าสุด → ยังไม่มีวันยืนยัน
                last_divergence = None
                rsistatus = "-"
                signal = "-"
                last_date = None
    else:
        # ✅ ไม่รอ confirm → ใช้ divergence ล่าสุดที่ไม่เป็น NaN
        valid_div = df[df['divergence'].notna()]
        if not valid_div.empty:
            last_row = valid_div.iloc[-1]
            last_divergence = last_row['divergence']
            last_signal = last_row['signal']
            last_date = last_row['date']
            rsistatus = last_divergence
            signal = last_signal
            # 🔎 ตรวจอายุสัญญาณ (3 วัน)
            import pandas as pd
            last_date_ts = pd.to_datetime(last_date)
            last_df_date = pd.to_datetime(df.iloc[-1]['date'])
            if (last_df_date - last_date_ts).days > 3:
                last_divergence = None
                rsistatus = "-"
                signal = "-"
                last_date = None

    # หลัง loop ตรวจ divergence เสร็จ
    df['divergence_confirmed'] = None
    df['signal_confirmed'] = None

    if confirm:
        # หาแถวที่มี divergence แล้วเขียนค่าไปยังแถวถัดไป (pos+1) หากมีแถวถัดไป
        # ใช้ index ของ dataframe เองเพื่อไม่ต้องแม็ช timestamp ที่อาจต่างกัน
        for idx_label in df[df['divergence'].notna()].index:
            # แปลง index label เป็นตำแหน่งเชิงตัวเลข (pos)
            pos = df.index.get_loc(idx_label)
            if pos + 1 < len(df):
                next_label = df.index[pos + 1]
                # ใช้ .at เพื่อ assign อย่างปลอดภัย (หลีกเลี่ยง SettingWithCopyWarning)
                df.at[next_label, 'divergence_confirmed'] = df.at[idx_label, 'divergence']
                df.at[next_label, 'signal_confirmed'] = df.at[idx_label, 'signal']
    else:
        # ถ้าไม่ confirm ให้แสดงสัญญาณตามเดิม
        df['divergence_confirmed'] = df['divergence']
        df['signal_confirmed'] = df['signal']

    print(f"last_date: {last_date}")
    print(f"last_divergence: {last_divergence}")
    print(f"rsistatus: {rsistatus}, signal: {signal}")

    if end_date:
        df_plot = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    else:
        df_plot = df[(df['date'] >= start_date)]
    #df_plot = df_plot.copy()
    df_plot = df_plot.set_index('time')
    # ถ้า confirm=True ให้ใช้คอลัมน์ confirmed ในการ plot (เลื่อนเป็นวันถัดไป),
    # ถ้า confirm=False ให้ใช้ divergence ปกติ
    if confirm:
        df_plot['divergence_plot'] = df_plot['divergence_confirmed']
        df_plot['signal_plot'] = df_plot['signal_confirmed']
    else:
        df_plot['divergence_plot'] = df_plot['divergence']
        df_plot['signal_plot'] = df_plot['signal']

    print("checking data: df_plot date=2025-07-30")
    print(df_plot[df_plot['date'] == "2025-07-30"])
    print("checking data: df_plot date=2025-07-31")
    print(df_plot[df_plot['date'] == "2025-07-31"])
    print("divergence rows (orig):")
    print(df[df['divergence'].notna()][['date','divergence','signal']].tail(10))
    print("divergence_confirmed rows:")
    print(df[df['divergence_confirmed'].notna()][['date','divergence_confirmed','signal_confirmed']].tail(10))
    print("df.index tail:", df.index[-5:])
    print("df['date'] tail:", df['date'].tail(5))

    # --- Plot by MPL Finance ---
    #df_plot['date'] = pd.to_datetime(df_plot['date'], errors='coerce')   # แปลงเป็น datetime
    #df_plot = df_plot.dropna(subset=['date'])                            # ลบแถวที่แปลงไม่ได้
    #df_plot = df_plot.set_index('date')                                  # ตั้งเป็น DatetimeIndex
    df_plot = df_plot.sort_index()                                       # เรียงตามเวลา
    print(df_plot.head)
    print(df_plot.info())

    # ====== สร้างเส้น Divergence สำหรับ alines ======
    price_divergence_lines = []  # เส้นในพาเนลราคา
    
    # Bullish Divergence Lines
    for p1, p2 in bullish_pairs:
        if p1 < len(df_plot) and p2 < len(df_plot):
            # เส้นในพาเนลราคา (สีเขียว)
            price_line = [
                (df_plot.index[p1], df_plot.iloc[p1]['close'] - (df_plot['close'].max() - df_plot['close'].min()) * 0.02),
                (df_plot.index[p2], df_plot.iloc[p2]['close'] - (df_plot['close'].max() - df_plot['close'].min()) * 0.02)
            ]
            price_divergence_lines.append(price_line)                        
            print(f"Bullish Line - Price: {df_plot.index[p1]} → {df_plot.index[p2]}")
            print(f"Bullish Line - RSI: {df_plot.iloc[p1]['RSI']:.1f} → {df_plot.iloc[p2]['RSI']:.1f}")

    # Bearish Divergence Lines
    for p1, p2 in bearish_pairs:
        if p1 < len(df_plot) and p2 < len(df_plot):
            # เส้นในพาเนลราคา (สีแดง)
            price_line = [
                (df_plot.index[p1], df_plot.iloc[p1]['close'] + (df_plot['close'].max() - df_plot['close'].min()) * 0.02),
                (df_plot.index[p2], df_plot.iloc[p2]['close'] + (df_plot['close'].max() - df_plot['close'].min()) * 0.02)
            ]
            price_divergence_lines.append(price_line)                        
            print(f"Bearish Line - Price: {df_plot.index[p1]} → {df_plot.index[p2]}")
            print(f"Bearish Line - RSI: {df_plot.iloc[p1]['RSI']:.1f} → {df_plot.iloc[p2]['RSI']:.1f}")

    df_plot['Price_local_min_offset'] = df_plot['Price_local_min'] * 0.995   # ต่ำกว่าแท่งเทียนเล็กน้อย (เช่น -0.5%)
    df_plot['Price_local_max_offset'] = df_plot['Price_local_max'] * 1.005   # สูงกว่าแท่งเทียนเล็กน้อย (เช่น +0.5%)
    apds = [mpf.make_addplot(df_plot['ema20'], color='blue'),
            mpf.make_addplot(df_plot['RSI'], panel=1, color='purple', ylabel="RSI"),
            mpf.make_addplot([30]*len(df_plot), color='green', linestyle='--', panel=1),
            mpf.make_addplot([70]*len(df_plot), color='red', linestyle='--', panel=1),
            mpf.make_addplot(df_plot['Price_local_min_offset'], type='scatter', color='green', marker='^', markersize=60, panel=0),
            mpf.make_addplot(df_plot['Price_local_max_offset'], type='scatter', color='red', marker='v', markersize=60, panel=0),
            ]

    scatter_rsi_min = pd.Series(np.nan, index=df_plot.index)
    scatter_rsi_min.loc[df_plot['RSI_local_min'].notna()] = df_plot['RSI_local_min']
    # สร้าง addplot สำหรับ scatter จุด Local Minima
    apds_local_min = mpf.make_addplot(
        scatter_rsi_min,
        type='scatter',
        markersize=50,
        marker='o',
        color='green',
        panel=1  # panel ของ RSI
    )
    scatter_rsi_max = pd.Series(np.nan, index=df_plot.index)
    scatter_rsi_max.loc[df_plot['RSI_local_max'].notna()] = df_plot['RSI_local_max']
    # สร้าง addplot สำหรับ scatter จุด Local Maxima
    apds_local_max = mpf.make_addplot(
        scatter_rsi_max,
        type='scatter',
        markersize=50,
        marker='o',
        color='red',
        panel=1  # panel ของ RSI
    )
    # Bullish Divergence
    scatter_bullish = pd.Series(np.nan, index=df_plot.index)
    scatter_bullish_rsi   = pd.Series(np.nan, index=df_plot.index)
    mask_bullish = df_plot['divergence_plot'] == 'Bullish'
    print("Query Bullish mask rows:")
    print(df_plot.loc[mask_bullish, ['close','divergence_plot','signal_plot']])
    if mask_bullish.any():
        scatter_bullish.loc[mask_bullish] = df_plot['close'] * 0.95
        apds_bullish = mpf.make_addplot(
            scatter_bullish,
            type='scatter',
            markersize=90,
            marker='^',
            color='green',
            panel=0
        )
        scatter_bullish_rsi.loc[mask_bullish] = df_plot['RSI'] - 1   # ลดลงนิดเพื่อไม่ทับเส้น
        apds_bullish_rsi = mpf.make_addplot(
            scatter_bullish_rsi,
            type='scatter',
            markersize=120,
            marker='^',
            color='green',
            panel=1   # <<== วางใน RSI panel
        )
    else:
        apds_bullish = None   # ถ้าไม่มี ไม่ต้องสร้าง
        apds_bullish_rsi   = None
    # Bearish Divergence
    scatter_bearish = pd.Series(np.nan, index=df_plot.index)
    scatter_bearish_rsi = pd.Series(np.nan, index=df_plot.index)
    mask_bearish = df_plot['divergence_plot'] == 'Bearish'
    print("Query Bearish mask rows:")
    print(df_plot.loc[mask_bearish, ['close','divergence_plot','signal_plot']])
    if mask_bearish.any():
        scatter_bearish.loc[mask_bearish] = df_plot['close'] * 1.05
        apds_bearish = mpf.make_addplot(
            scatter_bearish,
            type='scatter',
            markersize=60,
            marker='v',
            color='red',
            panel=0
        )
        scatter_bearish_rsi.loc[mask_bearish] = df_plot['RSI'] + 1
        apds_bearish_rsi = mpf.make_addplot(
            scatter_bearish_rsi,
            type='scatter',
            markersize=120,
            marker='v',
            color='red',
            panel=1
        )
    else:
        apds_bearish = None
        apds_bearish_rsi = None

    # รวมกับ Local Minima และ addplot อื่น ๆ
    apds_all = apds + [apds_local_min, apds_local_max]
    if apds_bullish is not None:
        apds_all.append(apds_bullish)
        apds_all.append(apds_bullish_rsi)
    if apds_bearish is not None:
        apds_all.append(apds_bearish)
        apds_all.append(apds_bearish_rsi)

    s = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.size':10})

    fig, axes = mpf.plot(
        df_plot,
        type='candle',
        style=s,
        addplot=apds_all,
        #alines=dict(alines=divergence_lines, colors=['green', 'red'], linewidths=2, alpha=0.7),
        alines=dict(
            alines=price_divergence_lines,
            colors=['green'] * len(bullish_pairs) + ['red'] * len(bearish_pairs),
            linewidths=2, linestyle="--",
            alpha=0.7
        ),
        volume=True,
        title=f'{SYMBOL} - Bullish/Bearish Divergence with EMA20 & RSI',
        panel_ratios=(2,1),
        figratio=(14,8),
        figscale=1.2,
        xrotation=20,      # ให้แกน X เอียง 20°
        returnfig=True
    )
    #สร้าง status line แสดงวันที่และราคา
    add_mouse_hover_info(fig, axes, df_plot, fontname="Tahoma")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.show()
    plt.close(fig)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    print(f"detect_bullish_bearish {rsistatus}, {signal}")

    # ====== Plot by Matplotlib======
    fig, (ax_price, ax_rsi) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                        gridspec_kw={'height_ratios': [2, 1]})
    ax_price.plot(df_plot.index, df_plot['close'], label="Close Price", color="blue")
    ax_price.plot(df_plot['date'], df_plot['Price_local_min'], color='green', marker='o', label='Price Min')
    ax_price.plot(df_plot['date'], df_plot['Price_local_max'], color='red', marker='o', label='Price Max')
    offset_price = (df_plot['close'].max() - df_plot['close'].min()) * 0.03  # offset 2% ของ range ราคา

    # Bullish Divergence → วาง marker ใต้แท่งเทียนเล็กน้อย
    bullish_points = df_plot[df_plot['divergence_plot'] == 'Bullish']
    ax_price.scatter(bullish_points['date'], bullish_points['close'] - offset_price,
                    color='lime', marker='^', s=120, label='Bullish Div')

    # Bearish Divergence → วาง marker เหนือแท่งเทียนเล็กน้อย
    bearish_points = df_plot[df_plot['divergence_plot'] == 'Bearish']
    ax_price.scatter(bearish_points['date'], bearish_points['close'] + offset_price,
                    color='red', marker='v', s=120, label='Bearish Div')

    # วาด RSI
    ax_rsi.plot(df_plot.index, df_plot['RSI'], label="RSI", color="blue")
    ax_rsi.axhline(70, color="red", linestyle="--", alpha=0.5)
    ax_rsi.axhline(30, color="green", linestyle="--", alpha=0.5)
    ax_rsi.plot(df_plot['date'], df_plot['RSI_local_min'], color='green', marker='o', label='RSI Min')
    ax_rsi.plot(df_plot['date'], df_plot['RSI_local_max'], color='red', marker='o', label='RSI Max')
    offset_rsi = (df_plot['RSI'].max() - df_plot['RSI'].min()) * 0.03  # offset 2% ของ range ราคา
    ax_rsi.scatter(bullish_points['date'], bullish_points['RSI'] - offset_rsi,
                color='lime', marker='^', s=80, label='Bullish Div')
    ax_rsi.scatter(bearish_points['date'], bearish_points['RSI'] + offset_rsi,
                color='red', marker='v', s=80, label='Bearish Div')

    ax_price.set_title(f'{SYMBOL} - Bullish/Bearish Divergence Signals')

    # -----------------------------
    # ฟังก์ชันวาดเส้น divergence จาก pairs
    # -----------------------------
    def plot_divergence_pairs(df, pairs, ax_price, ax_rsi, color="green"):
        for (p1, p2) in pairs:
            # ✅ ใช้ iloc เพราะ p1, p2 เป็นตำแหน่ง (integer index)
            t1, t2 = df.iloc[p1]['date'], df.iloc[p2]['date']
            price1, price2 = df.iloc[p1]['close'], df.iloc[p2]['close']
            rsi1, rsi2 = df.iloc[p1]['RSI'], df.iloc[p2]['RSI']

            # วาดเส้นที่กราฟราคา
            ax_price.plot([t1, t2], [price1, price2], color=color, linestyle="--", linewidth=1.5)

            # วาดเส้นที่กราฟ RSI
            ax_rsi.plot([t1, t2], [rsi1, rsi2], color=color, linestyle="--", linewidth=1.5)

            # ✅ Debug print
            print(f"Divergence line ({color}): {t1} → {t2} | Price {price1:.2f}→{price2:.2f}, RSI {rsi1:.2f}→{rsi2:.2f}")

    plot_divergence_pairs(df_plot, bullish_pairs, ax_price, ax_rsi, color="green")
    plot_divergence_pairs(df_plot, bearish_pairs, ax_price, ax_rsi, color="red")

    plt.legend(); plt.grid(True)   
    plt.tight_layout(); plt.show()

    # แสดง divergence ที่เจอ
    print(df_plot.dropna(subset=['divergence'])[['date','close','RSI','divergence']])

    return img_base64, rsistatus, signal

def detect_double_bottom(SYMBOL: str):
    df, error = prepare_stock_data(SYMBOL, tf="D", end_date=end_date)
    # หา local minima และ maxima
    df['min'] = df['close'][(df['close'].shift(1) > df['close']) & (df['close'].shift(-1) > df['close'])]
    df['max'] = df['close'][(df['close'].shift(1) < df['close']) & (df['close'].shift(-1) < df['close'])]

    # ดึง index ที่เป็น local minima
    min_idx = argrelextrema(df['close'].values, np.less, order=5)[0]

    signals = []
    recent_signals = []  # สำหรับเก็บสัญญาณล่าสุด
    threshold = 0.03  # 3% tolerance
    current_date = datetime.now()
    three_days_ago = current_date - timedelta(days=3)

    for i in range(len(min_idx) - 1):
        first = min_idx[i]
        second = min_idx[i + 1]

        # ตรวจสอบว่าระดับใกล้กันหรือไม่
        if abs(df['close'].iloc[first] - df['close'].iloc[second]) / df['close'].iloc[first] < threshold:
            # หา neckline = ค่าสูงสุดระหว่าง first และ second
            neckline = df['close'].iloc[first:second].max()

            # ถ้ามีจุดที่ราคาทะลุ neckline หลังจาก second → สัญญาณซื้อ
            future_prices = df['close'].iloc[second:]
            breakout = future_prices[future_prices > neckline]

            if not breakout.empty:
                breakout_index = breakout.index[0]
                breakout_date = df['date'].iloc[breakout_index]
                signal_data = {
                    "first_bottom": df['date'].iloc[first],
                    "second_bottom": df['date'].iloc[second],
                    "neckline": neckline,
                    "breakout_date": breakout_date,
                    "breakout_price": breakout.iloc[0]
                }
                signals.append(signal_data)
                if isinstance(breakout_date, (datetime, pd.Timestamp)):
                    if breakout_date >= three_days_ago:
                        recent_signals.append(signal_data)

    if recent_signals:  # ถ้าพบสัญญาณ double bottom ภายใน 3 วันที่ผ่านมา
        defect_status = "Double Bottom"
        defect_signal = "Buy"
        print(f"พบสัญญาณ Double Bottom ล่าสุด {len(recent_signals)} รายการ")
    else:  # ถ้าไม่พบสัญญาณ
        defect_status = ""
        defect_signal = None
        print("ไม่พบสัญญาณ Double Bottom")
    if signals:
        signals_df = pd.DataFrame(signals)
        print("สัญญาณ Double Bottom ทั้งหมด:")
        print(signals_df)        
        # แสดงสัญญาณล่าสุดแยกต่างหาก
        if recent_signals:
            recent_signals_df = pd.DataFrame(recent_signals)
            print("\nสัญญาณล่าสุด (ภายใน 3 วันที่ผ่านมา):")
            print(recent_signals_df)

    # Plot ตัวอย่าง
    plt.figure(figsize=(14,8))
    plt.plot(df['date'], df['close'], label="Close Price")

    buy_label_added = False
    for sig in signals:
        plt.scatter(sig['first_bottom'], df.loc[df['date'] == sig['first_bottom'], 'close'], color='red', marker='v')
        plt.scatter(sig['second_bottom'], df.loc[df['date'] == sig['second_bottom'], 'close'], color='red', marker='v')
        plt.axhline(sig['neckline'], color='green', linestyle='--')
        buy_label = 'Buy Signal' if not buy_label_added else ""
        plt.scatter(sig['breakout_date'], sig['breakout_price'], color='green', marker='^', s=120, label=buy_label, zorder=5)
        if not buy_label_added and buy_label:
            buy_label_added = True

    plt.title(f'{SYMBOL} - Double Bottom Detection')
    plt.legend()
    #buf = io.BytesIO()
    #plt.savefig(buf, format="png", bbox_inches="tight")
    #buf.seek(0)
    plt.show()
    #img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), height_ratios=[2, 1], sharex=True)
    ax1.plot(df['date'], df['close'], label="Close Price", linewidth=1.5)
    buy_label_added = False
    for sig in signals:
        ax1.scatter(sig['first_bottom'], df.loc[df['date'] == sig['first_bottom'], 'close'], color='red', marker='v')
        ax1.scatter(sig['second_bottom'], df.loc[df['date'] == sig['second_bottom'], 'close'], color='red', marker='v')
        ax1.axhline(sig['neckline'], color='green', linestyle='--', alpha=0.7)
        buy_label = 'Buy Signal' if not buy_label_added else ""
        ax1.scatter(sig['breakout_date'], sig['breakout_price'], color='green', marker='^', s=120, label=buy_label, zorder=5)
        if not buy_label_added and buy_label:
            buy_label_added = True
        ax1.set_title(f'{SYMBOL} - Double Bottom Detection')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
    # ตั้งค่าแกนราคาด้านขวา
    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position("right")
    ax1.set_ylabel('Price')
    ax1.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    plt.setp(ax1.get_xticklabels(), visible=False)

    ax2.plot(df['date'], df['RSI'], label="RSI", color='purple', linewidth=1.5)
    ax2.axhline(70, color='red', linestyle='--', alpha=0.7, label='Overbought')
    ax2.axhline(30, color='green', linestyle='--', alpha=0.7, label='Oversold')
    ax2.fill_between(df['date'], 70, 100, color='red', alpha=0.1)
    ax2.fill_between(df['date'], 0, 30, color='green', alpha=0.1)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('RSI')
    ax2.set_ylim(0, 100)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    buf = io.BytesIO()
    plt.show()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)
    plt.close(fig)  # ปิดกราฟเฉพาะ figure นี้
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()

    return img_base64, defect_status, defect_signal


def detect_gartley(SYMBOL: str , order=5, tol=0.05):
    df, error = prepare_stock_data(SYMBOL, tf="D", end_date=end_date)
    # หา local extrema
    idx_max = argrelextrema(df['close'].values, np.greater, order=order)[0]
    idx_min = argrelextrema(df['close'].values, np.less, order=order)[0]
    pivots = sorted(np.concatenate([idx_max, idx_min]))

    patterns = []

    # loop หาแพทเทิร์น 5 จุด (X,A,B,C,D)
    for i in range(len(pivots) - 4):
        X, A, B, C, D = pivots[i:i+5]
        x, a, b, c, d = df['close'].iloc[[X, A, B, C, D]]

        # สัดส่วน Fibonacci
        ab = abs((b - a) / (x - a))      # AB retrace XA
        bc = abs((c - b) / (a - b))      # BC retrace AB
        cd = abs((d - c) / (b - c))      # CD extend BC
        ad = abs((d - x) / (a - x))      # AD retrace XA

        # เงื่อนไข Gartley
        if (0.61-tol <= ab <= 0.61+tol and
            0.38 <= bc <= 0.886 and
            1.27 <= cd <= 1.618 and
            0.786-tol <= ad <= 0.786+tol):
            
            patterns.append({
                "X": X, "A": A, "B": B, "C": C, "D": D,
                "prices": [x, a, b, c, d]
            })
    
    return patterns

def plot_gartley(df, patterns):
    plt.figure(figsize=(14,7))
    plt.plot(df['date'], df['close'], label="Close Price", color="black")

    for pat in patterns:
        points = [pat["X"], pat["A"], pat["B"], pat["C"], pat["D"]]
        prices = pat["prices"]

        # วาดเส้นเชื่อม X-A-B-C-D
        plt.plot(df['date'].iloc[points], prices, marker='o', color="blue", linewidth=2)
        for label, idx, price in zip(["X","A","B","C","D"], points, prices):
            plt.text(df['date'].iloc[idx], price, label, fontsize=12, color="red")

    plt.title("Harmonic Gartley Pattern Detection")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.show()



########################################################################
def prepare_divergence_df(df: pd.DataFrame, min_idx_price, max_idx_price, confirm=False):
    #print("prepare divergence")
    # ====== หา Divergence ======
    df['divergence'] = None
    #df['signal'] = None  # เพิ่มคอลัมน์ signal
    bullish_pairs = []
    bearish_pairs = []

    # Bullish Divergence (ใช้ local minima)
    for i in range(1, len(min_idx_price)):
        p1, p2 = min_idx_price[i-1], min_idx_price[i]
        if df.loc[p2, 'close'] < df.loc[p1, 'close'] and df.loc[p2, 'RSI'] > df.loc[p1, 'RSI']:
            df.loc[p2, 'divergence'] = 'Bullish'
            df.loc[p2, 'signal'] = 'Buy'
            bullish_pairs.append((p1, p2))
            #print("=== Bullish Divergence Pair Detected ===")
            #print(f"Index: {p1} ({df.loc[p1, 'date']}) → {p2} ({df.loc[p2, 'date']})")
            #print(f"Price: {df.loc[p1, 'close']} → {df.loc[p2, 'close']}")
            #print(f"RSI  : {df.loc[p1, 'RSI']} → {df.loc[p2, 'RSI']}")
            #print("-" * 50)

    # Bearish Divergence (ใช้ local maxima)
    for i in range(1, len(max_idx_price)):
        p1, p2 = max_idx_price[i-1], max_idx_price[i]
        if df.loc[p2, 'close'] > df.loc[p1, 'close'] and df.loc[p2, 'RSI'] < df.loc[p1, 'RSI']:
            df.loc[p2, 'divergence'] = 'Bearish'
            df.loc[p2, 'signal'] = 'Sell'
            bearish_pairs.append((p1, p2))
            #print("=== Bearish Divergence Pair Detected ===")
            #print(f"Index: {p1} ({df.loc[p1, 'date']}) → {p2} ({df.loc[p2, 'date']})")
            #print(f"Price: {df.loc[p1, 'close']} → {df.loc[p2, 'close']}")
            #print(f"RSI  : {df.loc[p1, 'RSI']} → {df.loc[p2, 'RSI']}")
            #print("-" * 50)

    # ====== ตรวจแท่งล่าสุดด้วย (บังคับเช็ค row สุดท้าย) ======
    last_idx = len(df) - 1

    # Bearish Divergence ล่าสุด
    if len(max_idx_price) > 0:
        last_max = max_idx_price[-1]
        if df.loc[last_idx, 'close'] > df.loc[last_max, 'close'] and df.loc[last_idx, 'RSI'] < df.loc[last_max, 'RSI']:
            df.loc[last_idx, 'divergence'] = 'Bearish'
            df.loc[last_idx, 'signal'] = 'Sell'
            bearish_pairs.append((last_max, last_idx))

    # Bullish Divergence ล่าสุด
    if len(min_idx_price) > 0:
        last_min = min_idx_price[-1]
        if df.loc[last_idx, 'close'] < df.loc[last_min, 'close'] and df.loc[last_idx, 'RSI'] > df.loc[last_min, 'RSI']:
            df.loc[last_idx, 'divergence'] = 'Bullish'
            df.loc[last_idx, 'signal'] = 'Buy'
            bullish_pairs.append((last_min, last_idx))

    # ====== หาสัญญาณล่าสุด ======
    #print("checking data: df date=2025-07-30")
    #print(df[df['date'] == "2025-07-30"])

    rsistatus = None
    signal = None
    last_divergence = None
    last_date = None

    if confirm:
        # ✅ รอ confirm → ต้องเอา divergence ล่าสุด + คอนเฟิร์มวันถัดไป
        last_idx = df['divergence'].last_valid_index()
        if last_idx is not None:
            # divergence ต้องไม่ใช่แท่งสุดท้าย → ต้องมีแท่งถัดไปให้ confirm
            if last_idx + 1 < len(df):
                confirm_row = df.iloc[last_idx + 1]
                last_divergence = df.loc[last_idx, 'divergence']
                last_signal = df.loc[last_idx, 'signal']
                last_date = confirm_row['date']   # ใช้วันถัดไปเป็นวันยืนยัน
                rsistatus = last_divergence
                signal = last_signal
            else:
                # ถ้า divergence อยู่ที่แท่งล่าสุด → ยังไม่มีวันยืนยัน
                last_divergence = None
                rsistatus = "-"
                signal = "-"
                last_date = None
    else:
        # ✅ ไม่รอ confirm → ใช้ divergence ล่าสุดที่ไม่เป็น NaN
        valid_div = df[df['divergence'].notna()]
        if not valid_div.empty:
            last_row = valid_div.iloc[-1]
            last_divergence = last_row['divergence']
            last_signal = last_row['signal']
            last_date = last_row['date']
            rsistatus = last_divergence
            signal = last_signal
            # 🔎 ตรวจอายุสัญญาณ (3 วัน)
            last_date_ts = pd.to_datetime(last_date)
            last_df_date = pd.to_datetime(df.iloc[-1]['date'])
            if (last_df_date - last_date_ts).days > 3:
                last_divergence = None
                rsistatus = "-"
                signal = "-"
                last_date = None

    # หลัง loop ตรวจ divergence เสร็จ
    df['divergence_confirmed'] = None
    df['signal_confirmed'] = None

    if confirm:
        # หาแถวที่มี divergence แล้วเขียนค่าไปยังแถวถัดไป (pos+1) หากมีแถวถัดไป
        # ใช้ index ของ dataframe เองเพื่อไม่ต้องแม็ช timestamp ที่อาจต่างกัน
        for idx_label in df[df['divergence'].notna()].index:
            # แปลง index label เป็นตำแหน่งเชิงตัวเลข (pos)
            pos = df.index.get_loc(idx_label)
            if pos + 1 < len(df):
                next_label = df.index[pos + 1]
                # ใช้ .at เพื่อ assign อย่างปลอดภัย (หลีกเลี่ยง SettingWithCopyWarning)
                df.at[next_label, 'divergence_confirmed'] = df.at[idx_label, 'divergence']
                df.at[next_label, 'signal_confirmed'] = df.at[idx_label, 'signal']
    else:
        # ถ้าไม่ confirm ให้แสดงสัญญาณตามเดิม
        df['divergence_confirmed'] = df['divergence']
        df['signal_confirmed'] = df['signal']

    #print(f"last_date: {last_date}")
    #print(f"last_divergence: {last_divergence}")
    #print(f"rsistatus: {rsistatus}, signal: {signal}")

    if confirm:
        df['divergence_plot'] = df['divergence_confirmed']
        df['signal_plot'] = df['signal_confirmed']
    else:
        df['divergence_plot'] = df['divergence']
        df['signal_plot'] = df['signal']

    #print("checking data: df_plot date=2025-07-30")
    #print(df_plot[df_plot['date'] == "2025-07-30"])
    #print("checking data: df_plot date=2025-07-31")
    #print(df_plot[df_plot['date'] == "2025-07-31"])
    #print("divergence rows (orig):")
    #print(df[df['divergence'].notna()][['date','divergence','signal']].tail(10))
    #print("divergence_confirmed rows:")
    #print(df[df['divergence_confirmed'].notna()][['date','divergence_confirmed','signal_confirmed']].tail(10))
    #print("df.index tail:", df.index[-5:])
    #print("5 แถวแรกของ df :")
    #print(df.head(5))
    #print("5 แถวสุดท้ายของ df :")
    #print(df.tail(5))

    return df, rsistatus, signal

def detect_combined_signals(SYMBOL: str, tf: str="D",confirm=False):
    df, error = prepare_stock_data(SYMBOL, tf, end_date=end_date)
    if error or df is None or df.empty:
        print("❌ ไม่สามารถดึงข้อมูลหุ้นได้")
        return None, {"RSI": {"status": "-", "signal": "-"}, 
                     "Divergence": {"status": "-", "signal": "-"}, 
                     "DoubleBottom": {"status": "-", "signal": "-"}}
    #print(df.info())
    # ---- Global Minimum ----
    global_min_value = df['RSI'].min()
    global_max_value = df['RSI'].max()
    global_min_row = df.loc[df['RSI'].idxmin()]
    global_max_row = df.loc[df['RSI'].idxmax()]
    #print("=== Global Minimum RSI ===")
    #print("ค่า RSI ต่ำสุด:", global_min_value)
    #print("ค่า RSI max:", global_max_value)
    #print("ข้อมูลแถวที่ RSI ต่ำสุด:")
    #print(global_min_row[['date', 'RSI']])
    #print("ข้อมูลแถวที่ RSI max:")
    #print(global_max_row[['date', 'RSI']])
    #print("\n")
    order = 3  # ใช้ดูรอบข้าง 3 แท่งเทียน (ปรับได้ตามต้องการ)
    min_idx_rsi = argrelextrema(df['RSI'].values, np.less, order=order)[0]
    df['RSI_local_min'] = np.nan
    df.loc[min_idx_rsi, 'RSI_local_min'] = df.loc[min_idx_rsi, 'RSI']
    #print("min_idx_rsi")
    #print(min_idx_rsi)
    #print(df.loc[min_idx_rsi])
    max_idx_rsi = argrelextrema(df['RSI'].values, np.greater, order=order)[0]
    df['RSI_local_max'] = np.nan
    df.loc[max_idx_rsi, 'RSI_local_max'] = df.loc[max_idx_rsi, 'RSI']
    #print("max_idx_rsi")
    #print(max_idx_rsi)
    #print(df.loc[max_idx_rsi])
    df['Price_local_min'] = np.nan
    df['Price_local_max'] = np.nan
    min_idx_price = argrelextrema(df['close'].values, np.less, order=order)[0]
    df.loc[min_idx_price, 'Price_local_min'] = df.loc[min_idx_price, 'close']
    max_idx_price = argrelextrema(df['close'].values, np.greater, order=order)[0]
    df.loc[max_idx_price, 'Price_local_max'] = df.loc[max_idx_price, 'close']
    #print("max_idx_price")
    #print(max_idx_price)
    #print(df.loc[max_idx_price])

    df['signal'] = None
    rsi_status = None
    signal = None
    # Buy: เมื่อ RSI < 30 และแท่งถัดไป RSI สูงกว่า local minima
    for idx in min_idx_rsi:
        if df.loc[idx, 'RSI'] < 30:
            # ตรวจสอบว่าแท่งถัดไป RSI สูงกว่า local minima
            if idx + 1 < len(df) and df.loc[idx + 1, 'RSI'] > df.loc[idx, 'RSI']:
                df.loc[idx + 1, 'signal'] = 'BUY'  # ใส่สัญญาณที่แท่งถัดไป
    # Sell: เมื่อ RSI > 70 (จุดขายง่าย ๆ)
    #df.loc[df['RSI'] > 70, 'signal'] = 'SELL'
    sell_idx = df.index[df['RSI'] > 70]
    if not sell_idx.empty:
        df.loc[sell_idx, 'signal'] = 'SELL'
    # --- ตรวจสอบ RSI สถานะจากแท่งสุดท้าย ---
    last_rsi = df['RSI'].iloc[-1]
    if last_rsi > 70:
        rsi_status = "Overbought"
    elif last_rsi < 30:
        rsi_status = "Oversold"
    else:
        rsi_status = "-"
    # --- ตรวจสอบสัญญาณแท่งสุดท้าย ---
    last_idx = df.index[-1]
    last_signal = df.loc[last_idx, 'signal']
    if last_signal == "BUY":
        signal = "Buy"
    elif last_signal == "SELL":
        signal = "Sell"
    else:
        signal = "-"
    #print(f"len(df): {len(df)}")
    dates_to_check = [pd.to_datetime("2024-10-25").date(), 
                        pd.to_datetime("2024-10-31").date(), 
                        pd.to_datetime("2025-10-01").date()]
    df_check = df.loc[df['date'].dt.date.isin(dates_to_check)]
    #print(df_check)
    df_check = df.loc[df['signal']=="BUY"]
    #print(df_check)
    df_check = df.loc[df['signal']=="SELL"]
    #print(df_check)
    #print(df[['date','close','RSI','RSI_local_min','signal']].dropna(subset=['signal']).sort_values('date'))
    #print(df[['date','close','RSI','RSI_local_min','signal']].dropna(subset=['RSI_local_min']).sort_values('date'))
    #print(df[['date','close','RSI','RSI_local_max','signal']].dropna(subset=['RSI_local_max']).sort_values('date'))
    #print(df[['date','close','RSI','Price_local_min','signal']].dropna(subset=['Price_local_min']).sort_values('date'))
    #print(df[['date','close','RSI','Price_local_max','signal']].dropna(subset=['Price_local_max']).sort_values('date'))

    df, div_status, div_signal = prepare_divergence_df(df, min_idx_price, max_idx_price, confirm=False)
    #print(df.head(5))

    # ====== สรุปผล ======
    summary = {
        "RSI": {"status": rsi_status, "signal": signal},
        "Divergence": {"status": div_status, "signal": div_signal},
        #"DoubleBottom": {"status": dbl_status, "signal": dbl_signal}
    }

    print(f"✅ สรุปสัญญาณทั้งหมด: {SYMBOL}")
    print(f"RSI → {rsi_status} | {signal}")
    print(f"Divergence → {div_status} | {div_signal}")
    #print(f"Double Bottom → {dbl_status} | {dbl_signal}")

    if end_date:
        df_plot = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    else:
        df_plot = df[(df['date'] >= start_date)]
    df_plot = df_plot.set_index('date') 
    df_plot = df_plot.sort_index()
    oversold = pd.Series(np.nan, index=df_plot.index)
    mask_oversold = df_plot['signal'] == 'BUY'
    if mask_oversold.any():
        oversold.loc[mask_oversold] = df_plot['close'] * 0.9
        apds_oversold = mpf.make_addplot(
            oversold,
            type='scatter',
            markersize=80,
            marker='o',
            color='green',
            label='Oversold',
            panel=0
        )
    else:
        apds_oversold = None   # ถ้าไม่มี ไม่ต้องสร้าง
    overbought = pd.Series(np.nan, index=df_plot.index)
    mask_overbought = df_plot['signal'] == 'SELL'
    if mask_overbought.any():
        overbought.loc[mask_overbought] = df_plot['close'] * 1.05
        apds_overbought = mpf.make_addplot(
            overbought,
            type='scatter',
            markersize=80,
            marker='o',
            color='red',
            label='Overbought',
            panel=0
        )
    else:
        apds_overbought = None   # ถ้าไม่มี ไม่ต้องสร้าง
    bullish = pd.Series(np.nan, index=df_plot.index)
    mask_bullish = df_plot['divergence_plot'] == 'Bullish'
    if mask_bullish.any():
        bullish.loc[mask_bullish] = df_plot['close'] * 0.9
        apds_bullish = mpf.make_addplot(
            bullish,
            type='scatter',
            markersize=80,
            marker='^',
            color='green',
            label='Bullish',
            panel=0
        )
    else:
        apds_bullish = None   # ถ้าไม่มี ไม่ต้องสร้าง
    bearish = pd.Series(np.nan, index=df_plot.index)
    mask_bearish = df_plot['divergence_plot'] == 'Bearish'
    if mask_bearish.any():
        bearish.loc[mask_bearish] = df_plot['close'] * 1.05
        apds_bearish = mpf.make_addplot(
            bearish,
            type='scatter',
            markersize=80,
            marker='v',
            color='red',
            label='Bearish',
            panel=0
        )
    else:
        apds_bearish = None   # ถ้าไม่มี ไม่ต้องสร้าง

    apds = [mpf.make_addplot(df_plot['ema20'], color='blue', label='EMA20'),
            mpf.make_addplot(df_plot['RSI'], panel=1, color='purple', ylabel="RSI"),
            mpf.make_addplot([30]*len(df_plot), color='green', linestyle='--', panel=1),
            mpf.make_addplot([70]*len(df_plot), color='red', linestyle='--', panel=1),
            mpf.make_addplot(df_plot['Price_local_min'], type='scatter', color='orange', marker='o', markersize=50, label='Price Low', panel=0),
            mpf.make_addplot(df_plot['Price_local_max'], type='scatter', color='orange', marker='o', markersize=50, label='Price High', panel=0),
            mpf.make_addplot(df_plot['RSI_local_min'], type='scatter', color='orange', marker='o', markersize=50, label='RSI Low', panel=1),
            mpf.make_addplot(df_plot['RSI_local_max'], type='scatter', color='orange', marker='o', markersize=50, label='RSI High', panel=1),
            ]
    #apds_all = apds + [apds_local_min,apds_local_max]
    apds_all = apds
    if apds_oversold is not None:
        apds_all.append(apds_oversold)
    if apds_overbought is not None:
        apds_all.append(apds_overbought)
    if apds_bullish is not None:
        apds_all.append(apds_bullish)
    if apds_bearish is not None:
        apds_all.append(apds_bearish)
    s = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.size':10})
    fig, axes = mpf.plot(
        df_plot,
        type='candle',
        style=s,
        addplot=apds_all,
        volume=True,
        title=f'{SYMBOL} - {tf}',
        panel_ratios=(2,1),
        figratio=(14,8),
        figscale=1.2,
        xrotation=20,      # ให้แกน X เอียง 20°
        returnfig=True
    )
    def find_rsi_panel(axes):
        for i, ax in enumerate(axes):
            # 1) ถ้ามี ylabel เป็น RSI
            label = ax.get_ylabel()
            if label and "RSI" in label.upper():
                return i

            # 2) ถ้าช่วง y-limit อยู่ใน [0,100] → มักจะเป็น RSI
            ymin, ymax = ax.get_ylim()
            if 0 <= ymin <= 20 and 80 <= ymax <= 100:
                return i
        return -1  # ไม่เจอ
    rsi_index = find_rsi_panel(axes)
    #print("rsi_index:", rsi_index)
    if rsi_index != -1:
        ax_rsi = axes[rsi_index]
        x_min, x_max = ax_rsi.get_xlim()  # หาค่าขอบแกน X
        ax_rsi.text(x_min, 70, 'Overbought (70)',
            color='red', ha='left', va='bottom', fontsize=9)
        ax_rsi.text(x_min, 30, 'Oversold (30)',
            color='green', ha='left', va='top', fontsize=9)
    # --- แก้ tick ให้แสดงทุก 7 วัน ---
    ax_main = axes[0]   # แกนหลัก (candlestick)
    dates = df_plot.index

    # เลือกทุก 7 วัน
    xticks = range(0, len(dates), 15)
    ax_main.set_xticks(xticks)
    ax_main.set_xticklabels([d.strftime('%Y-%m-%d') for d in dates[::15]], rotation=20)
    axes[0].legend(loc='upper left', fontsize=8)
    axes[3].legend(loc='upper left', fontsize=8)

    # สร้าง status text ด้านล่าง
    add_mouse_hover_info(fig, axes, df_plot, fontname="Tahoma")

    plt.tight_layout()
    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.show()
    plt.close()
    return img_base64, summary

########################################################################

# ฟังก์ชันประเมินสัญญาณสุดท้าย
def get_final_trading_signal(summary: dict) -> tuple:
    """
    ประเมินสัญญาณสุดท้ายจากสัญญาณทั้งหมด
    """
    signals = []
    weights = []
    
    # RSI Signals
    if summary["RSI"]["signal"] == "BUY":
        signals.append("BUY")
        weights.append(1)
    elif summary["RSI"]["signal"] == "SELL":
        signals.append("SELL")
        weights.append(1)
    
    # Divergence Signals
    if summary["Divergence"]["signal"] == "Buy":
        signals.append("BUY")
        weights.append(2)  # น้ำหนักมากกว่า
    elif summary["Divergence"]["signal"] == "Sell":
        signals.append("SELL")
        weights.append(2)
    
    # Double Bottom Signals
    #if summary["DoubleBottom"]["signal"] == "Buy":
    #    signals.append("BUY")
    #    weights.append(1.5)
    
    if not signals:
        return "HOLD", "No clear signals"
    
    # นับคะแนน
    buy_score = sum(weights[i] for i, signal in enumerate(signals) if signal == "BUY")
    sell_score = sum(weights[i] for i, signal in enumerate(signals) if signal == "SELL")
    
    if buy_score > sell_score:
        return "BUY", f"Bullish signals (Score: {buy_score:.1f})"
    elif sell_score > buy_score:
        return "SELL", f"Bearish signals (Score: {sell_score:.1f})"
    else:
        return "HOLD", "Mixed signals"

def add_mouse_hover_info(fig, axes, df_plot, fontname="Tahoma"):
    status_text = fig.text(0.5, 0.01, "", ha="center", fontsize=10, color="blue", fontname="Tahoma")
    ax_main = axes[0]

    # ใช้จำนวนแท่งเทียนทั้งหมดเป็นแกน X
    x_vals = np.arange(len(df_plot))

    def on_move(event):
        if event.inaxes == ax_main and event.xdata is not None:
            # แปลงตำแหน่ง X ของเมาส์ให้เป็น index ใกล้เคียงที่สุด
            idx = int(round(event.xdata))
            if 0 <= idx < len(df_plot):
                d_str = df_plot.index[idx].strftime("%Y-%m-%d")
                close_val = df_plot['close'].iloc[idx]
                status_text.set_text(f"วันที่: {d_str} | ราคาปิด: {close_val:.2f}")
                fig.canvas.draw_idle()
        else:
            status_text.set_text("")

    fig.canvas.mpl_connect("motion_notify_event", on_move)

if __name__ == "__main__":

    #img_base64 = detect_overbought_oversold(SYMBOL=SYMBOL)
    #print(img_base64)
    #detect_bullish_bearish_divergence(SYMBOL=SYMBOL)
    #detect_swing_trade_ema(SYMBOL=SYMBOL)

    #img_base64, summary = detect_combined_signals_v2("RCL")
    # ประเมินสัญญาณสุดท้าย
    #print(f"🎯 สัญญาณสุดท้าย: {final_signal}")
    #print(f"📝 เหตุผล: {reason}")
    #print("📊 สรุปสัญญาณ:", summary)
    img_base64, summary = detect_combined_signals (SYMBOL="AAV", tf="1h",confirm=False )
    final_signal, reason = get_final_trading_signal(summary)
    print(f"Final Signal: {final_signal} Reason: {reason}")

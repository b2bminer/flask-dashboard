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

SYMBOL = "AOT"
#END_DATE = '2025-07-30'
# ---- เลือกช่วงเวลา ----
start_date = "2024-01-01"
end_date   =  "2025-08-05"

def prepare_stock_data(SYMBOL: str, tf: str = "D", end_date: str = None):
    df, error = fetch_stock_data(SYMBOL, tf=tf)
    if error:
        return None, error
    # แปลงคอลัมน์ date ให้เป็น datetime
    df['date'] = pd.to_datetime(df['date'])
    if end_date:
        end_date = pd.to_datetime(end_date)
        df = df[df['date'] <= end_date].copy()
        print(f"Columns: {df.columns.tolist()}")
    print(f"last_date:{df['time'].iloc[-1]}")
    return df, None

def detect_latest_bullish_divergence(SYMBOL: str):

    df, error = prepare_stock_data(SYMBOL, tf="D", end_date=end_date)
    latest_ref = None
    latest_divergence = None

    sorted_lows = df.sort_values("date")

    while True:
        # หา RSI จุดต่ำสุด
        ref_idx = sorted_lows['RSI'].idxmin()
        if pd.isna(ref_idx):
            break

        ref_date = sorted_lows.loc[ref_idx, 'date']
        ref_rsi = sorted_lows.loc[ref_idx, 'RSI']
        ref_low = sorted_lows.loc[ref_idx, 'low']

        latest_ref = (ref_date, ref_rsi, ref_low)

        # ข้อมูลหลังจาก reference
        df_after = df[df['date'] > ref_date]

        # ตรวจ Divergence
        signals = df_after[(df_after['low'] < ref_low) & (df_after['RSI'] > ref_rsi)]

        if not signals.empty:
            # เลือก Divergence ล่าสุด (ไม่ใช่ตัวแรก)
            latest_divergence = signals.iloc[-1]
            sorted_lows = sorted_lows[sorted_lows['date'] > ref_date]
        else:
            # ไม่เจอ divergence → หยุด
            break

    # ==== สรุปผล ====
    if latest_ref:
        print(f"RSI Low ล่าสุดที่ยังไม่เกิด Divergence: {latest_ref[0] } | RSI={latest_ref[1]:.2f} | Low={latest_ref[2]}")
    if latest_divergence is not None:
        print(f"เจอสัญญาณ Divergence ล่าสุดที่ {latest_divergence['date'] } | "
              f"Low={latest_divergence['low']:.2f} | RSI={latest_divergence['RSI']:.2f}")
    else:
        print("ยังไม่เกิด Bullish Divergence")

    # ==== Plot ====
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    # Plot ราคา
    ax1.plot(df['date'], df['close'], label="Close Price", color="blue")
    if latest_ref:
        ax1.scatter(latest_ref[0], latest_ref[2], color="red", s=120, label="RSI Low (ref)", zorder=5)
    if latest_divergence is not None:
        ax1.scatter(latest_divergence['date'], latest_divergence['low'], color="green", marker="^", s=150, label="Bullish Divergence", zorder=5)
        ax1.plot([latest_ref[0], latest_divergence['date']], [latest_ref[2], latest_divergence['low']], "g--")  # เส้นเชื่อม
    ax1.legend()
    ax1.set_title("Price with Bullish Divergence")

    # Plot RSI
    ax2.plot(df['date'], df['RSI'], label="RSI", color="purple")
    if latest_ref:
        ax2.axhline(latest_ref[1], color="red", linestyle="--", label="Ref RSI")
    if latest_divergence is not None:
        ax2.scatter(latest_divergence['date'], latest_divergence['RSI'], color="green", marker="^", s=150, label="Bullish Divergence", zorder=5)
        ax2.plot([latest_ref[0], latest_divergence['date']], [latest_ref[1], latest_divergence['RSI']], "g--")  # เส้นเชื่อม
    ax2.legend()
    ax2.set_title("RSI")

    plt.show()

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
        title="Overbought/Oversold with EMA20 & RSI",
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

    # Bullish Divergence (ใช้ local minima)
    for i in range(1, len(min_idx_price)):
        p1, p2 = min_idx_price[i-1], min_idx_price[i]
        if df.loc[p2, 'close'] < df.loc[p1, 'close'] and df.loc[p2, 'RSI'] > df.loc[p1, 'RSI']:
            df.loc[p2, 'divergence'] = 'Bullish'
            df.loc[p2, 'signal'] = 'Buy'

    # Bearish Divergence (ใช้ local maxima)
    for i in range(1, len(max_idx_price)):
        p1, p2 = max_idx_price[i-1], max_idx_price[i]
        if df.loc[p2, 'close'] > df.loc[p1, 'close'] and df.loc[p2, 'RSI'] < df.loc[p1, 'RSI']:
            df.loc[p2, 'divergence'] = 'Bearish'
            df.loc[p2, 'signal'] = 'Sell'

    # ====== ตรวจแท่งล่าสุดด้วย (บังคับเช็ค row สุดท้าย) ======
    last_idx = len(df) - 1

    # Bearish Divergence ล่าสุด
    if len(max_idx_price) > 0:
        last_max = max_idx_price[-1]
        if df.loc[last_idx, 'close'] > df.loc[last_max, 'close'] and df.loc[last_idx, 'RSI'] < df.loc[last_max, 'RSI']:
            df.loc[last_idx, 'divergence'] = 'Bearish'
            df.loc[last_idx, 'signal'] = 'Sell'

    # Bullish Divergence ล่าสุด
    if len(min_idx_price) > 0:
        last_min = min_idx_price[-1]
        if df.loc[last_idx, 'close'] < df.loc[last_min, 'close'] and df.loc[last_idx, 'RSI'] > df.loc[last_min, 'RSI']:
            df.loc[last_idx, 'divergence'] = 'Bullish'
            df.loc[last_idx, 'signal'] = 'Buy'

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
    mask_bullish = df_plot['divergence_plot'] == 'Bullish'
    print("Query Bullish mask rows:")
    print(df_plot.loc[mask_bullish, ['close','divergence_plot','signal_plot']])
    if mask_bullish.any():
        scatter_bullish.loc[mask_bullish] = df_plot['close'] * 0.95
        apds_bullish = mpf.make_addplot(
            scatter_bullish,
            type='scatter',
            markersize=60,
            marker='^',
            color='green',
            panel=0
        )
    else:
        apds_bullish = None   # ถ้าไม่มี ไม่ต้องสร้าง
    # Bearish Divergence
    scatter_bearish = pd.Series(np.nan, index=df_plot.index)
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
    else:
        apds_bearish = None

    # ====== วาดเส้น Divergence ======
    # ตรวจสอบข้อมูล Divergence
    print("=== ตรวจสอบข้อมูล Divergence ===")
    bullish_rows = df_plot[df_plot['divergence_plot'] == 'Bullish']

    print("\nBearish Divergence rows:")
    bearish_rows = df_plot[df_plot['divergence_plot'] == 'Bearish']
    print(bearish_rows[['close', 'RSI', 'divergence_plot']])

    print(f"\nจำนวน Bullish Divergence: {len(bullish_rows)}")
    print(f"จำนวน Bearish Divergence: {len(bearish_rows)}")

    bullish_rows_ini = df_plot[df_plot['divergence_plot'] == 'Bullish']
    bearish_rows_ini = df_plot[df_plot['divergence_plot'] == 'Bearish']
    if len(bullish_rows_ini) < 2 and len(bearish_rows_ini) < 2:
        print("สร้างข้อมูล Divergence ตัวอย่างสำหรับทดสอบ...")
        # เลือกจุดสุ่ม 2 จุดสำหรับทดสอบ
        sample_indices = df_plot.index[:10:4]  # เลือกทุกจุดที่ 4 จาก 10 จุดแรก
        print(f"sample_indices: {sample_indices}, {len(sample_indices)}")
        if len(sample_indices) >= 2:
            df_plot.loc[sample_indices[0], 'divergence_plot'] = 'Bullish'
            df_plot.loc[sample_indices[1], 'divergence_plot'] = 'Bullish'
            print(f"สร้าง Bullish Divergence ตัวอย่างที่: {sample_indices[0]}, {sample_indices[1]}")




    # รวมกับ Local Minima และ addplot อื่น ๆ
    apds_all = apds + [apds_local_min, apds_local_max]
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
        title="Bullish/Bearish Divergence",
        panel_ratios=(2,1),
        figratio=(14,8),
        figscale=1.2,
        xrotation=20,      # ให้แกน X เอียง 20°
        returnfig=True
    )
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.show()
    plt.close(fig)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    print(f"detect_bullish_bearish {rsistatus}, {signal}")

    # ====== Plot by Matplotlib======
    plt.figure(figsize=(14,8))
    # Price
    plt.subplot(2,1,1)
    plt.plot(df_plot['date'], df_plot['close'], color='blue', label='Close')
    plt.scatter(df_plot['date'], df_plot['Price_local_min'], color='green', marker='o', label='Price Min')
    plt.scatter(df_plot['date'], df_plot['Price_local_max'], color='red', marker='o', label='Price Max')
    plt.scatter(df_plot.loc[df_plot['divergence_plot']=='Bullish','date'],
                df_plot.loc[df_plot['divergence_plot']=='Bullish','close'],
                color='lime', marker='^', s=150, label='Bullish Div')
    plt.scatter(df_plot.loc[df_plot['divergence_plot']=='Bearish','date'],
                df_plot.loc[df_plot['divergence_plot']=='Bearish','close'],
                color='orange', marker='v', s=150, label='Bearish Div')
    plt.title("Bullish/Bearish Divergence Signals"); plt.legend(); plt.grid(True)

    # RSI
    plt.subplot(2,1,2)
    plt.plot(df_plot['date'], df_plot['RSI'], color='purple', label='RSI')
    plt.scatter(df_plot['date'], df_plot['RSI_local_min'], color='green', marker='o', label='RSI Min')
    plt.scatter(df_plot['date'], df_plot['RSI_local_max'], color='red', marker='o', label='RSI Max')
    plt.axhline(70, color='red', linestyle='--'); plt.axhline(30, color='green', linestyle='--')
    plt.title("RSI with Local Extrema"); plt.legend(); plt.grid(True)

    plt.tight_layout(); plt.show()

    # ====== Plot กราฟ Test ======
    fig, (ax_price, ax_rsi) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                        gridspec_kw={'height_ratios': [2, 1]})

    # วาดราคา
    ax_price.plot(df_plot.index, df_plot['close'], label="Close Price", color="black")

    # วาด RSI
    ax_rsi.plot(df_plot.index, df_plot['RSI'], label="RSI", color="blue")
    ax_rsi.axhline(70, color="red", linestyle="--", alpha=0.5)
    ax_rsi.axhline(30, color="green", linestyle="--", alpha=0.5)

    # -----------------------------
    # หาคู่จุด Divergence อัตโนมัติ
    # -----------------------------

    def plot_divergence_lines(df, kind="Bullish", ax_price=None, ax_rsi=None, color="green"):
        # เลือกแถวที่เป็น divergence ตามประเภท
        rows = df[df['divergence_plot'] == kind]

        # ถ้ามีอย่างน้อย 2 จุด
        if len(rows) >= 2:
            points = rows[['close', 'RSI']]

            # loop สร้างคู่ต่อเนื่อง
            for i in range(len(points) - 1):
                t1, t2 = points.index[i], points.index[i+1]
                p1, p2 = points['close'].iloc[i], points['close'].iloc[i+1]
                r1, r2 = points['RSI'].iloc[i], points['RSI'].iloc[i+1]

                # วาดเส้นที่กราฟราคา
                ax_price.plot([t1, t2], [p1, p2], color=color, linestyle="--", linewidth=1.5)

                # วาดเส้นที่กราฟ RSI
                ax_rsi.plot([t1, t2], [r1, r2], color=color, linestyle="--", linewidth=1.5)


    # Bullish = สีเขียว
    plot_divergence_lines(df_plot, kind="Bullish", ax_price=ax_price, ax_rsi=ax_rsi, color="green")

    # Bearish = สีแดง
    plot_divergence_lines(df_plot, kind="Bearish", ax_price=ax_price, ax_rsi=ax_rsi, color="red")

    # -----------------------------
    # ตกแต่งกราฟ
    # -----------------------------
    ax_price.set_title("Price with Divergence Lines")
    ax_price.legend()
    ax_rsi.set_title("RSI with Divergence Lines")
    ax_rsi.legend()

    plt.tight_layout()
    plt.show()

    # แสดง divergence ที่เจอ
    print(df_plot.dropna(subset=['divergence'])[['date','close','RSI','divergence']])

    return img_base64, rsistatus, signal

def detect_swing_trade_ema(SYMBOL: str):

    df, error = prepare_stock_data(SYMBOL, tf="D", end_date=end_date)

    # === Moving Average ===
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()

    # === Swing Low Function ===
    def find_swing_lows(df, lookback=2):
        swing_lows = []
        for i in range(lookback, len(df)-lookback):
            low = df['low'].iloc[i]
            if low == min(df['low'].iloc[i-lookback:i+lookback+1]):
                swing_lows.append((df['date'].iloc[i], low))
        return pd.DataFrame(swing_lows, columns=['date','Swing_Low'])

    swing_lows = find_swing_lows(df, lookback=2)
    df = df.merge(swing_lows, on="date", how="left")

    # === Buy the Dip Condition + TP ===
    signals = []
    for i in range(1, len(df)):
        if df['EMA20'].iloc[i] < df['EMA50'].iloc[i]:  # ตลาดขาลง
            if pd.notna(df['Swing_Low'].iloc[i-1]) and df['close'].iloc[i] > df['EMA20'].iloc[i]:
                entry = df['close'].iloc[i]
                stop_loss = df['Swing_Low'].iloc[i-1]
                risk = entry - stop_loss
                take_profit = entry + (2 * risk)   # Risk:Reward = 1:2

                signals.append((df['date'].iloc[i], "BUY", entry, stop_loss, take_profit))

    signals_df = pd.DataFrame(signals, columns=['date','Signal','Entry_Price','Stop_Loss','Take_Profit'])

    print("📊 สัญญาณ Buy the Dip (ตลาดขาลง) พร้อม TP:")
    print(signals_df)

    # === Plot ===
    plt.figure(figsize=(12,6))
    plt.plot(df['date'], df['close'], label="Close", color="blue")
    plt.plot(df['date'], df['EMA20'], label="EMA20", color="orange")
    plt.plot(df['date'], df['EMA50'], label="EMA50", color="red")

    # Swing Low
    plt.scatter(swing_lows['date'], swing_lows['Swing_Low'], color='green', marker="v", label="Swing Low")

    # Signals
    for _, row in signals_df.iterrows():
        plt.scatter(row['date'], row['Entry_Price'], color="lime", marker="o", s=100, label="Buy Entry")
        plt.axhline(row['Stop_Loss'], color="purple", linestyle="--", label="Stop Loss")
        plt.axhline(row['Take_Profit'], color="gold", linestyle="--", label="Take Profit")

    plt.title("Swing Trading + Buy the Dip + Auto TP (RR 1:2)")
    plt.legend()
    # ✅ ตั้งค่าแกน X ให้แสดงวันที่ทุก 7 วัน
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=20)  # ✅ แกน X เอียง 20 องศา
    plt.show()


def detect_double_bottom(SYMBOL: str):

    # ตัวอย่าง DataFrame
    # df = pd.DataFrame({"date": [...], "close": [...]})

    df, error = prepare_stock_data(SYMBOL, tf="D", end_date=end_date)
    # หา local minima และ maxima
    df['min'] = df['close'][(df['close'].shift(1) > df['close']) & (df['close'].shift(-1) > df['close'])]
    df['max'] = df['close'][(df['close'].shift(1) < df['close']) & (df['close'].shift(-1) < df['close'])]

    # ดึง index ที่เป็น local minima
    min_idx = argrelextrema(df['close'].values, np.less, order=5)[0]

    signals = []
    threshold = 0.03  # 3% tolerance

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
                signals.append({
                    "first_bottom": df['date'].iloc[first],
                    "second_bottom": df['date'].iloc[second],
                    "neckline": neckline,
                    "breakout_date": breakout.index[0],
                    "breakout_price": breakout.iloc[0]
                })

    # แสดงผล
    signals_df = pd.DataFrame(signals)
    print(signals_df)

    # Plot ตัวอย่าง
    plt.figure(figsize=(12,6))
    plt.plot(df['date'], df['close'], label="Close Price")

    for sig in signals:
        plt.scatter(sig['first_bottom'], df.loc[df['date'] == sig['first_bottom'], 'close'], color='red', marker='v')
        plt.scatter(sig['second_bottom'], df.loc[df['date'] == sig['second_bottom'], 'close'], color='red', marker='v')
        plt.axhline(sig['neckline'], color='green', linestyle='--')
        plt.scatter(df['date'].iloc[sig['breakout_date']], sig['breakout_price'], color='blue', marker='^', s=120, label="Buy Signal")

    plt.legend()
    plt.show()


if __name__ == "__main__":

    #detect_latest_bullish_divergence(symbol=SYMBOL)
    img_base64 = detect_overbought_oversold(SYMBOL=SYMBOL)
    print(img_base64)
    #detect_bullish_bearish_divergence(symbol=SYMBOL)
    #detect_swing_trade_ema(symbol=SYMBOL)


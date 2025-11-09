import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import mplfinance as mpf
from io import BytesIO
import io
import base64

from statsmodels.tsa.statespace.sarimax import SARIMAX
from pandas.tseries.offsets import BDay

from fetch_stock_data import fetch_stock_data

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
import sys

#SYMBOL = "TASCO"
FORECAST_DAYS = 30
START_PREDICT_DATE = "2025-10-01"  # กำหนดวันที่เริ่มต้นทำนาย
DATE_CANDIDATES = ["date", "Date", "DATE", "datetime", "Datetime", "timestamp", "Timestamp"]
OVERSOLD_TH = 30


# -------------------------------
# Utilities
# -------------------------------
def _pick_price_column(df: pd.DataFrame) -> pd.Series:
    if "Close" in df.columns:
        return df["Close"].copy()
    for col in ["Adj Close", "Close Price", "close"]:
        if col in df.columns:
            return df[col].copy()
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        raise ValueError("No numeric/price-like columns found.")
    return df[numeric_cols[-1]].copy()

def _enforce_datetime_index(df: pd.DataFrame, date_col: str | None) -> pd.DatetimeIndex:
    if date_col is not None:
        if date_col not in df.columns:
            raise ValueError(f"date_col='{date_col}' not found in DataFrame columns: {list(df.columns)}")
        idx = pd.to_datetime(df[date_col], errors="coerce", utc=False)
        if idx.isna().any():
            raise ValueError("Some dates in the specified date column could not be parsed.")
        return idx
    if isinstance(df.index, pd.DatetimeIndex):
        return df.index
    for cand in DATE_CANDIDATES:
        if cand in df.columns:
            idx = pd.to_datetime(df[cand], errors="coerce", utc=False)
            if not idx.isna().any():
                return idx
    idx = pd.to_datetime(df.index, errors="coerce", utc=False)
    if idx.isna().any():
        raise ValueError("Index could not be parsed to datetime.")
    return idx

def prepare_series(data, date_col: str | None = None) -> pd.Series:
    if isinstance(data, pd.Series):
        s = data.copy()
        if not isinstance(s.index, pd.DatetimeIndex):
            idx = pd.to_datetime(s.index, errors="coerce", utc=False)
            if idx.isna().any():
                raise ValueError("Series index not datetime.")
            s.index = idx
    elif isinstance(data, pd.DataFrame):
        s = _pick_price_column(data)
        dt_index = _enforce_datetime_index(data, date_col=date_col)
        s.index = dt_index
    else:
        raise TypeError("Input must be Series or DataFrame")
    s = s.astype("float64").sort_index().dropna()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 50:
        raise ValueError("Too few data points")
    return s

# -------------------------------
# RSI (SMA-based) + Oversold Features
# -------------------------------
def rsi_from_series(close: pd.Series, period=14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    down = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = up / down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def build_rsi_features(close: pd.Series, period=14, th=OVERSOLD_TH) -> pd.DataFrame:
    rsi = rsi_from_series(close, period)
    feat = pd.DataFrame({
        "Rsi": rsi,
        "Rsi_slope": rsi.diff(),
        "Rsi_dist30": (rsi - th),
        "Rsi_oversold": (rsi < th).astype(int),
    }, index=close.index)
    cross_up = (rsi.shift(1) < th) & (rsi >= th)
    feat["Rsi_crossup"] = cross_up.astype(int)
    feat = feat.replace([np.inf, -np.inf], np.nan)
    feat = feat.fillna(method="ffill").fillna(method="bfill")
    return feat

# -------------------------------
# Candlestick Pattern Features
# -------------------------------
def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Return binary features for a few reversal patterns using O/H/L/C."""
    patterns = pd.DataFrame(index=df.index)

    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(set(df.columns)):
        # If any of OHLC missing, return zeros
        for col in ["Bullish_Hammer", "Bearish_Engulfing", "Doji"]:
            patterns[col] = 0
        return patterns

    # Basic calculations
    body = (df["Close"] - df["Open"]).abs()
    candle_range = (df["High"] - df["Low"]).replace(0, 0.001)  # Avoid division by zero
    body_mid = df[["Open", "Close"]].mean(axis=1)

    # Shadow calculations
    upper_shadow = df["High"] - df[["Open", "Close"]].max(axis=1)
    lower_shadow = df[["Open", "Close"]].min(axis=1) - df["Low"]
    total_shadow = upper_shadow + lower_shadow
    
    # Previous values
    prev_open = df["Open"].shift(1)
    prev_close = df["Close"].shift(1)
    prev_high = df["High"].shift(1)
    prev_low = df["Low"].shift(1)
    prev_body = (prev_close - prev_open).abs()
    
    # Two periods back
    prev2_close = df["Close"].shift(2)
    prev2_open = df["Open"].shift(2)
    
    # 1. Bullish Hammer (ปรับปรุงเงื่อนไข)
    is_small_body = body / candle_range < 0.3
    has_long_lower_shadow = lower_shadow > 2 * body
    is_near_low = (df["Close"] - df["Low"]) / candle_range < 0.2
    patterns["Bullish_Hammer"] = ((is_small_body & has_long_lower_shadow & is_near_low) & 
                                 (df["Close"] > df["Open"])).fillna(False).astype(int)
    
    # 2. Bearish Hammer (Inverted Hammer)
    has_long_upper_shadow = upper_shadow > 2 * body
    is_near_high = (df["High"] - df["Close"]) / candle_range < 0.2
    patterns["Bearish_Hammer"] = ((is_small_body & has_long_upper_shadow & is_near_high) & 
                                 (df["Close"] < df["Open"])).fillna(False).astype(int)
    
    # 3. Bullish Engulfing
    is_downtrend = prev_close < prev_open  #  downtrend before
    current_bullish = df["Close"] > df["Open"]
    engulfs_previous = (df["Open"] < prev_close) & (df["Close"] > prev_open)
    patterns["Bullish_Engulfing"] = ((is_downtrend & current_bullish & engulfs_previous) & 
                                    (body > prev_body * 1.2)).fillna(False).astype(int)
    
    # 4. Bearish Engulfing
    is_uptrend = prev_close > prev_open  # uptrend before
    current_bearish = df["Close"] < df["Open"]
    engulfs_previous_bearish = (df["Open"] > prev_close) & (df["Close"] < prev_open)
    patterns["Bearish_Engulfing"] = ((is_uptrend & current_bearish & engulfs_previous_bearish) & 
                                    (body > prev_body * 1.2)).fillna(False).astype(int)
    
    # 5. Morning Star Pattern (3-candle pattern)
    first_candle_bearish = (prev2_close < prev2_open) & (prev_body > candle_range * 0.5)
    second_candle_small = (prev_close - prev_open).abs() / (prev_high - prev_low) < 0.3
    third_candle_bullish = (df["Close"] > df["Open"]) & (df["Close"] > prev2_open)
    gap_down = prev_open < prev_low  # gap down from first candle
    gap_up = df["Open"] > prev_close  # gap up from second candle
    patterns["Morning_Star"] = ((first_candle_bearish & second_candle_small & 
                               third_candle_bullish & gap_down & gap_up)).fillna(False).astype(int)
    
    # 6. Evening Star Pattern
    first_candle_bullish = (prev2_close > prev2_open) & (prev_body > candle_range * 0.5)
    third_candle_bearish = (df["Close"] < df["Open"]) & (df["Close"] < prev2_open)
    gap_up_first = prev_open > prev_high  # gap up from first candle
    gap_down_third = df["Open"] < prev_low  # gap down from second candle
    patterns["Evening_Star"] = ((first_candle_bullish & second_candle_small & 
                               third_candle_bearish & gap_up_first & gap_down_third)).fillna(False).astype(int)
    
    # 7. Piercing Pattern
    first_candle_bearish = prev_close < prev_open
    second_candle_bullish = df["Close"] > df["Open"]
    pierces_half = df["Close"] > (prev_open + prev_close) / 2
    patterns["Piercing_Pattern"] = ((first_candle_bearish & second_candle_bullish & 
                                   pierces_half)).fillna(False).astype(int)
    
    # 8. Doji (ปรับปรุง)
    patterns["Doji"] = ((body / candle_range) <= 0.05).fillna(False).astype(int)
    
    return patterns.fillna(0)

def make_zero_candle_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Placeholder zeros for future where OHLC unknown."""
    z = pd.DataFrame(index=index)
    for col in ["Bullish_Hammer", "Bearish_Engulfing", "Doji"]:
        z[col] = 0
    return z

# ฟังก์ชันทดสอบเพิ่มเติมเพื่อตรวจสอบข้อมูล
def test_data_structure(SYMBOL: str, tf: str = "15m"):
    """ทดสอบโครงสร้างข้อมูลก่อน plot"""
    df, error = fetch_stock_data(SYMBOL, tf)
    if error:
        print(f"Error: {error}")
        return
    # ตรวจสอบและแปลงคอลัมน์เวลาเป็น DatetimeIndex
    if 'time' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    else:
        # ถ้าไม่มีคอลัมน์ time ให้ลองแปลง index
        try:
            df.index = pd.to_datetime(df.index)
        except:
            raise ValueError("Could not convert to DatetimeIndex")
    
    print("DataFrame info:")
    print(f"Index type: {type(df.index)}")
    print(f"Index: {df.index[:5]}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Shape: {df.shape}")
    
    # ตรวจสอบว่า index เป็น DatetimeIndex หรือไม่
    if not isinstance(df.index, pd.DatetimeIndex):
        print("WARNING: Index is not DatetimeIndex!")
        
    return df

def plot_results(df, series, future_mean, SYMBOL, FORECAST_DAYS, START_PREDICT_DATE):

    mc = mpf.make_marketcolors(up='lime', down='red', edge='black', wick='black', volume='blue')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle=':')

    base_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    base_df = df[base_cols].astype(float)

    # --- 3) แยกช่วง forecast ---
    first_half = future_mean.iloc[:15]  # 15 วันแรก → แท่งเทียนจำลอง
    last_half = future_mean.iloc[15:]   # 15 วันหลัง → เส้นต่อเนื่อง

    # --- 4) สร้างแท่งเทียนจำลอง ---
    last_close = df['Close'].iloc[-1]
    prev_close = last_close
    synth_data = []
    for dt, val in first_half.items():
        open_ = prev_close
        close_ = val
        spread = max(0.005 * close_, 0.01)
        high_ = max(open_, close_) + spread
        low_ = min(open_, close_) - spread
        synth_data.append({'Open': open_, 'High': high_, 'Low': low_, 'Close': close_, 'Volume': np.nan})
        prev_close = close_

    synth_df = pd.DataFrame(synth_data, index=first_half.index)

    # --- 5) รวมข้อมูลจริง + 15 วันแรกของอนาคต (แท่งเทียน) ---
    combined_df = pd.concat([base_df, synth_df])

    # ✅ เพิ่มแถวว่างสำหรับช่วง 15 วันสุดท้าย (เพื่อรองรับเส้น)
    future_padding = pd.DataFrame({
        'Open': np.nan,
        'High': np.nan,
        'Low': np.nan,
        'Close': np.nan,
        'Volume': np.nan
    }, index=last_half.index)

    combined_df = pd.concat([combined_df, future_padding])
    combined_df = combined_df.astype(float)

    # --- 6) เตรียม indicators ให้ align กับ combined_df ---
    ema5_plot = df['Ema5'].reindex(combined_df.index)
    ema20_plot = df['Ema20'].reindex(combined_df.index)
    vol_ma20_plot = df['Volume'].rolling(20).mean().reindex(combined_df.index)
    rsi_plot = df['Rsi'].reindex(combined_df.index)

    # --- 7) สร้างเส้น forecast (15 วันสุดท้าย) ---
    future_plot = pd.Series(index=combined_df.index, data=np.nan, dtype=float)
    future_30 = future_mean.iloc[:30] 
    aligned_future = future_30.reindex(combined_df.index)
    for idx, val in aligned_future.items():
        if pd.notna(val):
            future_plot.loc[idx] = val

    # --- ตรวจสอบก่อน plot ---
    if future_plot.dropna().empty:
        print("⚠️ Warning: No forecast values aligned with combined_df index.")
        return None

    # --- 8) สร้าง addplot ---
    apds = [
        mpf.make_addplot(ema5_plot, color='brown', width=1.5, panel=0, label='EMA5'),
        mpf.make_addplot(ema20_plot, color='purple', width=1.5, panel=0, label='EMA20'),
        mpf.make_addplot(future_plot, color='blue', width=2, panel=0, label='Forecast (Line)'),
        mpf.make_addplot(vol_ma20_plot, color='black', panel=1),
        mpf.make_addplot(rsi_plot, color='blue', panel=2),
        mpf.make_addplot([30]*len(combined_df), color='green', linestyle='--', panel=2),
        mpf.make_addplot([70]*len(combined_df), color='red', linestyle='--', panel=2),
    ]

    # การ Plot
    fig, axes = mpf.plot(
        combined_df,
        type='candle',
        style=style,
        addplot=apds,
        volume=True,
        #figsize=(22, 12),  # กราฟใหญ่
        figsize=(12, 8),
        panel_ratios=(12,1,1),
        update_width_config={
            'candle_linewidth': 1,
            'candle_width': 0.55,
            'volume_width': 0.55,
        },
        tight_layout=True,
        returnfig=True,
        closefig=False,
        datetime_format='%Y-%m-%d',  # ใช้รูปแบบย่อ
        xrotation=20,                # หมุนวันที่ 30 องศา
        title=f"{SYMBOL} {FORECAST_DAYS} Business Days Forecast (1D)",
        show_nontrading=False,
        ylabel='Price'
    )
    # กำหนดการแสดงวันที่
    main_ax = axes[0]






    # หาวันจันทร์ที่มีการซื้อขายจริง
    mondays = df.index[df.index.dayofweek == 0]
    selected_mondays = mondays[::2]  # ทุกๆ 2 วันจันทร์

    # หาตำแหน่งในแกน x
    positions = [df.index.get_loc(date) for date in selected_mondays]
    labels = [date.strftime('%Y-%m-%d') for date in selected_mondays]

    main_ax.set_xticks(positions)
    main_ax.set_xticklabels(labels, rotation=20)
    main_ax.grid(True, linestyle='--', alpha=0.3)

    # --- Hint ด้านล่างรูป (กึ่งกลางด้านล่าง) ---
    hint = fig.text(
        0.5, 0.015,                # ตำแหน่ง (สัดส่วน fig) ต่ำสุดของรูป
        "Date:",
        ha='center', va='bottom',
        fontsize=11,
        bbox=dict(boxstyle='round', fc='w', ec='0.6', alpha=0.85, pad=0.4)
    )

    tooltip = main_ax.annotate(
        text="",
        xy=(0, 0),
        xytext=(15, 15),  # offset จากเม้าส์
        textcoords="offset points",
        bbox=dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9, pad=0.4),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        fontsize=10,
        visible=False
    )

    # บันทึก index เป็น list เพื่อเข้าถึงเร็ว
    idx_dates = list(df.index)

    # เส้นไกด์แนวตั้ง (ไว้ช่วยบอกแท่งที่ชี้)
    vline = main_ax.axvline(x=np.nan, linestyle='--', alpha=0.35)

    def on_move(event):
        # เช็คว่าเมาส์อยู่ในแกนหลักและมีพิกัด x
        if event.inaxes != main_ax or event.xdata is None:
            hint.set_text("Date:")
            vline.set_xdata([np.nan, np.nan])
            tooltip.set_visible(False)
            fig.canvas.draw_idle()
            return

        # xdata ของ mplfinance เป็นตำแหน่งเชิงตัวเลข (0..N-1) แม้ใช้ DatetimeIndex
        x = int(round(event.xdata))
        if x < 0 or x >= len(idx_dates):
            hint.set_text("Date:")
            vline.set_xdata([np.nan, np.nan])
            tooltip.set_visible(False)
            fig.canvas.draw_idle()
            return

        dt = idx_dates[x]
        row = df.iloc[x]
        hint.set_text(
            f"Date: {dt.strftime('%Y-%m-%d')} | O:{row['Open']:.2f} H:{row['High']:.2f} "
            f"L:{row['Low']:.2f} C:{row['Close']:.2f} Vol:{row.get('Volume', float('nan'))}")
        tooltip.xy = (x, row['Close'])  # จุดผูก annotation (แกนกราฟ)
        tooltip.set_text(
            f"{dt.strftime('%Y-%m-%d')}\n"
            f"O:{row['Open']:.2f} H:{row['High']:.2f}\n"
            f"L:{row['Low']:.2f} C:{row['Close']:.2f}\n"
            f"EMA5:{row.get('Ema5', float('nan')):.2f} Ema20:{row.get('Ema20', float('nan')):.2f}" )
        tooltip.set_visible(True)

        # ขยับเส้นไกด์ไปยังแท่งที่ชี้
        vline.set_xdata([x, x])
        fig.canvas.draw_idle()

    # ผูก event เลื่อนเมาส์
    cid = fig.canvas.mpl_connect('motion_notify_event', on_move)
    fig.canvas.mpl_connect('motion_notify_event', on_move)

    fig.autofmt_xdate()
    plt.legend()
    plt.tight_layout()
    plt.show()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    #filename = f"{SYMBOL}_prediction_plot.png"
    #plt.savefig(filename)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def plot_chart(date_col: str | None = "Date", SYMBOL: str = None, tf: str = "15m", max_bars: int = 150):
    # โหลดข้อมูล
    df, error = fetch_stock_data(SYMBOL, tf)
    if error:
        raise RuntimeError(f"Data load error for {SYMBOL}: {error}")
    
    # จำกัดจำนวนแท่ง
    if len(df) > max_bars:
        df = df.tail(max_bars)

    # แปลง DatetimeIndex
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    else:
        df.index = pd.to_datetime(df.index)

    # Normalize column names
    rename_map = {c: c.capitalize() for c in df.columns}
    df = df.rename(columns=rename_map)

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # สร้างกราฟ
    mc = mpf.make_marketcolors(up='lime', down='red', edge='black', wick='black', volume='blue')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle=':')

    apds = [
        mpf.make_addplot(df['Ema5'], color='brown', width=1.5, label='EMA 5', panel=0),
        mpf.make_addplot(df['Ema20'], color='purple', width=1.5, label='EMA 20', panel=0),
        mpf.make_addplot(df['Volume'].rolling(20).mean(), color='red', panel=1),
        mpf.make_addplot(df['Rsi'], color='blue', panel=2),
        #mpf.make_addplot([30]*len(df), color='green', linestyle='--', panel=2),
        #mpf.make_addplot([70]*len(df), color='red', linestyle='--', panel=2),
    ]
    # เพิ่มเส้น RSI levels โดยระบุให้ใช้แกนด้านซ้าย
    for level in [30, 70]:
        apds.append(
            mpf.make_addplot(
                [level] * len(df), 
                color='green' if level == 30 else 'red', 
                linestyle='--', 
                panel=2,
                width=1.0,
                secondary_y=False,  # 强制使用左侧Y轴
                #label=f'RSI {level}'
            )
        )

    fig, axes = mpf.plot(
        df,
        type='candle',
        style=style,
        addplot=apds,
        volume=True,
        #figsize=(22, 12),  # กราฟใหญ่
        figsize=(12, 8),
        panel_ratios=(12,1,1),
        update_width_config={
            'candle_linewidth': 1,
            'candle_width': 0.55,
            'volume_width': 0.55,
        },
        tight_layout=True,
        returnfig=True,
        closefig=False,
        datetime_format='%Y-%m-%d',  # ใช้รูปแบบย่อ
        xrotation=20,                # หมุนวันที่ 30 องศา
        title=f"{SYMBOL} ({tf})",
        show_nontrading=False,
        ylabel='Price'
    )

    axes[0].legend(loc='upper right')  # Legend สำหรับกราฟราคา (EMA)
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.show()
    plt.close(fig)

    return base64.b64encode(buf.getvalue()).decode('utf-8')


def compute_rsi(data, window=14):
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def plot_chart_daily_weekly_side_by_side(SYMBOL: str, max_bars: int = 150):
    # โหลดข้อมูล Daily และ Weekly
    df_d, error_d = fetch_stock_data(SYMBOL, "D")
    df_w, error_w = fetch_stock_data(SYMBOL, "W")
    if error_d or error_w:
        raise RuntimeError(f"Data load error: {error_d or error_w}")

    # --- เตรียม Daily ---
    df_d['time'] = pd.to_datetime(df_d['time'])
    df_d.set_index('time', inplace=True)
    if len(df_d) > max_bars:
        df_d = df_d.tail(max_bars)
    df_d = df_d.rename(columns={c: c.capitalize() for c in df_d.columns})
    df_d["RSI"] = compute_rsi(df_d)

    # --- เตรียม Weekly ---
    df_w['time'] = pd.to_datetime(df_w['time'])
    df_w.set_index('time', inplace=True)
    df_w = df_w.rename(columns={c: c.capitalize() for c in df_w.columns})
    df_w["RSI"] = compute_rsi(df_w)

    # --- Style ---
    mc = mpf.make_marketcolors(up='lime', down='red', edge='black', wick='black', volume='blue')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle=':')

    # --- Layout 3 แถว × 2 คอลัมน์ ---
    fig = plt.figure(figsize=(16,10))
    gs = gridspec.GridSpec(3, 2, height_ratios=[3,0.5,0.5], hspace=0.3, wspace=0.2)

    # Daily Panels
    ax_d_price = fig.add_subplot(gs[0,0])
    ax_d_vol   = fig.add_subplot(gs[1,0])
    ax_d_rsi   = fig.add_subplot(gs[2,0])

    # Weekly Panels
    ax_w_price = fig.add_subplot(gs[0,1])
    ax_w_vol   = fig.add_subplot(gs[1,1])
    ax_w_rsi   = fig.add_subplot(gs[2,1])

    # --- Plot Daily Candlestick ---
    mpf.plot(
        df_d,
        type='candle',
        update_width_config={
            'candle_linewidth': 1,
            'candle_width': 0.55,
            'volume_width': 0.55,
        },
        style=style,
        ax=ax_d_price,
        volume=ax_d_vol,
        show_nontrading=False
    )
    ax_d_price.set_title(f"{SYMBOL} - Daily")

    # Daily RSI
    ax_d_rsi.plot(df_d.index, df_d["RSI"], color="purple")
    ax_d_rsi.axhline(70, color="red", linestyle="--")
    ax_d_rsi.axhline(30, color="green", linestyle="--")
    ax_d_rsi.set_ylim(0,100)
    ax_d_rsi.legend()

    # --- Plot Weekly Candlestick ---
    mpf.plot(
        df_w,
        type='candle',
        style=style,
        ax=ax_w_price,
        volume=ax_w_vol,
        show_nontrading=False
    )
    ax_w_price.set_title(f"{SYMBOL} - Weekly")

    # Weekly RSI
    ax_w_rsi.plot(df_w.index, df_w["RSI"], color="blue")
    ax_w_rsi.axhline(70, color="red", linestyle="--")
    ax_w_rsi.axhline(30, color="green", linestyle="--")
    ax_w_rsi.set_ylim(0,100)
    ax_w_rsi.legend()

    # ซ้าย xtick labels ในพาเนลบน (price และ volume)
    ax_d_price.set_xticklabels([])
    ax_d_vol.set_xticklabels([])
    ax_w_price.set_xticklabels([])
    ax_w_vol.set_xticklabels([])

    # ตั้งค่าการจัดรูปแบบวันที่ในพาเนล RSI
    date_format = mdates.DateFormatter('%Y-%m-%d')
    ax_d_rsi.xaxis.set_major_formatter(date_format)
    ax_w_rsi.xaxis.set_major_formatter(date_format)

    # หมุนวันที่เพื่อให้อ่านง่าย
    for tick in ax_d_rsi.get_xticklabels():
        tick.set_rotation(25)
    for tick in ax_w_rsi.get_xticklabels():
        tick.set_rotation(25)

    plt.tight_layout()
    filename = f"images/{SYMBOL}.png"
    #plt.legend()
    plt.savefig(filename)
    plt.show()
    plt.close(fig)


# Custom Toolbar สำหรับ PyQt
class CustomToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent, custom_home_function=None):
        super().__init__(canvas, parent)
        self.custom_home_function = custom_home_function
    
    def home(self, *args, **kwargs):
        # เรียกฟังก์ชั่นเดิมของ matplotlib
        super().home(*args, **kwargs)
        
        # เรียกฟังก์ชั่นที่คุณสร้างเอง
        if self.custom_home_function:
            self.custom_home_function()

def plot_chart_PyQt(date_col: str | None = "Date", SYMBOL: str = None, tf: str = "15m", max_bars: int = 100):
    # โหลดข้อมูล
    df, error = fetch_stock_data(SYMBOL, tf)
    if error:
        raise RuntimeError(f"Data load error for {SYMBOL}: {error}")
    
    # ตรวจสอบและแปลงคอลัมน์เวลาเป็น DatetimeIndex
    if len(df) > max_bars:
        df = df.tail(max_bars)
        print(f"Showing last {max_bars} bars only")
    
    if 'time' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    else:
        try:
            df.index = pd.to_datetime(df.index)
        except:
            raise ValueError("Could not convert to DatetimeIndex")
    
    if not isinstance(df.index, pd.DatetimeIndex):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
        else:
            try:
                df.index = pd.to_datetime(df.index)
            except:
                raise ValueError("Could not convert index to DatetimeIndex")

    # Normalize column names
    rename_map = {c: c.capitalize() for c in df.columns}
    df = df.rename(columns=rename_map)
    
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # สร้าง PyQt Application
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # สร้างหน้าต่างหลัก
    window = QMainWindow()
    window.setWindowTitle(f"{SYMBOL} {tf} Chart")
    window.setGeometry(100, 100, 1200, 800)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    
    # สร้าง figure และ axes ด้วย mplfinance
    mc = mpf.make_marketcolors(up='lime', down='red', edge='black', wick='black', volume='blue')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle=':')
    
    apds = [
        mpf.make_addplot(df['Ema5'], color='brown', width=1.5, panel=0, label='EMA5'),
        mpf.make_addplot(df['Ema20'], color='purple', width=1.5, panel=0, label='EMA20'),
        mpf.make_addplot(df['Volume'].rolling(20).mean(), color='black', panel=1),
        mpf.make_addplot(df['Rsi'], color='blue', panel=2),
        mpf.make_addplot([30]*len(df), color='green', linestyle='--', panel=2),
        mpf.make_addplot([70]*len(df), color='red', linestyle='--', panel=2),
    ]
    
    title = f"{SYMBOL} {tf} Timeframe"
    
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=style,
        addplot=apds,
        volume=True,
        figsize=(12, 8),
        panel_ratios=(12, 1, 1),
        update_width_config={
            'candle_linewidth': 1,     
            'candle_width': 0.55,  # ลดความกว้างแท่ง
            'volume_width': 0.55,
            },
        tight_layout=True,
        returnfig=True,
        closefig=False,
        datetime_format='%Y-%m-%d %H:%M',
        xrotation=20,
        title=title,
        show_nontrading=False,
        ylabel='Price'
    )
    fig.set_size_inches(12, 8)
    fig.set_dpi(100)

    main_ax = axes[0]
    
    # ปรับขอบเขตแกน x เพื่อเพิ่มช่องว่างระหว่างแท่งเทียน
    padding = len(df) * 0.08
    x_limit = main_ax.get_xlim()
    main_ax.set_xlim(x_limit[0] - padding, x_limit[1] + padding)
    
    # ปรับขนาด font
    main_ax.tick_params(axis='both', which='major', labelsize=11)
    main_ax.grid(True, which='major', axis='x', linestyle=':', linewidth=0.9, alpha=0.9, color='grey')
    
    # เก็บค่าเริ่มต้นของแกน
    initial_limits = {
        "xlim": main_ax.get_xlim(),
        "ylim": main_ax.get_ylim()
    }
    
    # สร้าง canvas
    canvas = FigureCanvasQTAgg(fig)
    
    # ฟังก์ชัน custom home
    def my_custom_home_function():
        print("✅ Custom Home function called!")
        print("Resetting view to initial limits...")
        
        # รีเซ็ตการแสดงผล
        main_ax.set_xlim(initial_limits["xlim"])
        main_ax.set_ylim(initial_limits["ylim"])
        
        # อัพเดท title
        main_ax.set_title(f"{SYMBOL} {tf} - Reset View")
        
        # วาดใหม่
        canvas.draw()
        
        print("View reset completed!")
    
    # สร้าง custom toolbar
    toolbar = CustomToolbar(canvas, window, my_custom_home_function)
    
    # เพิ่ม tooltip
    tooltip = main_ax.annotate(
        text="",
        xy=(0, 0),
        xytext=(15, 15),
        textcoords="offset points",
        bbox=dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9, pad=0.4),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        fontsize=10,
        visible=False
    )
    
    # เส้นไกด์แนวตั้ง
    vline = main_ax.axvline(x=np.nan, linestyle='--', alpha=0.35)
    
    # ฟังก์ชันสำหรับ tooltip
    idx_dates = list(df.index)
    
    # สถานะโหมด Pan
    toolbar = CustomToolbar(canvas, window, my_custom_home_function)
    
    def check_pan_state():
        try:
            interactive_mode = False
            print(f"[DEBUG] Toolbar actions: {list(toolbar._actions.keys())}")

            pan_active = toolbar._actions.get('pan')
            zoom_active = toolbar._actions.get('zoom')

            if pan_active and pan_active.isChecked():
                print("[DEBUG] Pan mode: ON")
                interactive_mode = True
            elif zoom_active and zoom_active.isChecked():
                print("[DEBUG] Zoom mode: ON")
                interactive_mode = True
            else:
                print("[DEBUG] Pan/Zoom: OFF")
                interactive_mode = False

        except Exception as e:
            print(f"[DEBUG] Error while checking pan/zoom state: {e}")
            interactive_mode = False

    # Scroll Mouse → Zoom เฉพาะเมื่อ Pan ปิด
    base_scale = 1.1
    def zoom(event):
        if event.inaxes != main_ax:
            return
        # ตรวจสอบว่า event นี้เป็น scroll event
        if not hasattr(event, 'button') or event.button not in ['up', 'down']:
            return

        cur_xlim = main_ax.get_xlim()
        cur_ylim = main_ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata

        if event.button == 'up':  # Scroll ขึ้น → Zoom In
            scale_factor = 1 / base_scale
        elif event.button == 'down':  # Scroll ลง → Zoom Out
            scale_factor = base_scale
        else:
            return

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        main_ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        main_ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        canvas.draw()

    # ฟังก์ชันสำหรับ Double Click Reset
    def reset_zoom(event):
        if event.dblclick and event.inaxes == main_ax:
            print("Double click detected - resetting zoom")
            main_ax.set_xlim(initial_limits["xlim"])
            main_ax.set_ylim(initial_limits["ylim"])
            canvas.draw()

    # ฟังก์ชันสำหรับ Pan (ลากเมาส์)
    press_event = {'x': None, 'y': None}
    
    def on_press(event):
        if event.inaxes == main_ax:
            press_event['x'] = event.xdata
            press_event['y'] = event.ydata

    def on_move(event):
        interactive_mode = False
        check_pan_state()

        if interactive_mode:
            return

        if event.inaxes != main_ax or event.xdata is None:
            tooltip.set_visible(False)
            canvas.draw()
            return
        
        x = int(round(event.xdata))
        if 0 <= x < len(df):
            dt = df.index[x]
            row = df.iloc[x]
            tooltip.xy = (x, row['Close'])
            tooltip.set_text(
                f"{dt.strftime('%Y-%m-%d %H:%M')}\n"
                f"O:{row['Open']:.2f} H:{row['High']:.2f}\n"
                f"L:{row['Low']:.2f} C:{row['Close']:.2f}\n"
                f"EMA5:{row['Ema5']:.2f} EMA20:{row['Ema20']:.2f}"
            )
            tooltip.set_visible(True)
            canvas.draw()
    
    # เชื่อม event
    canvas.mpl_connect('motion_notify_event', on_move)
    
    # เพิ่ม widget ลง layout
    layout.addWidget(toolbar)
    layout.addWidget(canvas)

    def on_motion(event):
        if press_event['x'] is None or event.inaxes != main_ax:
            return
        
        # ตรวจสอบว่าไม่ใช่โหมด Pan จาก toolbar
        check_pan_state()
        if interactive_mode:
            return
            
        dx = press_event['x'] - event.xdata
        dy = press_event['y'] - event.ydata
        
        cur_xlim = main_ax.get_xlim()
        cur_ylim = main_ax.get_ylim()
        
        main_ax.set_xlim(cur_xlim[0] + dx, cur_xlim[1] + dx)
        main_ax.set_ylim(cur_ylim[0] + dy, cur_ylim[1] + dy)
        
        fig.canvas.draw_idle()
        #canvas.draw()
    
    def on_release(event):
        press_event['x'] = None
        press_event['y'] = None

    canvas.mpl_connect('scroll_event', zoom)
    canvas.mpl_connect('button_press_event', on_press)
    canvas.mpl_connect('motion_notify_event', on_motion)
    canvas.mpl_connect('button_release_event', on_release)
    canvas.mpl_connect('button_press_event', reset_zoom)
    # ------------------------------------------

    # แสดงหน้าต่าง
    #window.show()
    
    # รัน application
    app.exec_()
    
    # ส่งกลับ base64 image
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    
    return base64.b64encode(buf.getvalue()).decode('utf-8')


# -------------------------------
# Main (single cut-off forecast)
# -------------------------------

def main(date_col: str | None = "Date", SYMBOL: str = None):
    # 1) Load
    df, error = fetch_stock_data(SYMBOL)
    #df.columns = df.columns.str.capitalize()
    if error:
        raise RuntimeError(f"Data load error for {SYMBOL}: {error}")
    # Normalize column names (keep case for OHLCV keys)
    # Ensure standard OHLCV exist if present
    rename_map = {c: c.capitalize() for c in df.columns}
    df = df.rename(columns=rename_map)

    # 2) Target series (Close) with Date index
    series = prepare_series(df, date_col=date_col)

    # 3) Build exog for history: RSI + Candlestick
    # Align df index to series
    df = df.copy()
    df.index = series.index

    rsi_feats = build_rsi_features(series)
    candle_feats = detect_candlestick_patterns(df)
    exog_full = pd.concat([rsi_feats, candle_feats], axis=1)

    # 4) Train until START_PREDICT_DATE
    print(">>> ตรวจสอบ DataFrame ก่อนกำหนด start_date")
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Index (head): {df.index[:5]}")
    if df is None or df.empty:
        raise ValueError(f"No data returned for symbol {SYMBOL}")

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df.dropna(subset=df.index.names)

    if df.empty:
        raise ValueError(f"DataFrame is empty after converting index to datetime")
    start_date = df.index.max()  # ใช้วันที่ล่าสุดใน DataFrame
    #start_date = pd.to_datetime(START_PREDICT_DATE)
    if start_date not in series.index:
        # Snap to the last available date before start_date
        start_date = series.index.asof(start_date)

    # align series ให้ตรงกับ df เสมอ
    series = series.loc[series.index.intersection(df.index)]

    if series.empty:
        raise ValueError("Series is empty after aligning with DataFrame index")
    hist_data = series.loc[:start_date]
    if len(hist_data) < 50:
        raise ValueError("Not enough history before start prediction date")
    if hist_data.empty:
        raise ValueError(f"No data available up to start_date={start_date}")
    print(f"hist_data len: {len(hist_data)}")
    print(f"hist_data head:\n{hist_data.head()}")
    print(f"hist_data tail:\n{hist_data.tail()}")

    train_exog = exog_full.loc[hist_data.index]
    print(f"train_exog columns: {train_exog.columns.tolist()}")

    order = (1, 1, 1)
    seasonal_order = (0, 0, 0, 0)
    final_fit = SARIMAX(
        hist_data,
        exog=train_exog,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False)

    # 5) Step-ahead forecast 30 business days from START_PREDICT_DATE
    future_idx = pd.bdate_range(start=start_date + BDay(1), periods=FORECAST_DAYS)

    pred_path = []
    tmp_close = hist_data.copy()

    # We'll keep track of future exog day-by-day
    future_exog_rows = []

    for i, dt in enumerate(future_idx):
        # Build RSI features from the path (uses only Close)
        print(f"Step {i}: dt={dt}, tmp_close len={len(tmp_close)}")

        rsi_all = build_rsi_features(tmp_close)
        print(f"rsi_all shape={rsi_all.shape}, last row nulls={rsi_all.iloc[-1].isna().sum()}")
        
        tmp_rsi = rsi_all.iloc[[-1]]
        #tmp_rsi = build_rsi_features(tmp_close).iloc[[-1]]

        # Future candle features unknown → zeros
        tmp_candle = make_zero_candle_features(pd.DatetimeIndex([dt]))

        tmp_exog = pd.concat([tmp_rsi.set_index(pd.DatetimeIndex([dt])), tmp_candle], axis=1)
        # Align columns to training exog
        tmp_exog = tmp_exog.reindex(columns=train_exog.columns, fill_value=0)
        print(f"Step {i}: dt={dt}, tmp_exog shape={tmp_exog.shape}, NaNs={tmp_exog.isna().sum().sum()}")
        if tmp_exog.shape[1] == 0:
            raise ValueError("No exogenous features available for forecasting step")
        if tmp_exog.empty:
            raise ValueError("tmp_exog is empty!")
        step_fore = final_fit.get_forecast(steps=1, exog=tmp_exog)
        yhat = step_fore.predicted_mean.iloc[0]

        pred_path.append(yhat)
        future_exog_rows.append(tmp_exog)

        # Append the newly predicted close to the temporary series
        tmp_close = pd.concat([tmp_close, pd.Series([yhat], index=[dt])])

    future_mean = pd.Series(pred_path, index=future_idx)
    future_exog = pd.concat(future_exog_rows, axis=0)

    print(f"future_mean len={len(future_mean)}, index range: {future_mean.index.min()} → {future_mean.index.max()}")
    print(f"df len={len(df)}, series len={len(series)}")
    print(f"future_mean.head():\n{future_mean.head()}")
    print(f"future_mean.tail():\n{future_mean.tail()}")
    plot_base64 = plot_results(df, series, future_mean, SYMBOL, FORECAST_DAYS, start_date)
    #print(plot_base64)

    # 7) Print future forecast values
    #print("\nFuture forecast (Close):")
    #print(future_mean)
    return plot_base64


if __name__ == "__main__":
    try:
        #main(date_col="Date", SYMBOL="TASCO")
        #result = plot_chart(date_col="Date", SYMBOL="BANPU", tf="D", max_bars=200)
        #print("Plot created successfully")
        #test_data_structure("TASCO", "15m")
        #image_data = plot_chart_daily_weekly_side_by_side(SYMBOL="BANPU", max_bars=300)
        chart78 = plot_chart(date_col="Date", SYMBOL="BANPU", tf="1h", max_bars=150)
    except Exception as e:
        print(f"Error: {e}")


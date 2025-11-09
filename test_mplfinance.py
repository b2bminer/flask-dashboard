import pandas as pd
import mplfinance as mpf
import matplotlib.dates as mdates
from matplotlib.dates import AutoDateLocator, DateFormatter
import matplotlib.pyplot as plt
from fetch_stock_data import fetch_stock_data

# ดึงข้อมูล
SYMBOL = "TASCO"
df, error = fetch_stock_data(SYMBOL)

if error:
    print(f"Error: {error}")
else:
    # แปลงและทำความสะอาดข้อมูล
    df.columns = df.columns.str.capitalize()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
    # กรองวันที่ที่ไม่สมเหตุสมผล
    current_year = pd.Timestamp.now().year
    df = df[df['Date'].dt.year >= current_year - 5]
    
    df = df.set_index('Date')
    
    # ตั้งค่า style
    mc = mpf.make_marketcolors(up='lime', down='red', edge='black', wick='black', volume='blue')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle=':')
    
    # พล็อตกราฟ
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=style,
        volume=True,
        figsize=(14, 8),
        returnfig=True,
        closefig=False,
        datetime_format='%Y-%m-%d',
        xrotation=30,
        show_nontrading=False
    )
    
    # กำหนดการแสดงวันที่
    main_ax = axes[0]

    # หาวันจันทร์ที่มีการซื้อขายจริง
    mondays = df.index[df.index.dayofweek == 0]
    selected_mondays = mondays[::3]  # ทุกๆ 3 วันจันทร์

    # หาตำแหน่งในแกน x
    positions = [df.index.get_loc(date) for date in selected_mondays]
    labels = [date.strftime('%Y-%m-%d') for date in selected_mondays]

    main_ax.set_xticks(positions)
    main_ax.set_xticklabels(labels, rotation=30)

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()

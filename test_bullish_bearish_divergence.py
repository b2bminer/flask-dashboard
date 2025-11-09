import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt

# =========================
# สร้างข้อมูลตัวอย่างที่ชัดเจน
# =========================
dates = pd.date_range("2024-01-01", periods=50, freq="D")
np.random.seed(42)

# สร้างแนวโน้มราคาที่ชัดเจน
trend = np.linspace(100, 110, 50) + np.sin(np.arange(50) * 0.3) * 5
data = []

for i in range(50):
    base = trend[i]
    open_p = base + np.random.randn() * 0.8
    close_p = base + np.random.randn() * 0.8
    high_p = max(open_p, close_p) + abs(np.random.randn() * 0.6)
    low_p = min(open_p, close_p) - abs(np.random.randn() * 0.6)
    
    # สร้าง RSI ที่เห็น divergence ชัดเจน
    if i < 25:
        rsi = 40 + i * 0.5  # RSI เพิ่มขึ้น
    else:
        rsi = 60 - (i - 25) * 0.3  # RSI ลดลง
    
    data.append([open_p, high_p, low_p, close_p, rsi])

df_plot = pd.DataFrame(data, index=dates, 
                      columns=['Open', 'High', 'Low', 'Close', 'RSI'])

SYMBOL = "TEST_STOCK"
bullish_pairs = [(15, 35)]  # ตัวอย่างจุด divergence
bearish_pairs = [(10, 30)]

print("ข้อมูลตัวอย่าง:")
print(df_plot.head())
print(f"\nช่วงราคา: {df_plot['Low'].min():.2f} - {df_plot['High'].max():.2f}")
print(f"ช่วง RSI: {df_plot['RSI'].min():.2f} - {df_plot['RSI'].max():.2f}")

# =========================
# วิธีที่ได้ผลแน่นอน: ใช้ mplfinance แบบ standalone
# =========================

# สร้างเส้น divergence ด้วย alines
divergence_lines = []

# Bullish divergence (เส้นสีเขียว)
for i1, i2 in bullish_pairs:
    line = [
        (df_plot.index[i1], df_plot['Low'].iloc[i1] - 1),
        (df_plot.index[i2], df_plot['Low'].iloc[i2] - 1)
    ]
    divergence_lines.append(line)

# Bearish divergence (เส้นสีแดง)  
for i1, i2 in bearish_pairs:
    line = [
        (df_plot.index[i1], df_plot['High'].iloc[i1] + 1),
        (df_plot.index[i2], df_plot['High'].iloc[i2] + 1)
    ]
    divergence_lines.append(line)

# สร้าง addplot สำหรับ RSI
rsi_plot = mpf.make_addplot(df_plot['RSI'], 
                           panel=1,
                           color='purple',
                           ylabel='RSI',
                           secondary_y=False)

# สร้างเส้นแนวนอนสำหรับ RSI
rsi_overbought = mpf.make_addplot([70] * len(df_plot), 
                                 panel=1,
                                 color='red',
                                 linestyle='--',
                                 secondary_y=False)

rsi_oversold = mpf.make_addplot([30] * len(df_plot), 
                               panel=1,
                               color='green', 
                               linestyle='--',
                               secondary_y=False)

# พล็อตกราฟทั้งหมด
fig, axes = mpf.plot(df_plot,
         type='candle',
         style='charles',
         title=f'\n{SYMBOL} - วิธีที่ 1 -- Candlestick with Divergence\n',
         addplot=[rsi_plot, rsi_overbought, rsi_oversold],
         alines=dict(alines=divergence_lines, colors=['green', 'red'], linewidths=2),
         volume=False,
         figratio=(12, 8),
         panel_ratios=(2, 1),
         returnfig=True)
axes[0].set_ylabel('Price!!!')
axes[2].set_ylabel('RSI...')
plt.show()

print("✅ สร้างกราฟสำเร็จ!")
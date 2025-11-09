import pandas as pd
import numpy as np
from scipy import stats  # สำหรับคำนวณ percentile
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import yfinance as yf
from sklearn.linear_model import LinearRegression
import os
import base64
from io import BytesIO

def create_plot(stock_data, ticker):
    # ตั้งค่าฟอนต์ไทยและขนาดกราฟ
    plt.rcParams['font.family'] = 'Tahoma'
    plt.rcParams['font.size'] = 14  # เพิ่มขนาดฟอนต์
    
    # สร้างกราฟขนาดใหญ่ (20x10 นิ้ว) สำหรับโหมดเต็มจอ
    plt.figure(figsize=(20, 10))
    
    # ปรับ margins ให้ใช้พื้นที่ได้เต็มที่
    plt.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.1)
    
    # สร้างเส้นกราฟ
    plt.plot(stock_data['Close'], label='ราคาปิด', color='blue', linewidth=3)
    if 'MA_5' in stock_data:
        plt.plot(stock_data['MA_5'], label='MA 5 วัน', color='orange', linewidth=2)
    if 'MA_20' in stock_data:
        plt.plot(stock_data['MA_20'], label='MA 20 วัน', color='green', linewidth=2)
    
    # ตั้งค่า Title และป้ายแกน
    plt.title(f'แนวโน้มราคาหุ้น {ticker}', pad=25, fontsize=18, fontweight='bold')
    plt.xlabel('วันที่', labelpad=15, fontsize=14)
    plt.ylabel('ราคา', labelpad=15, fontsize=14)
    
    # ตั้งค่า legend และ grid
    plt.legend(loc='upper left', fontsize=12, framealpha=0.7)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # ปรับขนาด ticks ให้อ่านง่าย
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=12)
    
    # บันทึกกราฟด้วยความละเอียดสูง
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return plot_data

def prepare_plotly_data(stock_data, ticker):
    """เตรียมข้อมูลสำหรับ Plotly.js"""
    import plotly.graph_objects as go
    from plotly.utils import PlotlyJSONEncoder
    import json
    
    print(type(stock_data))
    print(stock_data.columns)
    print(stock_data)

    # แปลง DatetimeIndex เป็น string สำหรับแกน X
    dates = stock_data.index.strftime('%Y-%m-%d').tolist()
    #dates = stock_data.index.astype(str).tolist()
    #close_prices = stock_data['Close'].values.tolist()
    close_prices = stock_data['Close'].tolist()

    # สร้างเส้นกราฟ
    fig = go.Figure()
    
    # เพิ่มเส้นราคาปิด
    fig.add_trace(go.Scatter(
        x=dates,
        y=close_prices,
        name='ราคาปิด',
        line=dict(color='blue', width=2),
        mode='lines'
    ))
    
    # เพิ่มเส้นค่าเฉลี่ยเคลื่อนที่ถ้ามี
    if 'MA_5' in stock_data:
        fig.add_trace(go.Scatter(
            x=dates,
            y=stock_data['MA_5'].tolist(),
            name='MA 5 วัน',
            line=dict(color='orange', width=1.5)
        ))
    
    if 'MA_20' in stock_data:
        fig.add_trace(go.Scatter(
            x=dates,
            y=stock_data['MA_20'].tolist(),
            name='MA 20 วัน',
            line=dict(color='green', width=1.5)
        ))

    if 'MA_200' in stock_data:
        fig.add_trace(go.Scatter(
            x=dates,
            y=stock_data['MA_200'].tolist(),
            name='MA 200 วัน',
            line=dict(color='pink', width=1.5)
        ))

    # เพิ่มปริมาณซื้อขาย (Y-axis ด้านขวา)
    fig.add_trace(go.Bar(
        x=dates,
        y=stock_data['Volume'],
        name='ปริมาณซื้อขาย',
        marker=dict(color='rgba(200, 200, 200, 0.5)'),
        yaxis='y2'
    ))
    # เพิ่มเส้นค่าเฉลี่ยปริมาณซื้อขาย
    fig.add_trace(go.Scatter(
        x=dates,
        y=stock_data['Volume_MA_20'],
        name='Volume MA 20',
        line=dict(color='red', width=1, dash='dot'),
        yaxis='y2'
    ))

    # ปรับแต่งเลย์เอาต์ให้แสดงแกน Y ในแนวตั้ง
    fig.update_layout(
        title=f'<b>แนวโน้มราคาและปริมาณซื้อขาย {ticker}</b>',
        xaxis_title='วันที่',
        yaxis_title='ราคา',
        yaxis=dict(
            autorange=True,
            showgrid=True,
            zeroline=False,
            fixedrange=False  # อนุญาตให้ซูมในแนวตั้ง
        ),
        xaxis=dict(
            autorange=True,
            showgrid=True
        ),
        hovermode='x unified',
        height=600
    )
    
    return fig.to_json()

def analyze_stock_trend2(ticker, start_date, end_date):
    try:
        # ดึงข้อมูลราคาหุ้นจาก Yahoo Finance
        stock_data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, actions=False)        
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = stock_data.columns.get_level_values(0)
        print("โครงสร้าง columns:", stock_data.columns)
        print("ประเภทข้อมูล Close:", type(stock_data['Close']))
        print("ตัวอย่างข้อมูล Close:", stock_data['Close'].head())
        if len(stock_data) == 0:
            print(f"ไม่พบข้อมูลสำหรับหุ้น {ticker} ในช่วงวันที่กำหนด")
            return
        
        # คำนวณค่าเฉลี่ยเคลื่อนที่ (Moving Average)
        stock_data['MA_5'] = stock_data['Close'].rolling(window=5).mean()
        stock_data['MA_20'] = stock_data['Close'].rolling(window=20).mean()
        stock_data['MA_200'] = stock_data['Close'].rolling(window=200).mean()

        stock_data['Volume_MA_20'] = stock_data['Volume'].rolling(window=20).mean()
        stock_data['Volume_Ratio'] = stock_data['Volume'] / stock_data['Volume_MA_20']

        # คำนวณ Momentum (เปอร์เซ็นต์การเปลี่ยนแปลงจาก 5 วันก่อน)
        stock_data['Momentum'] = (stock_data['Close'] / stock_data['Close'].shift(5) - 1) * 100

        # คำนวณ Bollinger Bands
        #stock_data['Upper_Band'] = stock_data['MA_20'] + (2 * stock_data['Close'].rolling(window=20).std())
        rolling_std_20 = stock_data['Close'].rolling(window=20).std()
        stock_data['Upper_Band'] = stock_data['MA_20'] + (2 * rolling_std_20)
        stock_data['Lower_Band'] = stock_data['MA_20'] - (2 * stock_data['Close'].rolling(window=20).std())
        # คำนวณ Percentile (เปรียบเทียบกับ 1 ปีย้อนหลัง)
        latest_close = stock_data['Close'].iloc[-1]
        one_year_data = stock_data['Close'].tail(252)  # 252 วันทำการใน 1 ปี
        percentile = stats.percentileofscore(one_year_data, latest_close)
        # วิเคราะห์ระดับราคา
        price_zone = {
            'latest_price': latest_close,
            'ma200': stock_data['MA_200'].iloc[-1],
            'percentile': percentile,
            'bollinger_position': None,
            'zone_analysis': None
        }

        latest = {
            'price': stock_data['Close'].iloc[-1],
            'volume': stock_data['Volume'].iloc[-1],
            'volume_ma20': stock_data['Volume_MA_20'].iloc[-1],
            'volume_ratio': stock_data['Volume_Ratio'].iloc[-1],
            'ma5': stock_data['MA_5'].iloc[-1],
            'ma20': stock_data['MA_20'].iloc[-1],
            'ma200': stock_data['MA_200'].iloc[-1]
        }
        volume_analysis = {
            'normal_range': (0.8, 1.2),  # ปริมาณปกติอยู่ระหว่าง 80%-120% ของค่าเฉลี่ย
            'abnormal_volume': latest['volume_ratio'] > 1.5 or latest['volume_ratio'] < 0.5,
            'volume_signal': None,
            'trend_confirmation': None
        }
        # วิเคราะห์ตำแหน่งเทียบ Bollinger Bands
        if latest_close > stock_data['Upper_Band'].iloc[-1]:
            price_zone['bollinger_position'] = 'above_upper'
        elif latest_close < stock_data['Lower_Band'].iloc[-1]:
            price_zone['bollinger_position'] = 'below_lower'
        else:
            price_zone['bollinger_position'] = 'within_bands'
        
        # วิเคราะห์โซนราคา (ใช้ทั้ง MA200 และ Percentile)
        if (latest_close < stock_data['MA_200'].iloc[-1]) and (percentile < 30):
            price_zone['zone_analysis'] = 'undervalued'
        elif (latest_close > stock_data['MA_200'].iloc[-1]) and (percentile > 70):
            price_zone['zone_analysis'] = 'overvalued'
        else:
            price_zone['zone_analysis'] = 'fair_value'

        # วิเคราะห์แนวโน้มด้วยการถดถอยเชิงเส้น
        X = np.array(range(len(stock_data))).reshape(-1, 1)
        y = stock_data['Close'].values
        model = LinearRegression().fit(X, y)
        trend_slope = model.coef_[0]
        
        # วิเคราะห์สัญญาณ
        latest_close = float(stock_data['Close'].iloc[-1])
        latest_ma5 = float(stock_data['MA_5'].iloc[-1])
        latest_ma20 = float(stock_data['MA_20'].iloc[-1])
        latest_momentum = float(stock_data['Momentum'].iloc[-1])
        
        # เงื่อนไขการปรับตัวขึ้น
        bullish_conditions = [
            latest_close > latest_ma20,  # ราคาปิดเหนือ MA20
            latest_ma5 > latest_ma20,   # MA5 อยู่เหนือ MA20
            trend_slope > 0,            # แนวโน้มเป็นขาขึ้น
            latest_momentum > 0        # Momentum เป็นบวก
        ]
        
        bullish_score = sum(bullish_conditions)
        result = {
            'stock_data': stock_data,  # เพิ่มข้อมูลดิบสำหรับใช้ใน Plotly
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'latest_close': latest_close,
            'ma5': latest_ma5,
            'ma20': latest_ma20,
            'momentum': latest_momentum,
            'trend_slope': trend_slope,
            'bullish_score': bullish_score,
            'trend': 'ขาขึ้น' if trend_slope > 0 else 'ขาลง',
            'price_zone': price_zone,
            'latest': latest,
            'volume_analysis': volume_analysis,
            'analysis': '',
            'success': True
        }
        
        if bullish_score >= 3:
            result['analysis'] = 'ปรับตัวขึ้น (Bullish)'
        elif bullish_score >= 2:
            result['analysis'] = 'มีโอกาสปรับตัวขึ้น'
        else:
            result['analysis'] = 'ยังไม่มีการปรับตัวขึ้นชัดเจน'
        
        # แสดงผลการวิเคราะห์
        print(f"\nผลการวิเคราะห์หุ้น {ticker} (วันที่ {start_date} ถึง {end_date})")
        print("----------------------------------------")
        print(f"ราคาปิดล่าสุด: {latest_close:.2f}")
        print(f"MA5: {latest_ma5:.2f}, MA20: {latest_ma20:.2f}")
        print(f"Momentum (5 วัน): {latest_momentum:.2f}%")
        print(f"แนวโน้มโดยรวม: {'ขาขึ้น' if trend_slope > 0 else 'ขาลง'} ")
        print(f"คะแนนแนวโน้มขาขึ้น: {bullish_score}/4")
        
        if bullish_score >= 3:
            print("--> แนวโน้ม: ปรับตัวขึ้น (Bullish)")
        elif bullish_score >= 2:
            print("--> แนวโน้ม: มีโอกาสปรับตัวขึ้น")
        else:
            print("--> แนวโน้ม: ยังไม่มีการปรับตัวขึ้นชัดเจน")
                
        return result, bullish_score
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        return None, 0


# ตัวอย่างการใช้งาน
if __name__ == "__main__":
    print("โปรแกรมวิเคราะห์แนวโน้มราคาหุ้นปรับตัวขึ้น")
    
    # รับค่าจากผู้ใช้
    ticker = 'AAPL'
    start_date = '2024-01-01'
    end_date = '2025-01-31'
    
    # เรียกใช้ฟังก์ชันวิเคราะห์
    #data, score = analyze_stock_trend(ticker, start_date, end_date)
    analysis_result, score = analyze_stock_trend2(ticker, start_date, end_date)
    print(analysis_result['stock_data'])
    #print(analysis_result['stock_data'])        
    # เตรียมข้อมูลสำหรับ Plotly
    graphJSON = prepare_plotly_data(analysis_result['stock_data'], ticker)
    create_plot(analysis_result['stock_data'], ticker)

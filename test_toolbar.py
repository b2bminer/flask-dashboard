import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
from io import BytesIO
import base64
import random
from datetime import datetime, timedelta

# เพิ่ม import สำหรับ PyQt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
import sys

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

# ฟังก์ชันสร้างข้อมูลตัวอย่าง
def create_sample_data(symbol="TEST", periods=100):
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='15min')
    np.random.seed(42)
    prices = np.cumsum(np.random.randn(periods)) + 100
    
    data = {
        'Open': prices + np.random.uniform(-1, 1, periods),
        'High': prices + np.random.uniform(0, 2, periods),
        'Low': prices + np.random.uniform(-2, 0, periods),
        'Close': prices,
        'Volume': np.random.randint(1000, 10000, periods)
    }
    df = pd.DataFrame(data, index=dates)
    df['Ema5'] = df['Close'].ewm(span=5).mean()
    df['Ema20'] = df['Close'].ewm(span=20).mean()
    df['Rsi'] = np.random.uniform(30, 70, periods)
    return df

# Main Window สำหรับแสดงกราฟ
class StockChartWindow(QMainWindow):
    def __init__(self, symbol="TEST", tf="15m", max_bars=100):
        super().__init__()
        self.symbol = symbol
        self.tf = tf
        self.max_bars = max_bars
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(f"{self.symbol} {self.tf} Chart")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # สร้าง figure และ axes
        self.fig, self.axes = self.create_chart()
        self.main_ax = self.axes[0]
        
        # สร้าง canvas
        self.canvas = FigureCanvasQTAgg(self.fig)
        
        # สร้าง custom toolbar
        self.toolbar = CustomToolbar(self.canvas, self, self.my_custom_home_function)
        
        # เพิ่ม widget ลง layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # เก็บค่าเริ่มต้นของแกน
        self.initial_limits = {
            "xlim": self.main_ax.get_xlim(),
            "ylim": self.main_ax.get_ylim()
        }

        self.tooltip = self.main_ax.annotate(
            text="",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9, pad=0.4),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
            fontsize=10,
            visible=False
        )
        self.press_event = {'x': None, 'y': None}
        self.vline = self.main_ax.axvline(x=np.nan, linestyle='--', alpha=0.35)

        self.connect_events()
    
    def create_chart(self):
        # สร้างข้อมูลตัวอย่าง
        df = create_sample_data(self.symbol, self.max_bars)
        
        # สไตล์การแสดงผล
        mc = mpf.make_marketcolors(up='lime', down='red', edge='black', wick='black', volume='blue')
        style = mpf.make_mpf_style(marketcolors=mc, gridstyle=':')
        
        # Addplots
        apds = [
            mpf.make_addplot(df['Ema5'], color='brown', width=1.5, panel=0, label='EMA5'),
            mpf.make_addplot(df['Ema20'], color='purple', width=1.5, panel=0, label='EMA20'),
            mpf.make_addplot(df['Volume'].rolling(5).mean(), color='black', panel=1),
            mpf.make_addplot(df['Rsi'], color='blue', panel=2),
            mpf.make_addplot([30]*len(df), color='green', linestyle='--', panel=2),
            mpf.make_addplot([70]*len(df), color='red', linestyle='--', panel=2),
        ]
        
        title = f"{self.symbol} {self.tf} Timeframe"
        
        # สร้าง figure
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=style,
            addplot=apds,
            volume=True,
            figsize=(24, 12),
            panel_ratios=(10, 1, 1),
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
        self.df = df
        self.interactive_mode = False

        return fig, axes

    def connect_events(self):
        """เชื่อมต่อ events ต่างๆ"""
        # Tooltip movement
        self.canvas.mpl_connect('motion_notify_event', self.on_move)
        
        # Pan events
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        
        # Zoom events
        self.canvas.mpl_connect('scroll_event', self.on_zoom)
        
        # Double click to reset
        self.canvas.mpl_connect('button_press_event', self.on_double_click)

    def check_pan_state(self):
        """ตรวจสอบสถานะ Pan/Zoom จาก Toolbar และแสดงค่า debug"""
        try:
            print(f"[DEBUG] Toolbar actions: {list(self.toolbar._actions.keys())}")

            pan_active = self.toolbar._actions.get('pan')
            zoom_active = self.toolbar._actions.get('zoom')

            if pan_active and pan_active.isChecked():
                print("[DEBUG] Pan mode: ON")
                self.interactive_mode = True
            elif zoom_active and zoom_active.isChecked():
                print("[DEBUG] Zoom mode: ON")
                self.interactive_mode = True
            else:
                print("[DEBUG] Pan/Zoom: OFF")
                self.interactive_mode = False

        except Exception as e:
            print(f"[DEBUG] Error while checking pan/zoom state: {e}")
            self.interactive_mode = False

    def on_move(self, event):
        """จัดการการเคลื่อนไหวของเมาส์สำหรับ tooltip"""
        self.check_pan_state()
        print(f"[DEBUG] interactive_mode = {getattr(self, 'interactive_mode', None)}")
        if getattr(self, 'interactive_mode', False):
            return

        if event.inaxes != self.main_ax or event.xdata is None:
            self.tooltip.set_visible(False)
            self.vline.set_xdata([np.nan])  # ซ่อนเส้นแนวตั้ง
            self.canvas.draw()
            return
        
        x = int(round(event.xdata))
        if 0 <= x < len(self.df):
            dt = self.df.index[x]
            row = self.df.iloc[x]
            self.tooltip.xy = (x, row['Close'])
            self.tooltip.set_text(
                f"{dt.strftime('%Y-%m-%d %H:%M')}\n"
                f"O:{row['Open']:.2f} H:{row['High']:.2f}\n"
                f"L:{row['Low']:.2f} C:{row['Close']:.2f}\n"
                f"EMA5:{row['Ema5']:.2f} EMA20:{row['Ema20']:.2f}"
            )
            self.tooltip.set_visible(True)
            
            # แสดงเส้นแนวตั้งที่ตำแหน่งเมาส์
            self.vline.set_xdata([x])
            
            self.canvas.draw()
    
    def on_press(self, event):
        """เมื่อกดเมาส์"""
        if event.inaxes == self.main_ax and event.button == 1:  # left click
            self.press_event = {'x': event.xdata, 'y': event.ydata}
    
    def on_motion(self, event):
        """เมื่อลากเมาส์"""
        if self.press_event['x'] is None or event.inaxes != self.main_ax:
            return
        
        # ตรวจสอบว่าไม่ใช่โหมด Pan จาก toolbar
        self.check_pan_state()
        print(f"[DEBUG] interactive_mode = {getattr(self, 'interactive_mode', None)}")
        if getattr(self, 'interactive_mode', False):
            return
        
        dx = self.press_event['x'] - event.xdata
        dy = self.press_event['y'] - event.ydata
        
        cur_xlim = self.main_ax.get_xlim()
        cur_ylim = self.main_ax.get_ylim()
        
        self.main_ax.set_xlim(cur_xlim[0] + dx, cur_xlim[1] + dx)
        self.main_ax.set_ylim(cur_ylim[0] + dy, cur_ylim[1] + dy)
        
        self.canvas.draw()
    
    def on_release(self, event):
        """เมื่อปล่อยเมาส์"""
        self.press_event = {'x': None, 'y': None}
    
    def on_zoom(self, event):
        """เมื่อ scroll เมาส์"""
        if event.inaxes != self.main_ax:
            return
        
        base_scale = 1.1
        cur_xlim = self.main_ax.get_xlim()
        cur_ylim = self.main_ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        
        if event.button == 'up':  # Zoom in
            scale_factor = 1 / base_scale
        elif event.button == 'down':  # Zoom out
            scale_factor = base_scale
        else:
            return
        
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        
        self.main_ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.main_ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        
        self.canvas.draw()
    
    def on_double_click(self, event):
        """เมื่อ double click"""
        if event.dblclick and event.inaxes == self.main_ax:
            self.my_custom_home_function()
    

    def my_custom_home_function(self):
        """ฟังก์ชัน custom ที่จะถูกเรียกเมื่อกดปุ่ม Home"""
        print("✅ Custom Home function called!")
        print("Resetting view to initial limits...")
        
        # รีเซ็ตการแสดงผล
        self.axes[0].set_xlim(self.initial_limits["xlim"])
        self.axes[0].set_ylim(self.initial_limits["ylim"])
        
        # อัพเดท title
        self.axes[0].set_title(f"{self.symbol} {self.tf} - Reset View")
        
        # วาดใหม่
        self.canvas.draw()
        
        print("View reset completed!")


def plot_tf15m_pyqt(SYMBOL: str = "TEST", tf: str = "15m", max_bars: int = 100):
    """ฟังก์ชันหลักที่ใช้ PyQt backend"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # สร้างหน้าต่าง
    window = StockChartWindow(SYMBOL, tf, max_bars)
    window.show()
    
    # รัน application
    if QApplication.instance():
        app.exec_()
    
    # ส่งกลับ base64 image (optional)
    buf = BytesIO()
    window.fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

if __name__ == "__main__":
    print("Testing PyQt custom home button...")
    
    # ทดสอบตัวอย่างง่ายๆ ก่อน
    print("\n1. Testing simple PyQt example:")
    #simple_pyqt_example()
    
    # หรือทดสอบแบบเต็ม
    print("\n2. Testing full stock chart:")
    plot_tf15m_pyqt("TASCO", "15m", 150)

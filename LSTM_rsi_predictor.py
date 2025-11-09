import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import talib
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

import matplotlib
matplotlib.use('Agg')  # fix error RuntimeError: main thread is not in main loop
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64

DATA_DIR = "D:/python_prog/Flask/Odoo/data"

class RSIPredictor:
    def __init__(self, symbol='AOT', look_back=60):
        self.symbol = symbol
        self.look_back = look_back
        self.scaler = MinMaxScaler()
        self.model = None

    def get_stock_data(self, symbol, tf, from_ts=None, to_ts=None):
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

    def fetch_stock_data(self):
        stock_data = self.get_stock_data(self.symbol, 'D')
        if stock_data is None:
            print(f"ไม่สามารถโหลดข้อมูลหุ้นได้ {self.symbol}")
            return None

        print(f'symbol: {self.symbol}')
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = stock_data.columns.get_level_values(0)
        df = stock_data
        df.sort_values('time', inplace=True)
        df['RSI'] = talib.RSI(df['close'])
        df['MACD'], df['MACD_signal'], _ = talib.MACD(df['close'])
        return df

    def create_dataset(self, data, look_back=60):
        X, y = [], []
        for i in range(len(data)-look_back-1):
            X.append(data[i:(i+look_back), 0])  # ข้อมูลจาก t-look_back ถึง t
            y.append(data[i + look_back + 1, 0])  # ราคาใน t+1 (ล่วงหน้า 1 วัน)
        return np.array(X), np.array(y)

    def check_nan_in_X(self, X, data):
        """ตรวจสอบและแสดงวันที่ที่มีค่า NaN ใน X พร้อมคอลัมน์ที่เกี่ยวข้อง"""
        # ตรวจสอบตำแหน่งที่มี NaN ใน X
        nan_positions = np.where(np.isnan(X))
        
        if len(nan_positions[0]) == 0:
            print("ไม่มีค่า NaN ใน X")
            return
        
        print("\n=== ตรวจพบค่า NaN ใน X ===")
        print(f"จำนวน NaN ที่พบ: {len(nan_positions[0])} ตำแหน่ง")
        
        # เตรียมข้อมูลวันที่และค่าที่เกี่ยวข้อง
        results = []
        for i in range(len(nan_positions[0])):
            sample_idx = nan_positions[0][i]  # ดัชนีตัวอย่างใน X
            timestep = nan_positions[1][i]    # ดัชนี timestep ใน look_back
            
            # คำนวณวันที่ที่เกี่ยวข้อง
            date = data['date'].iloc[sample_idx + timestep]
            
            # ดึงค่า RSI ดั้งเดิม
            rsi_value = data['RSI'].iloc[sample_idx + timestep]
            
            results.append({
                'ตัวอย่างที่': sample_idx,
                'วันย้อนหลังที่': timestep + 1,  # นับจาก 1 แทน 0
                'วันที่': date,
                'ค่า RSI': rsi_value,
                'ตำแหน่งใน X': f"X[{sample_idx},{timestep},0]"
            })
        
        # สร้าง DataFrame เพื่อแสดงผล
        df_nan_report = pd.DataFrame(results)
        
        # แสดงผลลัพธ์แบบละเอียด
        pd.set_option('display.max_rows', None)
        print("\nรายละเอียดค่า NaN:")
        print(df_nan_report[['วันที่', 'ค่า RSI', 'ตัวอย่างที่', 'วันย้อนหลังที่']])
        
        # แสดงตัวอย่างข้อมูลที่เกี่ยวข้อง
        print("\nตัวอย่างข้อมูลที่พบปัญหา:")
        sample_idx = nan_positions[0][0]
        print(f"\nข้อมูลใน X[{sample_idx}]:")
        print(X[sample_idx])
        
        # แสดงข้อมูลดิบจาก DataFrame
        print(f"\nข้อมูลดิบรอบวันที่ {df_nan_report['วันที่'].iloc[0]}:")
        start_idx = max(0, sample_idx - 2)
        end_idx = min(len(data), sample_idx + 3)
        print(data[['date', 'RSI', 'close']].iloc[start_idx:end_idx])

    def prepare_data(self):
        data = self.fetch_stock_data()
        if data is None:
            return None, None, None

        data = data.dropna(subset=['RSI']) # กรองข้อมูลที่มีค่า NaN ออกก่อนสร้างชุดข้อมูล
        #data['RSI'] = data['RSI'].fillna(method='ffill')  # เติมค่า RSI ด้วยค่าก่อนหน้า

        rsi_values = data['RSI'].values.reshape(-1, 1)
        scaled_rsi = self.scaler.fit_transform(rsi_values)
        X, y = self.create_dataset(scaled_rsi, self.look_back)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        return X, y, data

        #ความสัมพันธ์ระหว่างข้อมูล
        #วันที่	   ข้อมูลใน X (Input)	            ข้อมูลใน y (Target)	ข้อมูลใน data
        #1-60	X[0] = [RSI(1), ..., RSI(60)]	y[0] = RSI(61)	data.iloc[0:60]
        #2-61	X[1] = [RSI(2), ..., RSI(61)]	y[1] = RSI(62)	data.iloc[1:61]

    def build_model(self):
        model = Sequential()
        model.add(LSTM(50, return_sequences=True, input_shape=(self.look_back, 1)))
        model.add(Dropout(0.2))
        model.add(LSTM(50))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def train_model(self, X, y, epochs=50, batch_size=32):
        self.model = self.build_model()
        history = self.model.fit(X, y, epochs=epochs, batch_size=batch_size, validation_split=0.2)
        return history

    def predict(self, X):
        if self.model is None:
            raise ValueError("Model has not been trained yet")
        return self.model.predict(X)

    def generate_plot(self, y_true, y_pred, dates):
        # เลือกเฉพาะ 10 วันล่าสุด
        last_10_days = -10  
        y_true_last10 = y_true[last_10_days:]
        y_pred_last10 = y_pred[last_10_days:]
        dates_last10 = dates[self.look_back+1:][last_10_days:]

        actual_dates = dates_last10
        pred_dates = pd.to_datetime(dates_last10[1:10])
        last_pred_date = pred_dates[-1] + pd.Timedelta(days=1)
        pred_dates = np.append(pred_dates, pd.DatetimeIndex([last_pred_date]))
        print('pred_dates:', pred_dates)
        print('dates_last10:', dates_last10)

        # คำนวณ RMSE
        rmse = np.sqrt(np.mean((y_true_last10[1:] - y_pred_last10[:-1])**2))
        print(f"RMSE last10: {rmse:.4f}")

        # สร้างกราฟ
        plt.figure(figsize=(12, 6))
        plt.plot(actual_dates, y_true_last10, label='Actual RSI', color='blue', marker='o')
        #plt.plot(pred_dates, y_pred_last10, label='Predicted RSI (t+1)', color='red', linestyle='--', marker='x')
        plt.plot(pred_dates, y_pred_last10[0:10], label='Predicted RSI (t+1)', color='red', linestyle='--', marker='x')
        last_pred_date = pred_dates[-1] + pd.Timedelta(days=1)
        plt.plot(last_pred_date, y_pred_last10[-1], 'ro', markersize=8, label='Next Day Prediction')

        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

        plt.title(f'{self.symbol} 1-Day Ahead RSI Prediction')
        plt.xlabel('Date')
        plt.ylabel('RSI')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')

        
    def run(self):
        X, y, data = self.prepare_data()
        if X is None:
            return None, "Failed to load data"
        
        self.check_nan_in_X(X, data)  #ตรวจสอบข้อมูลอินพุต (X) มีค่า NaN

        # ดูข้อมูลตัวอย่าง
        print("\nตรวจสอบข้อมูลอินพุต (X) มีค่า NaN")
        print(np.isnan(X).any()) #ตรวจสอบข้อมูลอินพุต (X) มีค่า NaN
        print("\nตัวอย่าง X[-1]:")
        print(X[-1])  # ค่า RSI ย้อนหลัง 60 วันแรก (ปรับสเกลแล้ว)

        print("\nตัวอย่าง y[-1]:")
        print(y[-1])  # ค่า RSI ของวันที่ 61

        print("\nตัวอย่างข้อมูลดิบ:")
        print(data[['date', 'RSI']].tail())

        self.train_model(X, y)
        y_pred = self.predict(X)
        #ข้อมูล y_pred = [
        #    [0.52],  # ทำนาย RSI ของวันที่ 61
        #    [0.48],  # ทำนาย RSI ของวันที่ 62
        #    ... ]

        # ปรับสเกลกลับเป็นค่า RSI จริง
        y_true = self.scaler.inverse_transform(y.reshape(-1, 1))
        y_pred = self.scaler.inverse_transform(y_pred)
        print( y_pred[:5])
        print(len(y_pred))
        for i in range(len(y_pred)):
            print(f"วันที่ {data['date'].iloc[i+self.look_back+1]} | ค่าจริง: {y_true[i][0]:.1f} | ทำนาย: {y_pred[i][0]:.1f}")

        # แปลงคอลัมน์ 'date' เป็น datetime
        data['date'] = pd.to_datetime(data['date'])
        dates = data['date'].values[self.look_back+1:]

        # สร้างและส่งกลับกราฟ
        plot_base64 = self.generate_plot(y_true, y_pred, dates)
        return plot_base64, None

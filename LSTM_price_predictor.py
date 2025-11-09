import numpy as np
import pandas as pd
import talib
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.metrics import mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

import matplotlib
matplotlib.use('Agg')  # fix error RuntimeError: main thread is not in main loop
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import io
import base64

DATA_DIR = "D:/python_prog/Flask/Odoo/data"

class PricePredictor:
    def __init__(self):
        self.look_back = 60
        #self.scaler = MinMaxScaler()
        self.close_scaler = MinMaxScaler()  # Scaler เฉพาะ close price
        self.features_scaler = MinMaxScaler()  # สำหรับราคาและ Indicators
        self.volume_scaler = StandardScaler()  # สำหรับ Volume
        self.model = None
    
    def get_stock_data(self, symbol, tf='D', from_ts=None, to_ts=None):
        # โหลดไฟล์ข้อมูลตาม timeframe
        DATA_DIR = "D:/python_prog/Flask/Odoo/data"
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

    def fetch_stock_data(self, symbol):
        stock_data = self.get_stock_data(symbol, 'D')
        if stock_data is None:
            print(f"ไม่สามารถโหลดข้อมูลหุ้นได้ {symbol}")
            return None, "ไม่สามารถโหลดข้อมูลหุ้นได้"

        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = stock_data.columns.get_level_values(0)
        df = stock_data
        df.sort_values('time', inplace=True)
        df['RSI'] = talib.RSI(df['close'])
        df['MACD'], df['MACD_signal'], _ = talib.MACD(df['close'])
        return df, None

    def prepare_data(self, symbol):
        try:
            data, error = self.fetch_stock_data(symbol)
            if error:
                return None, None, None, None, None, error

            data['date'] = pd.to_datetime(data['date'])
            data = data.set_index('date')

            # เพิ่ม Features
            data['MA_5'] = data['close'].rolling(5).mean()
            data['RSI_14'] = talib.RSI(data['close'], timeperiod=14)
            data['MACD'], _, _ = talib.MACD(data['close'])
            data['Volume_MA_5'] = data['volume'].rolling(5).mean()  # ปริมาณซื้อขายเฉลี่ย 5 วัน
            data['Volume_Change'] = data['volume'].pct_change()     # % การเปลี่ยนแปลง Volume
            data['Volume_SMA_Ratio'] = data['volume'] / data['Volume_MA_5']  # อัตราส่วน Volume ต่อค่าเฉลี่ย
            data = data.dropna()

            close_prices = data['close'].values.reshape(-1, 1)
            self.close_scaler.fit(close_prices)  # ฝึกเฉพาะ close price

            # เลือก Features ที่จะใช้ (close, open, volume, Indicators)
            features = data[['close', 'open', 'MA_5', 'RSI_14', 'MACD', 
                        'volume', 'Volume_MA_5', 'Volume_Change', 'Volume_SMA_Ratio']]
        
            # ลบแถวที่มีค่า NaN (จาก Indicators)
            features = features.dropna()

            price_features = features[['close', 'open', 'MA_5', 'RSI_14', 'MACD']]
            scaled_price = self.features_scaler.fit_transform(price_features)

            # ปรับสเกล Features กลุ่ม Volume
            volume_features = features[['volume', 'Volume_MA_5', 'Volume_Change', 'Volume_SMA_Ratio']]
            scaled_volume = self.volume_scaler.fit_transform(volume_features)

            # รวม Features ที่ปรับสเกลแล้ว
            #scaled_features = np.concatenate([scaled_price, scaled_volume], axis=1)
            scaled_features = scaled_price

            # สร้างชุดข้อมูล
            X, y = [], []
            n_features = features.shape[1]  # จำนวน Features (6)

            for i in range(self.look_back, len(scaled_features)-1):
                X.append(scaled_features[i-self.look_back:i, :])  # ใช้ numpy indexing
                y.append(scaled_features[i+1, 0])  # ใช้ numpy indexing

            X = np.array(X)
            y = np.array(y)

            # แบ่ง Train/Test
            train_size = int(0.8 * len(X))
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            test_dates = data.index[train_size+self.look_back+1:]

            return X_train, X_test, y_train, y_test, test_dates, scaled_features, None
        except Exception as e:
            print(f"Error generating plot: {str(e)}")
            return None

    def build_model(self, scaled_features):
        try:
            self.model = Sequential([
                LSTM(128, return_sequences=True, input_shape=(self.look_back, scaled_features.shape[1])),
                Dropout(0.2),
                LSTM(64, return_sequences=False),
                Dense(32, activation='relu'),
                Dense(1)  # ทำนายราคาปิด (close)
            ])
            self.model.compile(optimizer='adam', loss='mse')
        except Exception as e:
            print(f"Error generating plot: {str(e)}")
            return None

    def train_model(self, X_train, y_train, X_test, y_test, epochs=50, batch_size=32):
        history = self.model.fit(X_train, y_train, 
                               epochs=epochs, 
                               batch_size=batch_size, 
                               validation_data=(X_test, y_test), 
                               verbose=0)
        return history

    def predict(self, X_test):
        return self.model.predict(X_test)

    def inverse_transform(self, data, feature='close'):
        """แปลงข้อมูลกลับสู่สเกลเดิม
        - feature: 'close', 'price_features', หรือ 'volume'
        """
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)

        if feature == 'close':
            if not hasattr(self.close_scaler, 'scale_'):
                raise ValueError("Close Scaler ยังไม่ได้ถูกฝึก!")
            return self.close_scaler.inverse_transform(data).flatten()
        elif feature == 'price_features':
            if not hasattr(self.features_scaler, 'scale_'):
                raise ValueError("Price Scaler ยังไม่ได้ถูกฝึก!")
            return self.features_scaler.inverse_transform(data)
        elif feature == 'volume':
            if not hasattr(self.volume_scaler, 'scale_'):
                raise ValueError("Volume Scaler ยังไม่ได้ถูกฝึก!")
            return self.volume_scaler.inverse_transform(data).flatten()
        else:
            raise ValueError("feature ต้องเป็น 'close', 'price_features', หรือ 'volume'")
    
    def create_plot(self, test_dates, symbol, y_test_actual, y_pred_actual, last_n=10):
        try:
            rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
            print(f"RMSE: {rmse:.4f}")  # แสดงผลใน Console

            plt.figure(figsize=(15,6))
            pred_dates = test_dates[-last_n:] + pd.Timedelta(days=1)  # เพิ่ม 1 วัน

            # Actual Price (วันที่ t+1)
            plt.plot(test_dates[-last_n:], y_test_actual[-last_n:], 'b-o', label='Actual Price (t+1)')

            # Predicted Price (ทำนายสำหรับ t+1)
            plt.plot(pred_dates, y_pred_actual[-last_n:], 'r--x', label='Predicted Price (t+1)')

            # เพิ่มจุดทำนายล่วงหน้าสุดท้าย
            last_pred_date = test_dates[-1] + pd.Timedelta(days=1)
            plt.plot(last_pred_date, y_pred_actual[-1], 'ro', markersize=8, label='Next Day Prediction')

            # ปรับรูปแบบแกน X
            ax = plt.gca()
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)

            plt.title(f'{symbol} LSTM Train/Test Dataset 1-Day Ahead Stock Price Prediction (RMSE = {rmse:.4f})')
            plt.legend()
            plt.grid()
            plt.tight_layout()
            filename = f"{symbol}_prediction_plot.png"
            plt.savefig(filename)
            # แปลง plot เป็น base64
            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Error generating plot: {str(e)}")
            return None
    
    def run(self, symbol='AOT'):
        try:
            # เตรียมข้อมูล
            X_train, X_test, y_train, y_test, test_dates, scaled_features, error = self.prepare_data(symbol)
            if error:
                return None, error

            print('1')
            # สร้างและฝึกโมเดล
            self.build_model(scaled_features)
            print('1.1')
            self.train_model(X_train, y_train, X_test, y_test)

            print('2')
            # ทำนายผล
            y_pred = self.predict(X_test)

            print('3 - Prediction done, y_pred shape:', y_pred.shape)
            try:
                print("Checking data before inverse transform...")
                print("y_test sample:", y_test[:5])
                print("y_pred sample:", y_pred[:5])
                
                y_test_actual = self.inverse_transform(y_test, 'close')
                y_pred_actual = self.inverse_transform(y_pred, 'close')
                
                print('4 - Inverse transform successful')
                print("y_test_actual sample:", y_test_actual[:5])
                print("y_pred_actual sample:", y_pred_actual[:5])
            except Exception as e:
                print(f"Error in inverse transform: {str(e)}")
                return None, f"Inverse transform error: {str(e)}"

            print('4')
            # สร้าง plot และแปลงเป็น base64
            try:
                plot_base64 = self.create_plot(test_dates, symbol, y_test_actual, y_pred_actual)
                #plot_base64 = self.generate_plot(symbol, y_test_actual, y_pred_actual, test_dates)
                if plot_base64 is None:
                    print("Failed to generate plot: returned None")
            except Exception as e:
                print(f"Plot generation error: {str(e)}")
            return plot_base64, None
            
        except Exception as e:
            return None, f"เกิดข้อผิดพลาด: {str(e)}"

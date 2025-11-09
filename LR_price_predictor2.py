import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import yfinance as yf

from fetch_stock_data import get_stock_data, fetch_stock_data

def prepareDataForLR(x_df, y_df, return_period, add_lags=True):
    # ตรวจสอบข้อมูล
    assert len(x_df) == len(y_df), "Data length mismatch"
    assert return_period > 0 and return_period < len(y_df), "Invalid return_period"
    
    # Reset index
    x_df = x_df.copy().reset_index(drop=True)
    y_df = y_df.copy().reset_index(drop=True)
    
    # เพิ่ม Lag Features (ถ้าต้องการ)
    if add_lags:
        for i in [1, 2, 3, 5, 10]:
            x_df[f'close_lag_{i}'] = y_df['Close'].shift(i)
    
    # เลื่อนข้อมูลเป้าหมาย
    y_df = y_df.shift(-return_period)
    
    # ตัดข้อมูลส่วนท้าย
    valid_idx = len(y_df) - return_period
    x_df = x_df.iloc[:valid_idx]
    y_df = y_df.iloc[:valid_idx]
    
    # ล้างข้อมูล NaN ที่เกิดจากการสร้าง features ใหม่
    if add_lags:
        x_df = x_df.dropna()
        y_df = y_df.loc[x_df.index]
    
    return x_df, y_df

def train_and_predict(X_train, y_train, X_test, return_period):
    # 1. สร้างและฝึกโมเดล
    print('3.1')
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    print('3.2')
    # 2. ทำนายผลบนชุดทดสอบ
    y_pred = model.predict(X_test)
    
    print('3.3')
    # 3. ทำนายอนาคต (return_period วันข้างหน้า)
    last_data_point = X_test.iloc[-1:]  # เก็บเป็น DataFrame แทน array
    future_predictions = []
    
    for _ in range(return_period):
        next_pred = float(model.predict(last_data_point)[0])  # แปลงเป็น float อย่างชัดเจน
        future_predictions.append(next_pred)
        
        # อัพเดท last_data_point สำหรับการทำนายขั้นถัดไป
        if 'close_lag_1' in X_train.columns:
            # ตรวจสอบจำนวนคอลัมน์ที่แท้จริง
            num_columns = last_data_point.shape[1]
            
            # อัพเดทเฉพาะคอลัมน์ที่มีอยู่จริง
            last_data_point.iloc[0, 0] = next_pred  # อัพเดท lag_1
            
            # ปรับ loop ให้ไม่เกินจำนวนคอลัมน์
            max_lag = min(10, num_columns)  # ไม่เกินจำนวนคอลัมน์ที่มี
            for i in range(2, max_lag + 1):
                if f'close_lag_{i}' in X_train.columns:
                    last_data_point.iloc[0, i-1] = last_data_point.iloc[0, i-2]  # ใช้ iloc แทนการเข้าถึงโดยตรง
    
    print('3.4')
    # 4. ประเมินโมเดล
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Evaluation:")
    print(f"- MSE: {mse:.4f}")
    print(f"- R-squared: {r2:.4f}")
    print(f"\nFuture Predictions (Next {return_period} days):")
    for i, price in enumerate(future_predictions, 1):
        print(f"Day {i}: {price:.2f}")
    
    return model, y_pred, future_predictions

def plot_predictions(date_series, y_train, y_test, y_pred, future_prices, return_period, start_date=None, full_dates=None, full_prices=None ):
    plt.figure(figsize=(12, 6))
    # แปลง index เป็นวันที่
    train_dates = date_series.iloc[y_train.index]
    test_dates = date_series.iloc[y_test.index]

    if start_date is not None:
        cutoff_date = pd.Timestamp(start_date)

        full_mask = full_dates >= cutoff_date
        train_mask = train_dates >= cutoff_date
        test_mask = test_dates >= cutoff_date

        full_dates = full_dates[full_mask]
        full_prices = full_prices[full_mask]

        train_dates = train_dates[train_mask]
        y_train = y_train[train_mask]

        test_dates = test_dates[test_mask]
        y_test = y_test[test_mask]
        y_pred = y_pred[test_mask]

    # สร้างวันที่สำหรับการทำนายอนาคต
    last_date = date_series.iloc[-1]
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=return_period
    )
    
    plt.plot(full_dates, full_prices, label='Close Price', color='grey')

    # พล็อตข้อมูลฝึกอบรม
    #plt.plot(train_dates, y_train, label='Training Data', color='blue')
    
    # พล็อตข้อมูลทดสอบจริง
    test_index = y_test.index
    #plt.plot(test_dates, y_test, label='Actual Prices', color='green')
    
    # พล็อตการทำนาย
    plt.plot(test_dates, y_pred, label='Predicted Prices', color='red', linestyle='--')
    
    # พล็อตการทำนายอนาคต
    future_index = range(test_index[-1]+1, test_index[-1]+1+return_period)
    plt.plot(future_dates, future_prices, 'o-', label='Future Predictions', color='purple')
    
    plt.title(f'{symbol} - Stock Price Prediction')
    plt.xlabel('Time Period')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    #plt.xlim(pd.Timestamp('2025-04-01'), None) #กำหนดให้กราฟแสดงเริ่มต้นวันที่ 2025-01-01
    plt.show()

def plot_predictions_dual(date_series, y_train, y_test, y_pred, future_prices, return_period, cutoff_date_str='2025-01-01'):
    cutoff_date = pd.Timestamp(cutoff_date_str)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharey=True)
    fig.subplots_adjust(hspace=0.3)

    # ===== เตรียมข้อมูล =====
    train_dates = date_series.iloc[y_train.index]
    test_dates = date_series.iloc[y_test.index]

    # ชุดข้อมูลสำหรับกราฟเต็ม
    train_full = train_dates
    y_train_full = y_train
    test_full = test_dates
    y_test_full = y_test
    y_pred_full = y_pred

    # ชุดข้อมูลสำหรับกราฟตัด
    train_mask = train_dates >= cutoff_date
    test_mask = test_dates >= cutoff_date

    train_cut = train_dates[train_mask]
    y_train_cut = y_train[train_mask]
    test_cut = test_dates[test_mask]
    y_test_cut = y_test[test_mask]
    y_pred_cut = y_pred[test_mask]

    # วันที่อนาคต (ใช้ร่วมกัน)
    last_date = date_series.iloc[-1]
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=return_period
    )

    # ===== กราฟ 1: ข้อมูลเต็ม =====
    axes[0].plot(train_full, y_train_full, label='Training Data', color='blue')
    axes[0].plot(test_full, y_test_full, label='Actual Prices', color='green')
    axes[0].plot(test_full, y_pred_full, label='Predicted Prices', color='red', linestyle='--')
    axes[0].plot(future_dates, future_prices, 'o-', label='Future Predictions', color='purple')
    axes[0].set_title(f'{symbol} - Full Date Range')
    axes[0].set_xlabel('Time Period')
    axes[0].set_ylabel('Price')
    axes[0].legend()
    axes[0].grid(True)

    # ===== กราฟ 2: ตัดตั้งแต่ cutoff_date =====
    axes[1].plot(train_cut, y_train_cut, label='Training Data', color='blue')
    axes[1].plot(test_cut, y_test_cut, label='Actual Prices', color='green')
    axes[1].plot(test_cut, y_pred_cut, label='Predicted Prices', color='red', linestyle='--')
    axes[1].plot(future_dates, future_prices, 'o-', label='Future Predictions', color='purple')
    axes[1].set_title(f'{symbol} - From {cutoff_date_str} Onwards')
    axes[1].set_xlabel('Time Period')
    axes[1].set_ylabel('Price')
    axes[1].legend()
    axes[1].grid(True)

    plt.show()

try:
    symbol = 'PTT'
    data, error = fetch_stock_data(symbol)
    print("Columns in data:", data.columns.tolist())
    print(data.describe())

    data.columns = data.columns.str.capitalize()
    data['Date'] = pd.to_datetime(data['Date'])
    data = data[['Date', 'Close']]  # ใช้เฉพาะราคาปิด
    data['Days'] = (data['Date'] - data['Date'].min()).dt.days # แปลงวันที่เป็นจำนวนวันเนื่องจากโมเดล Linear Regression ต้องการ input เป็นตัวเลขเท่านั้น
    data = data.reset_index()

    x_df=data[['Days']]
    y_df=data[['Close']]
    PREDICTION_PERIOD = 10

    # 1. เตรียมข้อมูล
    print('1')
    X_prepared, y_prepared = prepareDataForLR(x_df, y_df, return_period=PREDICTION_PERIOD)

    print('2')
    # 2. แบ่งข้อมูล
    split_point = int(len(X_prepared) * 0.8)
    X_train, X_test = X_prepared[:split_point], X_prepared[split_point:]
    y_train, y_test = y_prepared[:split_point], y_prepared[split_point:]

    print('3')
    # 3. ฝึกและทำนาย
    model, y_pred, future_prices = train_and_predict(X_train, y_train, X_test, return_period=PREDICTION_PERIOD)

    print('4')
    # 4. วิเคราะห์ผลลัพธ์
    date_series = data['Date']  # เก็บคอลัมน์วันที่ไว้ใช้พล็อตกราฟ
    plot_predictions(
        date_series=date_series,
        y_train=y_train,                  # ข้อมูลฝึกอบรม
        y_test=y_test,                    # ข้อมูลทดสอบจริง
        y_pred=y_pred,                    # ผลลัพธ์การทำนาย
        future_prices=future_prices,      # การทำนายอนาคต
        return_period=PREDICTION_PERIOD,
        full_dates=data['Date'],          # วันที่ทั้งหมด
        full_prices=data['Close']         # ราคาจริงทั้งหมด
    )
    plot_predictions(
        date_series=date_series,
        y_train=y_train,                  # ข้อมูลฝึกอบรม
        y_test=y_test,                    # ข้อมูลทดสอบจริง
        y_pred=y_pred,                    # ผลลัพธ์การทำนาย
        future_prices=future_prices,      # การทำนายอนาคต
        return_period=PREDICTION_PERIOD,
        start_date='2025-01-01',
        full_dates=data['Date'],          # วันที่ทั้งหมด
        full_prices=data['Close']         # ราคาจริงทั้งหมด
    )
    #plot_predictions(date_series, y_train, y_test, y_pred, future_prices, return_period=PREDICTION_PERIOD)
    #plot_predictions(date_series, y_train, y_test, y_pred, future_prices, return_period=PREDICTION_PERIOD, start_date='2025-01-01')
    plot_predictions_dual(date_series, y_train, y_test, y_pred, future_prices, return_period=PREDICTION_PERIOD, cutoff_date_str='2025-07-01')

except Exception as e:
    print(f"Error in Linear Regression Model: {str(e)}")

#เพิ่ม Features เช่น Moving Averages

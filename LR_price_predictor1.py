import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import yfinance as yf

from fetch_stock_data import get_stock_data, fetch_stock_data

try:
    symbol = 'BAM'
    data, error = fetch_stock_data(symbol)
    print("Columns in data:", data.columns.tolist())
    print(data.describe())

    data.columns = data.columns.str.capitalize()
    data['Date'] = pd.to_datetime(data['Date'])
    data = data[['Date', 'Close']]  # ใช้เฉพาะราคาปิด
    data = data.reset_index()

    # 2. สร้างฟีเจอร์ (วันเป็นตัวเลข)
    data['Days'] = (data['Date'] - data['Date'].min()).dt.days

    # 3. แบ่งข้อมูลเป็น train และ test sets
    X = data[['Days']]
    y = data['Close']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 4. สร้างและฝึกโมเดล Linear Regression
    model = LinearRegression()
    model.fit(X_train, y_train)

    # 5. ทำนายราคา
    y_pred = model.predict(X_test)
    slope = model.coef_[0]  # ค่าลบ = เส้นเอียงลง
    intercept = model.intercept_
    print(f"สมการเส้นตรง: Price = {slope:.4f} * Days + {intercept:.4f}")

    # 6. ประเมินโมเดล
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"Mean Squared Error: {mse:.2f}")
    print(f"R-squared: {r2:.4f}")

    # 7. ทำนายราคาในอนาคต (เช่น 30 วันข้างหน้า)
    future_days = np.array([data['Days'].max() + i for i in range(1, 31)]).reshape(-1, 1)
    future_prices = model.predict(future_days)

    # 8. แสดงผลกราฟ
    plt.figure(figsize=(12, 6))
    plt.plot(data['Days'], data['Close'], linewidth=2, label='Actual Price', color='blue', alpha=0.5)
    plt.title(f'{symbol} Stock Price Trend (Raw Data)')
    plt.xlabel('Days')
    plt.ylabel('Price')
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.scatter(X_train, y_train, color='blue', label='Training Data')
    plt.scatter(X_test, y_test, color='green', label='Testing Data')
    plt.plot(X_test, y_pred, color='red', linewidth=2, label=f'Regression Line (Slope: {slope:.2f})')
    plt.scatter(future_days, future_prices, color='purple', label='Future Prediction')
    plt.title(f'{symbol} Stock Price Prediction | R-squared: {r2:.4f}')
    if slope < 0:
        warn_text = f'Slope = {slope:.4f} | Downtrend Predicted'
    else:
        warn_text = f'Slope = {slope:.4f} | Uptrend Predicted'
    plt.text(0.5, 0.9, warn_text, 
         transform=plt.gca().transAxes, color='red', fontsize=12)
    plt.xlabel('Days')
    plt.ylabel('Price')
    plt.legend()
    plt.show()

except Exception as e:
    print(f"Error in Linear Regression Model: {str(e)}")


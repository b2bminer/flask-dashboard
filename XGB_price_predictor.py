import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import yfinance as yf

from fetch_stock_data import get_stock_data, fetch_stock_data

# 1. ดึงข้อมูลหุ้น
symbol = 'TASCO'
data, error = fetch_stock_data(symbol)
data.columns = data.columns.str.capitalize()
data['Date'] = pd.to_datetime(data['Date'])
data = data[['Date', 'Close']]  # ใช้เฉพาะราคาปิด
data = data.reset_index()

# 2. สร้างฟีเจอร์ (แปลงวันที่เป็นตัวเลข)
data['Days'] = (data['Date'] - data['Date'].min()).dt.days

# 3. แบ่งข้อมูลเป็น Train/Test
X = data[['Days']]
y = data['Close']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. สร้างและฝึกโมเดล XGBoost
xgb_model = xgb.XGBRegressor(
    n_estimators=100,  # จำนวนต้นไม้
    max_depth=3,       # ความลึกสูงสุดของแต่ละต้นไม้
    learning_rate=0.1, # อัตราการเรียนรู้
    random_state=42
)
xgb_model.fit(X_train, y_train)

# 5. ทำนายผล
y_pred = xgb_model.predict(X_test)

# 6. ประเมินโมเดล
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"Mean Squared Error: {mse:.2f}")
print(f"R-squared: {r2:.2f}")

# 7. ทำนาย 30 วันข้างหน้า
future_days = np.array([data['Days'].max() + i for i in range(1, 31)]).reshape(-1, 1)
future_prices = xgb_model.predict(future_days)

# 8. แสดงผลกราฟ
plt.figure(figsize=(12, 6))
plt.plot(data['Days'], data['Close'], linewidth=2, label='Actual Price', color='blue', alpha=0.5)
plt.title(f'{symbol} Stock Price Trend (Raw Data)')
plt.xlabel('Days')
plt.ylabel('Price')
plt.legend()
plt.show()

plt.figure(figsize=(12, 6))

# พล็อตข้อมูลจริง
plt.scatter(X_train, y_train, color='blue', alpha=0.5, label='Training Data')
plt.scatter(X_test, y_test, color='green', alpha=0.5, label='Testing Data')

# พล็อตผลการทำนาย
sorted_idx = X_test.squeeze().argsort()
plt.plot(X_test.iloc[sorted_idx], y_pred[sorted_idx], color='red', linewidth=2, label='XGBoost Prediction')

# พล็อตการทำนายอนาคต
plt.scatter(future_days, future_prices, color='purple', s=100, label='Future Prediction (30 days)')

# ตรวจสอบแนวโน้ม
if (future_prices[-1] - future_prices[0]) < 0:
    plt.text(0.5, 0.9, "Warning: Downtrend Predicted", 
             transform=plt.gca().transAxes,
             color='red', 
             fontsize=12,
             ha='center',
             bbox=dict(facecolor='white', alpha=0.8))
elif (future_prices[-1] - future_prices[0]) < 0:
    plt.text(0.5, 0.9, "Warning: Uptrend Predicted", 
             transform=plt.gca().transAxes,
             color='red', 
             fontsize=12,
             ha='center',
             bbox=dict(facecolor='white', alpha=0.8))

plt.title(f'{symbol} Stock Price Prediction (XGBoost)')
plt.xlabel('Days')
plt.ylabel('Price')
plt.legend()
plt.grid(True)
plt.show()

# 9. แสดง Feature Importance
xgb.plot_importance(xgb_model)
plt.show()

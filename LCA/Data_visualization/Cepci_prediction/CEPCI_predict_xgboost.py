import numpy as np
from xgboost import XGBRegressor

# === 原始数据 ===
years = np.arange(2001, 2025)
cepci = list([
    394.3, 395.6, 402.0, 444.2, 468.2, 499.6, 525.4, 575.4, 521.9, 550.8,
    585.7, 584.6, 567.3, 576.1, 556.8, 541.7, 567.5, 603.1, 607.5, 596.2,
    708.8, 816.0, 797.9, 799.3
])
all_years = list(years)
future_years = np.arange(2025, 2031)
xgb_preds = []

for year in future_years:
    X_train, y_train = [], []
    for i in range(3, len(cepci)):
        year_norm = (all_years[i] - 2000) / 30
        diff1 = cepci[i - 1] - cepci[i - 2]
        diff2 = cepci[i - 2] - cepci[i - 3]
        X_train.append([year_norm, diff1, diff2, cepci[i - 1]])
        y_train.append(cepci[i])

    model = XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.1, random_state=42)
    model.fit(np.array(X_train), np.array(y_train))

    year_norm = (year - 2000) / 30
    diff1 = cepci[-1] - cepci[-2]
    diff2 = cepci[-2] - cepci[-3]
    features = np.array([[year_norm, diff1, diff2, cepci[-1]]])
    pred = model.predict(features)[0]
    xgb_preds.append(pred)

    # 更新
    cepci.append(pred)
    all_years.append(year)

# === 打印结果 ===
print("\nExpanding Window XGBoost Predictions (2025–2030):")
for year, pred in zip(future_years, xgb_preds):
    print(f"{year}: {pred:.2f}")

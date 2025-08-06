import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
import warnings
warnings.filterwarnings("ignore")

# Data
years = np.arange(2001, 2025)
cepci = [
    394.3, 395.6, 402.0, 444.2, 468.2, 499.6, 525.4, 575.4, 521.9, 550.8,
    585.7, 584.6, 567.3, 576.1, 556.8, 541.7, 567.5, 603.1, 607.5, 596.2,
    708.8, 816.0, 797.9, 799.3
]

# Create DataFrame
df = pd.DataFrame({'year': years, 'cepci': cepci})
df.set_index('year', inplace=True)

if __name__ == "__main__":
    # Split data for validation
    train_data = df['cepci'][:21]  # 2001-2021
    test_data = df['cepci'][21:]   # 2022-2024

    # Parameter grid
    p_values = range(0, 3)
    d_values = range(0, 2)
    q_values = range(0, 5)
    best_mse = float('inf')
    best_params = None
    best_model = None

    for p in p_values:
        for d in d_values:
            for q in q_values:
                try:
                    model = ARIMA(train_data, order=(p, d, q))
                    model_fit = model.fit()
                    pred = model_fit.forecast(steps=3)
                    mse = mean_squared_error(test_data, pred)
                    print(f'ARIMA{p,d,q} MSE: {mse}')
                    if mse < best_mse:
                        best_mse = mse
                        best_params = (p, d, q)
                        best_model = model_fit
                except:
                    continue

    print(f'Best parameters: {best_params} with MSE: {best_mse}')

    # Forecast with best model
    forecast_years = np.arange(2025, 2031)
    forecast = best_model.forecast(steps=6)
    forecast_df = pd.DataFrame({'year': forecast_years, 'cepci_forecast': forecast})
    forecast_df.set_index('year', inplace=True)
    cepci_forecast_list = forecast.tolist()

    # Plot
    plt.plot(df.index, df['cepci'], label='Historical CEPCI')
    plt.plot(forecast_df.index, forecast_df['cepci_forecast'], label='Forecasted CEPCI', linestyle='--')
    plt.xlabel('Year')
    plt.ylabel('CEPCI')
    plt.title('CEPCI Forecast (2025–2030) with Best ARIMA')
    plt.legend()
    plt.grid(True)
    plt.show()

    # Combine historical and forecast CEPCI into a single dictionary
    cepci_years_combined = list(years) + list(forecast_years)
    cepci_values_combined = cepci + cepci_forecast_list

    cepci_dict = {year: round(value, 2) for year, value in zip(cepci_years_combined, cepci_values_combined)}

    # Print results
    print("CEPCI Forecast for 2025–2030:")
    print(forecast_df)
    print("Forecast list for other files:", cepci_forecast_list)

    # Print combined dict
    print("\nFull CEPCI (2001–2030):")
    for y, v in cepci_dict.items():
        print(f"{y}: {v}")

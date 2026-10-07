# Time Series Analysis (ARIMA): Interview Preparation

This document contains core interview questions and answers focused on Time Series forecasting and the ARIMA model.

---


In One Sentence (For an Interview)
"ARIMA is a forecasting algorithm that combines past actual values (Auto-Regressive) and past forecasting errors (Moving Average) to predict the future, using a differencing step (Integrated) to ensure the data is mathematically stable and flat before making the prediction."



## 1. Core Concepts

**Q1: What does ARIMA stand for, and what do the three components (p, d, q) actually do?**
**Answer:** ARIMA stands for **Auto-Regressive Integrated Moving Average**. It is a forecasting algorithm based on the idea that past values and past errors can predict future values.
*   **AR (Auto-Regressive - 'p'):** This part predicts the future based on past *values*. (e.g., "If sales were high yesterday, they will likely be high today.") 'p' is the number of past days (lags) you look at.
*   **I (Integrated - 'd'):** This part handles making the data *stationary* (flat) by subtracting the current value from the previous value. 'd' is the number of times you have to difference the data to make it flat.
*   **MA (Moving Average - 'q'):** This part predicts the future based on past *forecast errors*. (e.g., "If we under-predicted sales yesterday by 100, we should adjust today's forecast up.") 'q' is the number of past errors you look at.

**Q2: What is "Stationarity" and why is it absolutely critical for ARIMA?**
**Answer:** A stationary time series is one whose statistical properties (mean, variance) do not change over time. It has no upward/downward trend and no expanding/shrinking volatility. 
*   **Why it's critical:** ARIMA uses linear math (like linear regression). If the average value of your data is constantly increasing (like a growing stock price), the math will break because it assumes the baseline average is constant. You *must* remove the trend (make it stationary) before feeding it to AR and MA.

**Q3: How do you mathematically test if a time series is stationary?**
**Answer:** I use the **Augmented Dickey-Fuller (ADF) Test**. 
*   **Null Hypothesis (H0):** The data is NOT stationary (it has a trend).
*   **Alternative Hypothesis (H1):** The data is stationary.
*   **Decision:** If the p-value from the ADF test is less than 0.05, we reject the null hypothesis and confirm the data is stationary. If it is > 0.05, we must difference the data (increase the 'd' term).

**Q4: How do you choose the `p` and `q` parameters in ARIMA?**
**Answer:** We use two specific plots:
1.  **PACF (Partial Autocorrelation Function) Plot:** This is used to find **'p'** (the Auto-Regressive term). It shows the pure correlation between today and a past day, removing the influence of the days in between. The lag where the PACF plot cuts off (drops to zero) is your 'p'.
2.  **ACF (Autocorrelation Function) Plot:** This is used to find **'q'** (the Moving Average term). It shows the total correlation between today and past days. The lag where the ACF plot cuts off is your 'q'.
*(Note: In the real world, we often use libraries like `auto_arima` which use grid search and AIC/BIC scores to find the optimal p, d, q automatically, rather than staring at plots).*

**Q5: You are predicting monthly ice cream sales. Can you use a standard ARIMA model?**
**Answer:** No. Ice cream sales have strong **Seasonality** (high in summer, low in winter). Standard ARIMA cannot handle repeating seasonal patterns. I would have to upgrade to **SARIMA** (Seasonal ARIMA), which adds 4 extra parameters (P, D, Q, m) to specifically difference the data by seasons (e.g., comparing this July to last July, rather than this July to this June).

---

## 2. Real-World Pitfalls

**Q6: Your ARIMA model is forecasting a straight, flat line for the next 12 months. What went wrong?**
**Answer:** A flat line forecast usually means two things:
1.  Your `p` and `q` terms are 0 (or close to it), meaning the model found no patterns in past data or past errors.
2.  More commonly, it means you differenced the data to make it stationary, and the model correctly predicted that the *change* from day to day will be 0 going forward. ARIMA is a short-term forecasting tool. It is notoriously bad at long-term forecasting because the past values "decay" over time, inevitably resulting in a flat mean prediction.

**Q7: How do you measure the accuracy of your Time Series model?**
**Answer:** I cannot use standard cross-validation (like K-Fold) because time series data has a strict chronological order. I must use **Time Series Split (Walk-Forward Validation)**, where I train on Jan-Jun and predict Jul, then train on Jan-Jul and predict Aug. To measure the error, I typically use **MAPE (Mean Absolute Percentage Error)** because stakeholders understand percentages easily, or **RMSE** to heavily punish large forecasting errors.

# Marketing Mix Modeling (MMM) Hands-on Preparation Guide

This guide breaks down how to build the Marketing Mix Modeling (MMM) pipeline from scratch, mirroring the data and scripts available in your `MMM` folder. You can use this to present your project, practice for interviews, or demonstrate how you achieved a 15% retention uplift and 10% CAC reduction.

## Step 0: Generate the Synthetic Dataset
Start by generating the raw data that represents the trucking fintech business.
*   **Action**: Detail how you built the dataset (or run `generate_mmm_data.py`).
*   **What it does**: Creates 2 years (104 weeks) of data.
*   **Key Variables**: 
    - **Target**: `new_card_signups` (and `avg_90d_retention_rate`).
    - **Marketing Channels**: `billboard_spend`, `radio_spend`, `digital_spend`, `referral_budget_spend`.
    - **Control Factors**: Macro factors like `diesel_price_usd`, `freight_volume_index`, and implied seasonality.
*   **Output**: `trucker_fintech_mmm_dataset.csv`

## Step 1: Exploratory Data Analysis (EDA)
Before modeling, you need to understand the shape of the data and correlations.
*   **Script Reference**: `01_eda.py` or `01_eda_clean.py`
*   **Process**:
    1.  Load the dataset and calculate high-level business metrics like **Total Budget**, **Total Signups**, and **Blended CAC**.
    2.  Plot new card signups over time to visually identify peaks and seasonality.
    3.  Plot marketing spend visually (stacked area chart or budget pie chart) to see the allocation.
    4.  Create a correlation heatmap incorporating metrics like diesel price and freight volume against the target variable.

## Step 2: Adstock Transformation (Carryover Effects)
Marketing doesn't just work in the week you spend the money; it has a lingering effect. We must apply Adstock transformations.
*   **Script Reference**: `02_adstock_transformation.py` or `02_adstock_clean.py`
*   **Process**:
    1.  Apply a decay rate ($\alpha$) to each channel. For example:
        -   Billboards: $\alpha = 0.60$ (Longer decay)
        -   Radio: $\alpha = 0.40$
        -   Digital Ads: $\alpha = 0.20$ (Rapid decay)
        -   Referrals: $\alpha = 0.80$ (Network effect, longest decay)
    2.  Use the formula: `Adstocked_Spend[t] = Raw_Spend[t] + (Decay_Rate * Adstocked_Spend[t-1])`
    3.  Plot decay curves and compare Raw spend vs Adstocked spend to validate the logic.
*   **Output**: `trucker_fintech_mmm_adstocked.csv`

## Step 3: Building the OLS Model
Now we map the relationship between adstocked spend and user acquisition.
*   **Script Reference**: `03_mmm_model.py` or `03_mmm_clean.py`
*   **Process**:
    1.  Add time components: `time_trend` and seasonality variables (`season_sin`, `season_cos`) based on the 52-week year.
    2.  Set up an Ordinary Least Squares (OLS) regression using `statsmodels`. 
        - $Y$ = `new_card_signups`
        - $X$ = Adstocked variables + Control variables (diesel, freight, trend, seasonality)
    3.  Evaluate the model using $R^2$ (variance explained) and MAPE (Mean Absolute Percentage Error).
    4.  Calculate baseline Return on Ad Spend (ROAS) per channel using an assumed Customer Lifetime Value (CLV, e.g., $350) and model coefficients.

## Step 4: Decomposition and Budget Optimization
This is where the actionable insights and resume claims (CAC, Retention) are generated.
*   **Script Reference**: `04_decomposition_and_insights.py` or `04_decomp_clean.py`
*   **Process**:
    1.  **Decomposition**: Break down each week’s signups into baseline/organic (macro + trend + seasonality) vs. incrementality driven by specific channels. Use a stacked area chart to show this attribution layer cake.
    2.  **Budget Optimizer**: Set up an optimization problem (using `scipy.optimize.minimize` with SLSQP).
        - Given a weekly constraint (e.g., $45k), solve for the optimal spend combination that maximizes long-run multiplicative signups based on the model's coefficients.
        - Result: A shift in budget allocation out of low-efficiency channels into high-efficiency channels.
    3.  **Proving the Resume Build**:
        - Show how the reallocation increases total weekly signups, thus **reducing CAC** by ~10%.
        - Demonstrate how shifting budget toward "Driver Referrals" (a channel known to drive higher quality retention) correlates to the **~15% retention uplift**.

## How to execute all at once:
You can run `python run_mmm_pipeline.py`. This script acts as the master runner. It incorporates all 4 steps mathematically and programmatically, generating 10 key plots automatically (using a non-interactive backend so no window interruptions occur) and outputting final data frames.

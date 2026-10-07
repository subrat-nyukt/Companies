
    Y-Axis: True Positive Rate (TPR / Sensitivity)
        "Out of all ACTUAL positives, how many did we catch?"
        Formula: TP / (TP + FN)

    X-Axis: False Positive Rate (FPR / 1 - Specificity)
        "Out of all ACTUAL negatives, how many did we falsely flag as positive?"
        Formula: FP / (FP + TN)


3. How the ROC Curve is Created
   Machine learning models (like XGBoost or Logistic Regression) don't output direct "Yes/No" answers; they output probabilities between 0.0 and 1.0 (e.g., 0.85 probability of Fraud).
   Normally, we pick a threshold of 0.5 (if probability $\ge 0.5 \rightarrow$ Fraud).
   The ROC Curve sweeps the threshold from 1.0 down to 0.0:
   At Threshold = 1.0: Predict everything as Negative $\rightarrow$ $\text{TPR} = 0, \text{FPR} = 0$ (Point 0,0).
   At Threshold = 0.5: Calculate $\text{TPR}$ and $\text{FPR}$ $\rightarrow$ Plot point.
   At Threshold = 0.0: Predict everything as Positive $\rightarrow$ $\text{TPR} = 1, \text{FPR} = 1$ (Point 1,1).
   Connecting all these points creates the ROC Curve.
4. Visualizing the ROC Curve & AUC Scores
   TPR (Catching Positives)
   1.0 |         *----------- (Perfect Model: AUC = 1.0)
   |        /|
   |       / |
   0.5 |      /  |           (Random Guessing: AUC = 0.5)
   |     /   |          /
   |    /    |         /
   0.0 +----------------------- FPR (False Alarms)
   0.0       0.5       1.0
   AUC Value	Performance Meaning
   1.0	Perfect Model: Separates Positive and Negative classes completely without any errors.
   0.90 – 0.99	Outstanding: Excellent separation capability.
   0.70 – 0.89	Good / Acceptable: Useful model for practical applications.
   0.50	Random Guessing: No better than flipping a fair coin (diagonal line).
   < 0.50	Worst than Random: The model is predicting the exact opposite of reality.
5. Intuitive Meaning of AUC (The Interviewer Question!)
   If an interviewer asks: "What does an AUC of 0.85 actually mean mathematically?"

Answer: "An AUC of 0.85 means that if you randomly pick one positive instance and one negative instance from the dataset, there is an 85% probability that the model will score the positive instance higher than the negative instance."

6. Why Use ROC-AUC over Accuracy?
   Threshold-Independent: Evaluates the model's ranking ability across all decision thresholds, not just a default 0.5 threshold.
   Robust to Class Imbalance: Unlike Accuracy, ROC-AUC does not get artificially high when a dataset is imbalanced (e.g., 99% Negative, 1% Positive).
   (Note: If class imbalance is extreme, e.g., 99.9% Negative vs 0.1% Positive, Precision-Recall (PR) AUC is preferred over ROC-AUC).

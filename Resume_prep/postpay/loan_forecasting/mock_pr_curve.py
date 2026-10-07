import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, average_precision_score

# Simulate imbalanced data: 100,000 samples, 0.2% positive class (200 defaults)
np.random.seed(42)
n_samples = 100000
n_positive = int(n_samples * 0.002)

y_true = np.zeros(n_samples)
y_true[:n_positive] = 1

# Simulate predicted probabilities (mimicking a realistic model on imbalanced data)
# Majority class gets low probabilities
y_scores = np.random.beta(a=1, b=20, size=n_samples) 
# Minority class gets higher probabilities, but with some confusion
y_scores[:n_positive] = np.random.beta(a=8, b=2, size=n_positive) 

# Calculate PR-AUC
pr_auc = average_precision_score(y_true, y_scores)

# Generate PR Curve points
precision, recall, _ = precision_recall_curve(y_true, y_scores)

# Plotting
plt.figure(figsize=(8, 6))
plt.plot(recall, precision, color='blue', lw=2, label=f'PR Curve (AUC = {pr_auc:.4f})')
plt.xlabel('Recall (True Positive Rate)')
plt.ylabel('Precision (Positive Predictive Value)')
plt.title('Precision-Recall Curve (Simulated 0.2% Imbalance)')
plt.legend(loc='lower left')
plt.grid(True)

# Save the plot
plt.savefig('pr_curve.png', dpi=300, bbox_inches='tight')
print("Successfully generated pr_curve.png")

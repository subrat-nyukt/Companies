"""
============================================================
FEATURE SELECTION PIPELINE   Moove Driver Credit Risk
============================================================

Pipeline Steps:
  STEP 1 | Filter   | Pearson Correlation  -> 100 -> ~80 features
  STEP 2 | Prune    | Lasso L1 Penalty     -> ~80 -> ~30 features
  STEP 3 | Rank     | Gini Impurity (RF)   -> Importance Scores
  STEP 4 | Explain  | Shapley Values       -> Per-prediction breakdown
  STEP 5 | Report   | Bad Debt Reduction   -> Business Impact

Run after: 01_generate_dataset.py
Output files written to same folder.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # headless  no display needed
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from pathlib import Path

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LassoCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score, classification_report, confusion_matrix,
    precision_recall_curve, average_precision_score
)
import shap

# -- Paths --------------------------------------------------
HERE  = Path(__file__).parent
DATA  = HERE / "synthetic_driver_dataset.csv"

print("=" * 65)
print("  MOOVE FEATURE SELECTION PIPELINE")
print("=" * 65)

# ================================================================
# LOAD DATA
# ================================================================
df = pd.read_csv(DATA)
TARGET = "bad_debt"
FEATURES = [c for c in df.columns if c != TARGET]

X = df[FEATURES].copy()
y = df[TARGET].copy()

print(f"\n[DIR]  Dataset loaded: {df.shape[0]:,} rows x {df.shape[1]} cols")
print(f"    Features: {len(FEATURES)}  |  Bad-debt rate: {y.mean():.2%}")

# ================================================================
# STEP 1  FILTER: Pearson Correlation  (100 -> ~80 features)
# ================================================================
print("\n" + "-" * 65)
print("  STEP 1 | FILTER  Pearson Correlation")
print("-" * 65)

# 1a. Remove features whose |r| with target < 0.01  (uninformative)
corr_target = X.corrwith(y).abs().sort_values(ascending=False)
low_corr_features = corr_target[corr_target < 0.01].index.tolist()
X_step1 = X.drop(columns=low_corr_features)
print(f"  Removed {len(low_corr_features)} near-zero target-correlation features")

# 1b. Remove highly inter-correlated features  (|r| > 0.90)
corr_matrix = X_step1.corr().abs()
upper_tri   = corr_matrix.where(
    np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
)
to_drop_corr = [
    col for col in upper_tri.columns
    if any(upper_tri[col] > 0.90)
]
X_step1 = X_step1.drop(columns=to_drop_corr)

print(f"  Removed {len(to_drop_corr)} highly inter-correlated features (|r|>0.90)")
print(f"  -> Features remaining after Step 1: {X_step1.shape[1]}")

step1_features = X_step1.columns.tolist()

# -- Plot: Correlation heatmap (top 20 features to target) -
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("STEP 1  Pearson Correlation Analysis", fontsize=14, fontweight="bold")

corr_values = X_step1.corrwith(y).sort_values(key=abs, ascending=False).head(20)
colors = ["#e74c3c" if v > 0 else "#3498db" for v in corr_values.values]
axes[0].barh(corr_values.index[::-1], corr_values.values[::-1], color=colors[::-1])
axes[0].axvline(0, color="black", lw=0.8)
axes[0].set_title("Top 20 Features  Pearson r with bad_debt", fontweight="bold")
axes[0].set_xlabel("Pearson r")

# Inter-correlation heatmap (top 20)
top20 = X_step1.corrwith(y).abs().nlargest(20).index
sns.heatmap(
    X_step1[top20].corr(), ax=axes[1], cmap="RdBu_r",
    center=0, linewidths=0.3, annot=False, square=True, cbar_kws={"shrink": 0.8}
)
axes[1].set_title("Inter-Correlation Matrix (Top 20)", fontweight="bold")
axes[1].tick_params(axis="x", rotation=45, labelsize=8)
axes[1].tick_params(axis="y", rotation=0, labelsize=8)
plt.tight_layout()
plt.savefig(HERE / "step1_pearson_correlation.png", dpi=150, bbox_inches="tight")
plt.close()
print("  [CHART]  step1_pearson_correlation.png saved")

# ================================================================
# STEP 2  PRUNE: Lasso L1 Penalty  (~80 -> ~30 features)
# ================================================================
print("\n" + "-" * 65)
print("  STEP 2 | PRUNE  Lasso L1 Penalty")
print("-" * 65)

scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X_step1)

# LassoCV finds the best alpha automatically
lasso = LassoCV(
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    max_iter=5000,
    n_alphas=50,
    random_state=42,
    n_jobs=-1,
)
lasso.fit(X_scaled, y)

lasso_coefs = pd.Series(lasso.coef_, index=step1_features).abs().sort_values(ascending=False)
selected_lasso = lasso_coefs[lasso_coefs > 0].index.tolist()
zeroed_lasso   = lasso_coefs[lasso_coefs == 0].index.tolist()

X_step2 = X_step1[selected_lasso]

print(f"  Best alpha  : {lasso.alpha_:.6f}")
print(f"  Zeroed out  : {len(zeroed_lasso)} features")
print(f"  -> Features remaining after Step 2: {X_step2.shape[1]}")

# -- Plot: Lasso coefficient magnitudes -------------------
fig, ax = plt.subplots(figsize=(11, max(5, len(selected_lasso) * 0.35)))
colors2 = sns.color_palette("magma", len(selected_lasso))[::-1]
ax.barh(
    y=range(len(selected_lasso)),
    width=lasso_coefs[selected_lasso].values[::-1],
    color=colors2
)
ax.set_yticks(range(len(selected_lasso)))
ax.set_yticklabels(selected_lasso[::-1], fontsize=9)
ax.set_xlabel("|Lasso Coefficient|", fontsize=11)
ax.set_title(f"STEP 2  Lasso L1: {len(selected_lasso)} Surviving Features  (best ={lasso.alpha_:.5f})",
             fontsize=12, fontweight="bold")
ax.axvline(0, color="black", lw=0.5)
plt.tight_layout()
plt.savefig(HERE / "step2_lasso_coefs.png", dpi=150, bbox_inches="tight")
plt.close()
print("  [CHART]  step2_lasso_coefs.png saved")

# ================================================================
# STEP 3  RANK: Gini Impurity  -> Feature Importance Weights
# ================================================================
print("\n" + "-" * 65)
print("  STEP 3 | RANK  Gini Impurity (Random Forest)")
print("-" * 65)

X_train, X_test, y_train, y_test = train_test_split(
    X_step2, y, test_size=0.20, random_state=42, stratify=y
)

rf = RandomForestClassifier(
    n_estimators=500,
    max_depth=12,
    min_samples_leaf=20,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
)
rf.fit(X_train, y_train)

importance_df = pd.DataFrame({
    "feature":    X_step2.columns,
    "importance": rf.feature_importances_,
}).sort_values("importance", ascending=False).reset_index(drop=True)

importance_df["rank"]            = importance_df.index + 1
importance_df["importance_pct"]  = importance_df["importance"] / importance_df["importance"].sum() * 100
importance_df["cumulative_pct"]  = importance_df["importance_pct"].cumsum()

print("\n  Top 15 Features by Gini Importance:")
print(importance_df.head(15).to_string(index=False))

# Model performance
y_prob = rf.predict_proba(X_test)[:, 1]
auc    = roc_auc_score(y_test, y_prob)
print(f"\n  Random Forest AUC-ROC: {auc:.4f}")

# -- Plot: Feature importance bar chart -------------------
fig, axes = plt.subplots(1, 2, figsize=(17, 7))
fig.suptitle("STEP 3  Gini Impurity Feature Importance", fontsize=14, fontweight="bold")

top_n = importance_df.head(20)
palette = sns.color_palette("viridis", len(top_n))[::-1]
axes[0].barh(top_n["feature"][::-1], top_n["importance"][::-1], color=palette)
axes[0].set_xlabel("Gini Importance", fontsize=11)
axes[0].set_title(f"Top 20 Features  (RF AUC = {auc:.3f})", fontweight="bold")

# Cumulative importance curve
axes[1].plot(range(1, len(importance_df) + 1), importance_df["cumulative_pct"],
             color="#e74c3c", lw=2.5, marker="o", markersize=4)
axes[1].axhline(80, color="#3498db", ls="--", lw=1.5, label="80% threshold")
axes[1].axhline(95, color="#27ae60", ls="--", lw=1.5, label="95% threshold")
axes[1].fill_between(range(1, len(importance_df) + 1), importance_df["cumulative_pct"],
                     alpha=0.1, color="#e74c3c")
axes[1].set_xlabel("Number of Features", fontsize=11)
axes[1].set_ylabel("Cumulative Importance %", fontsize=11)
axes[1].set_title("Cumulative Feature Importance", fontweight="bold")
axes[1].legend()
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(HERE / "step3_gini_importance.png", dpi=150, bbox_inches="tight")
plt.close()
print("  [CHART]  step3_gini_importance.png saved")

# ================================================================
# STEP 4  EXPLAIN: Shapley Values  (1 prediction breakdown)
# ================================================================
print("\n" + "-" * 65)
print("  STEP 4 | EXPLAIN  Shapley Values")
print("-" * 65)

# Use a smaller GBM for SHAP speed
gbm = GradientBoostingClassifier(
    n_estimators=200, max_depth=4, learning_rate=0.05,
    subsample=0.8, random_state=42
)
gbm.fit(X_train, y_train)
gbm_auc = roc_auc_score(y_test, gbm.predict_proba(X_test)[:, 1])
print(f"  GBM AUC-ROC (for SHAP): {gbm_auc:.4f}")

explainer   = shap.TreeExplainer(gbm)
X_sample    = X_test.sample(200, random_state=42)         # 200 sample for speed
shap_values = explainer.shap_values(X_sample)

# -- 4a. Summary plot  (global SHAP) ----------------------
fig, ax = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_values, X_sample, show=False, max_display=20,
                  plot_type="bar", color="#e74c3c")
plt.title("STEP 4  SHAP Global Feature Impact (mean |SHAP|)",
          fontsize=13, fontweight="bold", pad=12)
plt.tight_layout()
plt.savefig(HERE / "step4_shap_global.png", dpi=150, bbox_inches="tight")
plt.close()
print("  [CHART]  step4_shap_global.png saved")

# -- 4b. Single prediction waterfall ----------------------
# Pick the highest-risk driver in the test set
high_risk_idx_in_sample = np.argmax(gbm.predict_proba(X_sample)[:, 1])
single_shap = shap_values[high_risk_idx_in_sample]


# Manual waterfall plot (works with any shap version)
sorted_idx = np.argsort(np.abs(single_shap))[-15:]
feat_names  = X_sample.columns[sorted_idx]
sv_vals     = single_shap[sorted_idx]

fig, ax = plt.subplots(figsize=(10, 7))
colors_wf = ["#e74c3c" if v > 0 else "#3498db" for v in sv_vals]
bars = ax.barh(range(len(sv_vals)), sv_vals, color=colors_wf, edgecolor="white")
ax.set_yticks(range(len(sv_vals)))
ax.set_yticklabels(feat_names, fontsize=10)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("SHAP Value  (impact on bad-debt prediction)", fontsize=11)
ax.set_title(
    f"STEP 4  SHAP Waterfall: Single High-Risk Driver Prediction\n"
    f"Predicted bad-debt probability: {gbm.predict_proba(X_sample.iloc[[high_risk_idx_in_sample]])[:, 1][0]:.2%}",
    fontweight="bold", fontsize=12
)
for bar, val in zip(bars, sv_vals):
    ax.text(val + (0.001 if val >= 0 else -0.001),
            bar.get_y() + bar.get_height() / 2,
            f"{val:+.3f}",
            va="center",
            ha="left" if val >= 0 else "right",
            fontsize=8.5)
plt.tight_layout()
plt.savefig(HERE / "step4_shap_single_prediction.png", dpi=150, bbox_inches="tight")
plt.close()
print("  [CHART]  step4_shap_single_prediction.png saved")

# -- 4c. SHAP beeswarm (dot) summary plot -----------------
fig, ax = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_values, X_sample, show=False, max_display=15)
plt.title("STEP 4  SHAP Beeswarm (Feature x Value x Impact)",
          fontsize=13, fontweight="bold", pad=12)
plt.tight_layout()
plt.savefig(HERE / "step4_shap_beeswarm.png", dpi=150, bbox_inches="tight")
plt.close()
print("  [CHART]  step4_shap_beeswarm.png saved")

# ================================================================
# STEP 5  REPORT: Bad Debt Reduction Simulation
# ================================================================
print("\n" + "-" * 65)
print("  STEP 5 | REPORT  Bad Debt Reduction Impact")
print("-" * 65)

# Threshold optimization: maximise precision (reduce false approvals)
precisions, recalls, thresholds = precision_recall_curve(y_test, y_prob)
f1_scores = 2 * precisions * recalls / (precisions + recalls + 1e-9)
best_thresh = thresholds[np.argmax(f1_scores)]

y_pred_base  = (y_prob >= 0.5).astype(int)
y_pred_tuned = (y_prob >= best_thresh).astype(int)

cm_base  = confusion_matrix(y_test, y_pred_base)
cm_tuned = confusion_matrix(y_test, y_pred_tuned)

# Bad debt = FP: we said "GOOD" but was "BAD"
fp_base  = cm_base[1, 0]   # actual=bad, predicted=good
fp_tuned = cm_tuned[1, 0]

reduction_pct = (fp_base - fp_tuned) / max(fp_base, 1) * 100
avg_loan      = df["loan_principal"].mean()
saved_loans   = fp_base - fp_tuned
saved_value   = saved_loans * avg_loan

print(f"  Baseline threshold=0.50  -> Bad loans approved (FN): {fp_base}")
print(f"  Tuned    threshold={best_thresh:.2f}  -> Bad loans approved (FN): {fp_tuned}")
print(f"  Bad Debt Reduction : {reduction_pct:.1f}%")
print(f"  Loans saved        : {saved_loans}")
print(f"  Estimated $ saved  : ${saved_value:,.0f}  (@ avg loan ${avg_loan:,.0f})")

# -- Plot: Confusion matrix comparison + summary dashboard -
fig = plt.figure(figsize=(18, 10))
gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.40, wspace=0.35)

fig.suptitle("STEP 5  Pipeline Impact Report: Bad Debt Reduction",
             fontsize=15, fontweight="bold")

# Confusion matrix baseline
ax1 = fig.add_subplot(gs[0, 0])
sns.heatmap(cm_base, annot=True, fmt="d", cmap="Blues", ax=ax1,
            xticklabels=["Pred Good", "Pred Bad"],
            yticklabels=["Act Good", "Act Bad"])
ax1.set_title("Confusion Matrix\nBaseline (thresh=0.50)", fontweight="bold")

# Confusion matrix tuned
ax2 = fig.add_subplot(gs[0, 1])
sns.heatmap(cm_tuned, annot=True, fmt="d", cmap="Greens", ax=ax2,
            xticklabels=["Pred Good", "Pred Bad"],
            yticklabels=["Act Good", "Act Bad"])
ax2.set_title(f"Confusion Matrix\nTuned (thresh={best_thresh:.2f})", fontweight="bold")

# KPI summary panel
ax3 = fig.add_subplot(gs[0, 2])
ax3.axis("off")
kpi_text = (
    f"{'='*30}\n"
    f"  PIPELINE SUMMARY\n"
    f"{'='*30}\n"
    f"  Start Features      : {len(FEATURES)}\n"
    f"  After Pearson (S1)  : {len(step1_features)}\n"
    f"  After Lasso   (S2)  : {len(selected_lasso)}\n"
    f"  RF AUC-ROC    (S3)  : {auc:.4f}\n"
    f"  GBM AUC-ROC   (S4)  : {gbm_auc:.4f}\n"
    f"{'-'*30}\n"
    f"  Bad Debt Reduction  : {reduction_pct:.1f}%\n"
    f"  Loans Saved         : {saved_loans}\n"
    f"  Est. Value Saved    : ${saved_value:,.0f}\n"
    f"{'='*30}"
)
ax3.text(0.05, 0.95, kpi_text, transform=ax3.transAxes,
         fontsize=10.5, va="top", fontfamily="monospace",
         bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a2e", edgecolor="#e74c3c",
                   linewidth=2))
ax3.set_facecolor("#f8f9fa")

# PR curve
ax4 = fig.add_subplot(gs[1, 0])
ax4.plot(recalls, precisions, color="#e74c3c", lw=2)
ax4.scatter([recalls[np.argmax(f1_scores)]], [precisions[np.argmax(f1_scores)]],
            color="#27ae60", s=100, zorder=5, label=f"Best F1 @ {best_thresh:.2f}")
ax4.set_xlabel("Recall"), ax4.set_ylabel("Precision")
ax4.set_title("Precision-Recall Curve", fontweight="bold")
ax4.legend(); ax4.grid(alpha=0.3)
ap = average_precision_score(y_test, y_prob)
ax4.set_title(f"Precision-Recall  (AP={ap:.3f})", fontweight="bold")

# Feature count waterfall
ax5 = fig.add_subplot(gs[1, 1])
stages = ["Start\n(111)", "After Pearson\nCorrelation", "After Lasso\nL1", "Final\nRanked"]
counts = [len(FEATURES), len(step1_features), len(selected_lasso), len(selected_lasso)]
clrs   = ["#95a5a6", "#3498db", "#e74c3c", "#27ae60"]
bars   = ax5.bar(stages, counts, color=clrs, edgecolor="white", width=0.55)
for b, c in zip(bars, counts):
    ax5.text(b.get_x() + b.get_width()/2, b.get_height() + 1, str(c),
             ha="center", fontweight="bold", fontsize=12)
ax5.set_ylabel("# Features")
ax5.set_title("Feature Count by Pipeline Stage", fontweight="bold")
ax5.set_ylim(0, max(counts) * 1.18)

# SHAP global importance bar
ax6 = fig.add_subplot(gs[1, 2])
mean_shap = pd.Series(
    np.abs(shap_values).mean(axis=0), index=X_sample.columns
).sort_values(ascending=False).head(10)
ax6.barh(mean_shap.index[::-1], mean_shap.values[::-1], color="#9b59b6")
ax6.set_xlabel("Mean |SHAP| Value")
ax6.set_title("Top 10 Features by SHAP Impact", fontweight="bold")

plt.savefig(HERE / "step5_pipeline_report.png", dpi=150, bbox_inches="tight")
plt.close()
print("  [CHART]  step5_pipeline_report.png saved")

# ================================================================
# SAVE: Feature registry CSV
# ================================================================
# Merge with SHAP importance
shap_importance = pd.Series(
    np.abs(shap_values).mean(axis=0), index=X_sample.columns, name="mean_abs_shap"
)
registry = importance_df.set_index("feature").join(
    lasso_coefs.rename("lasso_coef"),
    how="left"
).join(shap_importance, how="left")
registry["lasso_coef"] = registry["lasso_coef"].fillna(0)
registry["mean_abs_shap"] = registry["mean_abs_shap"].fillna(0)
registry = registry.reset_index().rename(columns={"index": "feature"})
registry.to_csv(HERE / "feature_registry.csv", index=False)
print("\n  [FILE]  feature_registry.csv saved (all scores per feature)")

# ================================================================
# PRINT: Final Feature Registry
# ================================================================
print("\n" + "=" * 65)
print("  FINAL FEATURE REGISTRY")
print("=" * 65)
print(registry[["feature", "rank", "importance", "importance_pct",
                "lasso_coef", "mean_abs_shap"]].to_string(index=False))

print("\n" + "=" * 65)
print("  [OK]  PIPELINE COMPLETE")
print("=" * 65)
print(f"""
  OUTPUT FILES:
  +-- synthetic_driver_dataset.csv
  +-- feature_registry.csv
  +-- step1_pearson_correlation.png
  +-- step2_lasso_coefs.png
  +-- step3_gini_importance.png
  +-- step4_shap_global.png
  +-- step4_shap_beeswarm.png
  +-- step4_shap_single_prediction.png
  +-- step5_pipeline_report.png

  PIPELINE SUMMARY:
  ------------------------------+----------
  | Stage                        | Features |
  +------------------------------+----------+
  | Start                        | {len(FEATURES):<8} |
  | After Pearson Correlation    | {len(step1_features):<8} |
  | After Lasso L1               | {len(selected_lasso):<8} |
  | RF AUC-ROC                   | {auc:<8.4f} |
  | Bad Debt Reduction           | {reduction_pct:<7.1f}% |
  +------------------------------+----------
""")

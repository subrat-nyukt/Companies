# Hypothesis Testing: Interview Preparation
## ANOVA & Monte Carlo Simulation

---

## PART 1: Foundations of Hypothesis Testing

**Q1: What is a Null Hypothesis and an Alternative Hypothesis? Give a business example.**
**Answer:**
*   **Null Hypothesis (H0):** The "boring" assumption. It states that nothing happened, there is no effect, or no difference exists. It is the default position you are trying to disprove.
*   **Alternative Hypothesis (H1):** The "interesting" claim. It states that there IS an effect or difference.

**Business Example (Marketing Campaign):**
*   H0: "Our new email campaign has NO effect on customer purchase rates. The average purchase rate is the same as before."
*   H1: "Our new email campaign INCREASED the average purchase rate."

You then collect data. If the p-value < 0.05, you reject H0 and conclude that the campaign genuinely worked.

---

**Q2: What is a p-value? What is the single biggest misconception about it?**
**Answer:** A p-value is the probability of observing your data results (or more extreme results) assuming the Null Hypothesis is TRUE.

**The Biggest Misconception:** Most people say "p-value is the probability that H0 is true." This is WRONG.
*   **Wrong:** "There is only a 3% chance the null hypothesis is true."
*   **Correct:** "If the null hypothesis were true, there is only a 3% chance I would have seen data this extreme by pure random luck."

In other words, the p-value measures how "surprised" you should be by your data IF nothing was actually happening.

---

**Q3: What is a Type I Error and a Type II Error?**
**Answer:**

| Error Type | Also Called | What it means | Business Consequence |
|---|---|---|---|
| **Type I Error** | False Positive | You reject H0 when it was actually TRUE | You deploy a new feature that doesn't actually work, wasting engineering resources |
| **Type II Error** | False Negative | You fail to reject H0 when it was actually FALSE | You abandon a genuinely effective marketing campaign, losing revenue |

*   **Alpha (α):** The threshold for Type I Error. If α = 0.05, you accept a 5% risk of a false positive.
*   **Beta (β):** The threshold for Type II Error. Power = 1 - β. Higher statistical power means fewer false negatives.

---

## PART 2: ANOVA (Analysis of Variance)

**Q4: What is ANOVA and when do you use it instead of a t-test?**
**Answer:** ANOVA (Analysis of Variance) tests whether the means of **three or more groups** are statistically significantly different from each other.

*   **Use a t-test** when comparing exactly 2 groups (e.g., "Is sales revenue in Region A different from Region B?").
*   **Use ANOVA** when comparing 3 or more groups (e.g., "Is sales revenue different across Regions A, B, C, and D?").

**Why not just run multiple t-tests?** If you run 6 t-tests to compare 4 groups pairwise, each at a 5% alpha level, your cumulative false-positive rate explodes well above 5%. ANOVA controls this by testing all groups simultaneously in a single test.

---

**Q5: What is the F-statistic in ANOVA? Explain it in plain English.**
**Answer:** The F-statistic is the core output of ANOVA. It is a ratio that answers:

> **F = (Variance BETWEEN the groups) / (Variance WITHIN the groups)**

*   **Numerator (Between-group variance):** How far apart are the group means from each other? If the groups are very different (e.g., Region A averages $10K sales, Region D averages $80K), this is large.
*   **Denominator (Within-group variance):** How noisy/spread is the data inside each group? If each region has wildly varying daily sales, this is large.

**Plain English:** A large F-statistic means "the groups are far apart from each other, but the data within each group is tight and consistent." This is strong evidence that the group means are genuinely different, not due to random noise.

If F is close to 1.0, it means the variation between groups is no larger than the variation you would expect from random chance.

---

**Q6: ANOVA tells you SOMETHING is different, but not WHICH groups. How do you find out?**
**Answer:** This is a critical follow-up question. After ANOVA rejects H0, you run a **Post-Hoc Test** to identify exactly which pairs of groups are different.

The most common Post-Hoc tests are:
*   **Tukey's HSD (Honest Significant Difference):** The most widely used. It compares all pairs simultaneously while controlling the false-positive rate. Best when you want to compare all groups to each other.
*   **Bonferroni Correction:** A simpler but more conservative approach. It divides your alpha level by the number of comparisons being made.
*   **Dunnett's Test:** Used specifically when you only want to compare all groups against a single control group.

---

**Q7: What are the 3 key assumptions of One-Way ANOVA? What if they are violated?**
**Answer:**
1.  **Independence:** Each observation must be independent (one customer's purchase doesn't influence another's).
2.  **Normality:** The data within each group should be roughly normally distributed. If violated with large samples, the **Central Limit Theorem** protects you. If the data is heavily skewed with small samples, switch to the non-parametric **Kruskal-Wallis test**.
3.  **Homogeneity of Variances (Homoscedasticity):** All groups should have roughly the same spread/variance. Test this using **Levene's Test**. If violated, use **Welch's ANOVA** instead of standard ANOVA.

---

## PART 3: Monte Carlo Simulation

**Q8: What is a Monte Carlo Simulation and what business problem does it solve?**
**Answer:** Monte Carlo Simulation is a technique for modeling uncertainty and risk. Instead of calculating a single deterministic answer, it runs thousands of simulations where each uncertain input is randomly sampled from a probability distribution. You then look at the distribution of all the outputs.

**Business Problem it Solves:** "We know our unit cost is roughly $10, but it varies. Our demand is roughly 5,000 units but it varies. What is our expected profit, and what is the probability of losing money?"

A standard calculation gives you one number. Monte Carlo gives you a full distribution of possible outcomes and, most importantly, a **probability of failure/loss.**

---

**Q9: Can you explain the key steps of a Monte Carlo Simulation?**
**Answer:** Yes. There are 4 steps:
1.  **Define the uncertain inputs:** Identify every variable that has uncertainty and assign it a probability distribution (e.g., "Demand follows a Normal distribution with mean=5,000 and std=500").
2.  **Random Sampling:** In each simulation run (called a "trial"), randomly draw one value for each uncertain input from its distribution.
3.  **Calculate the output:** Plug those randomly drawn values into your model and calculate the result (e.g., Profit = Revenue - Cost).
4.  **Repeat thousands of times:** Run steps 2 and 3 for 10,000 or 100,000 trials. Aggregate all the resulting outputs into a distribution.

The resulting distribution shows you: what is the most likely outcome, what is the worst-case scenario, and what is the probability of any specific outcome.

---

**Q10: How is Monte Carlo different from a simple sensitivity analysis?**
**Answer:**
*   **Sensitivity Analysis** changes one variable at a time (e.g., "What if cost is $8? What if cost is $12?"). It tells you which variable matters the most, but it cannot model situations where multiple variables are simultaneously bad (e.g., costs are high AND demand is low AND a competitor undercuts your price all at the same time).
*   **Monte Carlo Simulation** moves all uncertain variables simultaneously and randomly in every single trial. It captures the realistic worst-case scenario where everything goes wrong at once, which is critical for risk management and stress-testing financial models.

---



## PART 4: Sensitivity Analysis

**Q11: What is Sensitivity Analysis and what is its primary goal?**
**Answer:** Sensitivity Analysis (often called "What-If" analysis) is the process of changing the inputs of a model to see how drastically the output changes.
Its primary goal is to **identify the biggest drivers of risk and success**. If I change the "Marketing Budget" by 10% and profit changes by 2%, but I change "Product Price" by 10% and profit changes by 40%, then Product Price is my most "sensitive" variable. Management must focus all their attention on getting the price right.

**Q12: How do you visualize Sensitivity Analysis for business stakeholders?**
**Answer:** The two industry-standard visualizations are:
1.  **The Tornado Chart (One-Way):** A bar chart where the most sensitive variable is at the top with the widest bar, and the least sensitive is at the bottom, creating a funnel or "tornado" shape. It clearly ranks which variables matter most.
2.  **The Heatmap / Data Table (Two-Way):** A colored grid that varies exactly two inputs at the same time (e.g., Rows = Price, Columns = Units Sold) and shows the resulting profit in the intersecting cells. Green cells mean profit, red cells mean loss. It tells stakeholders the exact "safe zone" for those two variables.

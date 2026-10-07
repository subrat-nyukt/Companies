# Python (Pandas) vs. PySpark Code Patterns

There are significant differences in syntax because Spark is **Distributed**.

## 1. Loading Data
*   **Python (Pandas)**:
    ```python
    df = pd.read_csv("data.csv")
    ```
*   **PySpark**:
    ```python
    df = spark.read.csv("dbfs:/data.csv", header=True, inferSchema=True)
    ```

## 2. Filtering
*   **Python**:
    ```python
    # Filter for High Risk
    bad_users = df[df['risk_score'] > 0.8]
    ```
*   **PySpark**:
    ```python
    # Filter for High Risk (Running on 50 machines!)
    bad_users = df.filter(df.risk_score > 0.8)
    ```

## 3. Creating New Columns (The biggest difference)
*   **Python**:
    ```python
    # Vectorized operation in memory
    df['total_debt'] = df['loans'] + df['interest']
    ```
*   **PySpark**:
    ```python
    # You MUST use the 'col' function
    from pyspark.sql.functions import col
    
    df = df.withColumn("total_debt", col("loans") + col("interest"))
    ```

## 4. Aggregation (Group By)
*   **Python**:
    ```python
    df.groupby('city')['sales'].sum()
    ```
*   **PySpark**:
    ```python
    df.groupBy("city").agg({"sales": "sum"})
    ```

## Summary
*   **Pandas**: Reads like math (`df['x'] + df['y']`).
*   **Spark**: Reads like SQL (`df.select(...)`, `df.filter(...)`).
    *   Spark code is "Lazy". It doesn't actually run until you call `.show()` or `.save()`. This allows it to optimize the query plan first.

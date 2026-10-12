# src/revenue_calculator/calculator.py

def calculate_kpis(spark_session):
    """
    Simulates a business calculation.
    Creates a sample DataFrame and computes revenue metrics.
    """
    data = [
        ("Product_A", 100, 25.0),
        ("Product_B", 200, 15.0),
        ("Product_C", 50, 120.0),
    ]
    columns = ["product_name", "quantity", "unit_price"]
    
    df = spark_session.createDataFrame(data, columns)
    
    # Calculate Total Revenue
    df_with_revenue = df.withColumn("total_revenue", df["quantity"] * df["unit_price"])
    return df_with_revenue

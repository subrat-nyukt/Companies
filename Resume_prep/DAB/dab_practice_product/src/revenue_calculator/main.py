# src/revenue_calculator/main.py
import sys
from pyspark.sql import SparkSession
from revenue_calculator.calculator import calculate_kpis

def run():
    print("==========================================")
    print("🚀 Starting Revenue Calculator Product...")
    print("==========================================")

    spark = SparkSession.builder.getOrCreate()
    
    result_df = calculate_kpis(spark)
    result_df.show()

    total = result_df.groupBy().sum("total_revenue").collect()[0][0]
    print(f"✅ Calculation Complete! Total Revenue: ${total:,.2f}")
    print("==========================================")

if __name__ == "__main__":
    run()

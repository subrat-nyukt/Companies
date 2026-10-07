-- ==========================================
-- SQL WINDOW FUNCTIONS: HANDS-ON PRACTICE
-- Topics: RANK, DENSE_RANK, LEAD, LAG, ROLLING SUM, ROLLING AVG
-- ==========================================

-- ------------------------------------------
-- 1. SETUP: Create table and insert data
-- ------------------------------------------
-- Run this block first to set up your practice environment!
CREATE TABLE IF NOT EXISTS daily_sales (
    date DATE,
    sales_rep VARCHAR(50),
    region VARCHAR(50),
    revenue INT
);

-- Delete existing data if re-running
DELETE FROM daily_sales;

INSERT INTO daily_sales (date, sales_rep, region, revenue) VALUES
('2023-10-01', 'Alice', 'North', 500),
('2023-10-01', 'Bob', 'North', 500),
('2023-10-01', 'Charlie', 'South', 300),
('2023-10-02', 'Alice', 'North', 700),
('2023-10-02', 'Bob', 'North', 800),
('2023-10-02', 'Charlie', 'South', 400),
('2023-10-03', 'Alice', 'North', 600),
('2023-10-03', 'Bob', 'North', 800),
('2023-10-03', 'Charlie', 'South', 600),
('2023-10-04', 'Alice', 'North', 900),
('2023-10-04', 'Bob', 'North', 200),
('2023-10-04', 'Charlie', 'South', 900);


-- ------------------------------------------
-- PRACTICE QUESTIONS
-- ------------------------------------------

-- Q1: RANK vs DENSE_RANK
-- Write a query to rank all sales reps based on their TOTAL revenue across all days.
-- Use both RANK() and DENSE_RANK() to see the difference if there's a tie.
-- Expected columns: sales_rep, total_revenue, regular_rank, dense_rank

-- Write your query below:



/* -- SOLUTION --
WITH TotalSales AS (
    SELECT sales_rep, SUM(revenue) as total_revenue
    FROM daily_sales
    GROUP BY sales_rep
)
SELECT 
    sales_rep, 
    total_revenue,
    RANK() OVER(ORDER BY total_revenue DESC) as regular_rank,
    DENSE_RANK() OVER(ORDER BY total_revenue DESC) as dense_rank
FROM TotalSales;
*/


-- ------------------------------------------

-- Q2: LEAD & LAG (Comparing day-over-day)
-- Write a query to show Alice's revenue for each day, 
-- her revenue from the PREVIOUS day (LAG), 
-- and her revenue for the NEXT day (LEAD).
-- Filter only for sales_rep = 'Alice'.

-- Write your query below:



/* -- SOLUTION --
SELECT 
    date,
    revenue as today_revenue,
    LAG(revenue) OVER(ORDER BY date) as previous_day_revenue,
    LEAD(revenue) OVER(ORDER BY date) as next_day_revenue
FROM daily_sales
WHERE sales_rep = 'Alice';
*/


-- ------------------------------------------

-- Q3: ROLLING SUM (Cumulative Total)
-- Write a query to calculate the cumulative (running total) revenue for EACH sales_rep 
-- over time. The sum should reset for each sales_rep.
-- Expected columns: date, sales_rep, revenue, running_total

-- Write your query below:



/* -- SOLUTION --
SELECT 
    date,
    sales_rep,
    revenue,
    SUM(revenue) OVER(PARTITION BY sales_rep ORDER BY date) as running_total
FROM daily_sales
ORDER BY sales_rep, date;
*/


-- ------------------------------------------

-- Q4: ROLLING AVERAGE (Moving Average)
-- Write a query to calculate the 2-day rolling average revenue for 'Bob'.
-- The average should include the CURRENT day and the 1 PRECEDING day.
-- Expected columns: date, sales_rep, revenue, rolling_2day_avg

-- Write your query below:



/* -- SOLUTION --
SELECT 
    date,
    sales_rep,
    revenue,
    AVG(revenue) OVER(
        ORDER BY date 
        ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
    ) as rolling_2day_avg
FROM daily_sales
WHERE sales_rep = 'Bob';
*/


-- ------------------------------------------

-- Q5: ADVANCED COMBINATION (Rank within Partitions)
-- Write a query to find the TOP selling sales_rep for EACH day.
-- If there is a tie for 1st place on a day, both reps should be returned.
-- Hint: Use DENSE_RANK() partitioned by date.

-- Write your query below:



/* -- SOLUTION --
WITH RankedDaily AS (
    SELECT 
        date,
        sales_rep,
        revenue,
        DENSE_RANK() OVER(PARTITION BY date ORDER BY revenue DESC) as daily_rank
    FROM daily_sales
)
SELECT date, sales_rep, revenue
FROM RankedDaily
WHERE daily_rank = 1;
*/

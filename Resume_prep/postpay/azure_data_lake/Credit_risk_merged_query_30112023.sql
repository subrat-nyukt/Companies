CREATE TABLE anirban.credit_risk_returning_customer
AS
SELECT * 
FROM
(
with num_ins as 
(

select 
customer_id,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_instalment_plan_1m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_instalment_plan_3m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_instalment_plan_6m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_instalment_plan_9m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_instalment_plan_12m,
sum(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_instalment_plan_tot


from dl.instalment_plans
where currency='AED' and num_instalments=3
group by 
customer_id),

-- creating SQL for  average of instalment(Principal) per customer section
avg_ins as
(
select
customer_id,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else null end),0) as Avg_ins_amt_1m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else null end),0) as Avg_ins_amt_3m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else null end),0) as Avg_ins_amt_6m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else null end),0) as Avg_ins_amt_9m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else null end),0) as Avg_ins_amt_12m,
coalesce(avg(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else null end),0) as Avg_ins_amt_tot

from dl.instalment_plans 
group by 
customer_id),
-- Creating SQL for sum of instalment(principal) per customer section
sum_prin as (
select
customer_id,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else 0 end) as Tot_ins_amt_1m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else 0 end) as Tot_ins_amt_3m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else 0 end) as Tot_ins_amt_6m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else 0 end) as Tot_ins_amt_9m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else 0 end) as Tot_ins_amt_12m,
sum(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount-total_downpayment else 0 end) as Tot_ins_amt_tot

from dl.instalment_plans
where currency='AED' and num_instalments=3
group by 
customer_id),
-- creating SQL for number of unpaid orders/instalment_plan monthly basis per customer section

num_unpaid_order as (
select 
customer_id,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status = ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_unpaid_orders_1m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_unpaid_orders_3m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_unpaid_orders_6m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_unpaid_orders_9m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')- 365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_unpaid_orders_12m,
sum(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then 1 else 0 end) as No_of_unpaid_orders_tot


from dl.instalment_plans
where currency='AED' and num_instalments=3
group by 
customer_id),

-- creating SQL for Average Amount of unpaid orders/instalment_plan  per customer

avg_unpaid_order as (
select
customer_id,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_unpaid else null end),0) as Avg_unpaid_amt_1m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_unpaid else null end),0) as Avg_unpaid_amt_3m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_unpaid else null end),0) as Avg_unpaid_amt_6m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_unpaid else null end),0) as Avg_unpaid_amt_9m,
coalesce(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_unpaid else null end),0) as Avg_unpaid_amt_12m,
coalesce(avg(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('unpaid') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_unpaid else null end),0) as Avg_unpaid_amt_tot

from dl.instalment_plans 
WHERE currency='AED' and num_instalments=3
group by 
customer_id),

-- creating SQL for Total due amount in 1 month and 3 month

tot_amt_due as (
select
customer_id,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_due else 0 end) as Total_due_amt_1m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  total_amount_due else 0 end) as Total_due_amt_3m

from dl.instalment_plans 
WHERE currency='AED' and num_instalments=3
group by 
customer_id),

-- SQL for Total Number of Due instalment plans due 1m,3m

tot_num_ins_due as (
select
customer_id,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  1 else 0 end) as No_of_due_instalment_1m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 then  1 else 0 end) as No_of_due_instalment_3m

from dl.instalment_plans
where currency='AED' and num_instalments=3
group by 
customer_id),

-- SQL for Total Number of time instalment paid on/before due date history
tot_num_ins_before_due as (
select
a.customer_id,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled<=0 then 1 else 0 end) as No_of_ins_paid_ontime_1m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled<=0 then 1 else 0 end) as No_of_ins_paid_ontime_3m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled<=0 then 1 else 0 end) as No_of_ins_paid_ontime_6m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled<=0 then 1 else 0 end) as No_of_ins_paid_ontime_9m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled<=0 then 1 else 0 end) as No_of_ins_paid_ontime_12m,
sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled<=0 then 1 else 0 end) as No_of_ins_paid_ontime_tot

from dl.instalment_plans a
left join dl.instalments b
on a.instalment_plan_id = b.instalment_plan_id 
where a.currency='AED' and a.num_instalments=3
group by
a.customer_id),

-- SQL for Total Number of time instalment paid after due date history

tot_num_ins_aftr_due as (

select
a.customer_id,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled>0 then 1 else 0 end) as No_of_ins_notpaidondue_1m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled>0 then 1 else 0 end) as No_of_ins_notpaidondue_3m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled>0 then 1 else 0 end) as No_of_ins_notpaidondue_6m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled>0 then 1 else 0 end) as No_of_ins_notpaidondue_9m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled>0 then 1 else 0 end) as No_of_ins_notpaidondue_12m,
sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0 and b.status='paid' and b.completed::date-b.scheduled>0 then 1 else 0 end) as No_of_ins_notpaidondue_tot

from dl.instalment_plans a
left join dl.instalments b
on a.instalment_plan_id = b.instalment_plan_id 
where a.currency='AED' and a.num_instalments=3
group by
a.customer_id),

-- Creating SQL for Average Repay time history of the customer -- left join to this table
avg_repay_time_hist as (

select
a.customer_id,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0  then b.max_completed::date-a.created::date else null end),0) as avg_repay_time_day_3m,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0  then b.max_completed::date-a.created::date else null end),0) as avg_repay_time_day_6m,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0  then b.max_completed::date-a.created::date else null end),0) as avg_repay_time_day_9m,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0  then b.max_completed::date-a.created::date else null end),0) as avg_repay_time_day_12m,
coalesce(avg(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid') and a.status='captured' and a.num_instalments=3 and a.currency='AED' 
and a.downpayment_refunded_amount=0  then b.max_completed::date-a.created::date else null end),0) as avg_repay_time_day_tot

from
dl.instalment_plans a
join (select 
instalment_plan_id,
max(completed)  max_completed
from dl.instalments
where status='paid' and completed is not null
group by instalment_plan_id ) b
on a.instalment_plan_id = b.instalment_plan_id 
WHERE a.currency='AED' and a.num_instalments=3
group by
a.customer_id),

-- Order Dataset creation
-- Creating SQL for Debt to order for customer 

debt_to_ordr as (

select
customer_id,
coalesce(round(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 and total_amount<>0 then (total_amount_unpaid+total_amount_due)/total_amount else null end),2),0) as Debt_to_order_1m,
coalesce(round(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 and total_amount<>0then  (total_amount_unpaid+total_amount_due)/total_amount else null end),2),0) as Debt_to_order_3m,
coalesce(round(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 and total_amount<>0 then  (total_amount_unpaid+total_amount_due)/total_amount else null end),2),0) as Debt_to_order_6m,
coalesce(round(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 and total_amount<>0 then  (total_amount_unpaid+total_amount_due)/total_amount else null end),2),0) as Debt_to_order_9m,
coalesce(round(avg(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 and total_amount<>0 then  (total_amount_unpaid+total_amount_due)/total_amount else null end),2),0) as Debt_to_order_12m,
coalesce(round(avg(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and instalment_plan_status in ('paid','unpaid','due') and status='captured' and num_instalments=3 and currency='AED' and downpayment_refunded_amount=0 and total_amount<>0 then  (total_amount_unpaid+total_amount_due)/total_amount else null end),2),0) as Debt_to_order_tot

from dl.instalment_plans 
WHERE currency='AED' and num_instalments=3
group by 
customer_id),


-- Total Number of Items in the cart for each customer in last 1 month, 3 month , 6 month , 9 month , 12 month , total items in lifetime
-- Number of days since first and last order, Number of months since first and last order

order_hist as 
(

select 
b.customer_id,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then c.qty else 0 end) as No_of_items_1m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then c.qty else 0 end) as No_of_items_3m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then c.qty else 0 end) as No_of_items_6m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then c.qty else 0 end) as No_of_items_9m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then c.qty else 0 end) as No_of_items_12m,
sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then c.qty else 0 end) as No_of_items_tot,
-- Number of days since first and last order
current_date::date-d.min_created::date No_of_days_since_first_order,
round((current_date::date-d.min_created::date)/30,1) No_of_mnth_since_first_order,
current_date::date-d.max_created::date No_of_days_since_last_order,
round((current_date::date-d.max_created::date)/30,1) No_of_mnth_since_last_order,

-- Total order value in last 1,3,6,9,12 and tot
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else 0 end) as total_order_amount_1m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else 0 end) as total_order_amount_3m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else 0 end) as total_order_amount_6m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else 0 end) as total_order_amount_9m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else 0 end) as total_order_amount_12m,
sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else 0 end) as total_order_amount_tot,
-- Average order value in lifetime with postpay history for each customer
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else Null end),0) as average_order_value_1m,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else Null end),0) as average_order_value_3m,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else Null end),0) as average_order_value_6m,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else Null end),0) as average_order_value_9m,
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else Null end),0) as average_order_value_12m,
coalesce(avg(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then a.total_amount else Null end),0) as average_order_value_tot,
-- Total Number of time customer sucessfully ordered with postpay which is either paid,due ot unpaid
sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='captured'and  b.instalment_plan_status in ('paid','unpaid','due') and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then 1 else 0 end) as  total_no_orders,
-- Number of times denied by postpay in last 1,3,6,9,12 for each customer
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='denied' and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then 1 else 0 end) as No_of_times_denied_1m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='denied' and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then 1 else 0 end) as No_of_times_denied_3m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='denied' and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then 1 else 0 end) as No_of_times_denied_6m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='denied' and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then 1 else 0 end) as No_of_times_denied_9m,
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='denied' and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then 1 else 0 end) as No_of_times_denied_12m,
sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.status='denied' and a.num_instalments=3 and a.currency='AED' and a.total_amount<>0 then 1 else 0 end) as Total_Number_of_denied

from
dl.orders a
join dl.instalment_plans b
on a.order_id=b.order_id 
join dl.cart c
on a.order_id = c.order_id
join (select customer_id,
             min(created) min_created,
             max(created) max_created
      from dl.orders where num_instalments=3 and status='captured'
     and currency='AED' and total_amount <> 0
     group by customer_id) d
on a.customer_id= d.customer_id
where a.currency='AED' and a.num_instalments=3
     
group by 
b.customer_id,
current_date::date-d.min_created::date,
round((current_date::date-d.min_created::date)/30,1),
current_date::date-d.max_created::date,
round((current_date::date-d.max_created::date)/30,1)),

-- Payments(Cards) dataset creation

-- Creating dataset for payments by cards and their details
payment_cards as (

select 
customer_id,
-- Number of unique card history in last 1,3,6,9,12 months
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null then card_number end )) as No_of_card_lst_1m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null then card_number end )) as No_of_card_lst_3m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null then card_number end )) as No_of_card_lst_6m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null then card_number end )) as No_of_card_lst_9m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null then card_number end )) as No_of_card_lst_12m,
count(distinct(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null then card_number end )) as No_of_card_tot,
-- Number of apply pay transaction in last 1,3,6,9,12 months
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and is_apple_pay = 'true' then 1 else 0 end ) as No_of_applepay_trans_1m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and is_apple_pay = 'true' then 1 else 0 end ) as No_of_applepay_trans_3m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and is_apple_pay = 'true' then 1 else 0 end ) as No_of_applepay_trans_6m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and is_apple_pay = 'true' then 1 else 0 end ) as No_of_applepay_trans_9m,
sum(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and is_apple_pay = 'true' then 1 else 0 end ) as No_of_applepay_trans_12m,
sum(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and is_apple_pay = 'true' then 1 else 0 end ) as No_of_applepay_trans_tot,
-- Number of debit cards in last 1,3,6,9,12 and total
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%debit%' then card_number end )) as No_of_debit_card_lst_1m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%debit%' then card_number end )) as No_of_debit_card_lst_3m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%debit%' then card_number end )) as No_of_debit_card_lst_6m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%debit%' then card_number end )) as No_of_debit_card_lst_9m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%debit%' then card_number end )) as No_of_debit_card_lst_12m,
count(distinct(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%debit%'  then card_number end )) as No_of_debit_card_tot,
-- Number of credit cards in last 1,3,6,9,12 and total
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%credit%' or payment_method_type ilike '%charge%card%' then card_number end )) as No_of_credit_card_lst_1m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%credit%' or payment_method_type ilike '%charge%card%' then card_number end )) as No_of_credit_card_lst_3m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%credit%' or payment_method_type ilike '%charge%card%' then card_number end )) as No_of_credit_card_lst_6m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%credit%' or payment_method_type ilike '%charge%card%' then card_number end )) as No_of_credit_card_lst_9m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%credit%' or payment_method_type ilike '%charge%card%' then card_number end )) as No_of_credit_card_lst_12m,
count(distinct(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null and payment_method_type ilike '%credit%' or payment_method_type ilike '%charge%card%' then card_number end )) as No_of_credit_card_tot,
-- Number of Master and visa card in last 1,3,6,9,12 and total
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%mastercard%' or payment_method_brand ilike '%visa%') then card_number end )) as No_of_MASVISA_card_lst_1m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%mastercard%' or payment_method_brand ilike '%visa%') then card_number end )) as No_of_MASVISA_card_lst_3m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%mastercard%' or payment_method_brand ilike '%visa%') then card_number end )) as No_of_MASVISA_card_lst_6m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%mastercard%' or payment_method_brand ilike '%visa%') then card_number end )) as No_of_MASVISA_card_lst_9m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%mastercard%' or payment_method_brand ilike '%visa%') then card_number end )) as No_of_MASVISA_card_lst_12m,
count(distinct(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%mastercard%' or payment_method_brand ilike '%visa%') then card_number end )) as No_of_MASVISA_card_tot,
-- Number of AMEX,DINERS CLUB CARD
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%amex%' or payment_method_brand ilike '%diners%club%international%') then card_number end )) as No_of_amex_diner_card_lst_1m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%amex%' or payment_method_brand ilike '%diners%club%international%') then card_number end )) as No_of_amex_diner_card_lst_3m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%amex%' or payment_method_brand ilike '%diners%club%international%') then card_number end )) as No_of_amex_diner_card_lst_6m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%amex%' or payment_method_brand ilike '%diners%club%international%') then card_number end )) as No_of_amex_diner_card_lst_9m,
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%amex%' or payment_method_brand ilike '%diners%club%international%') then card_number end )) as No_of_amex_diner_card_lst_12m,
count(distinct(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_brand ilike '%amex%' or payment_method_brand ilike '%diners%club%international%') then card_number end )) as No_of_amex_diner_card_tot,
-- 

-- Number of global bank cards in last 1,3,6,9,12 and tot
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_bank ilike '%hsbc%'
or payment_method_bank ilike '%citi%bank%' or payment_method_bank ilike '%standard%chartered%' or
payment_method_bank ilike '%j%p%morgan%' or 
payment_method_bank ilike '%bank%of%america%' or  payment_method_bank ilike '%barclays%' 
or payment_method_bank ilike '%goldman%' or payment_method_bank ilike '%wells%fargo%'
or  payment_method_bank  ilike '%royal%bank%of%scotland%' or payment_method_bank ilike '%UBS%'
or payment_method_bank ilike '%ABSA%' or payment_method_bank ilike '%anz%'
or payment_method_bank ilike '%AMERICAN%EXPRESS%' or payment_method_bank ilike '%AMEX%'
or payment_method_bank ilike '%bank%of%china%' or payment_method_bank ilike '%china%construction%bank%'
or payment_method_bank ilike '%banco%'or payment_method_bank ilike '%deut%') then card_number end )) as No_of_global_bank_cards_1m,

count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_bank ilike '%hsbc%'
or payment_method_bank ilike '%citi%bank%' or payment_method_bank ilike '%standard%chartered%' or
payment_method_bank ilike '%j%p%morgan%' or 
payment_method_bank ilike '%bank%of%america%' or  payment_method_bank ilike '%barclays%' 
or payment_method_bank ilike '%goldman%' or payment_method_bank ilike '%wells%fargo%'
or  payment_method_bank  ilike '%royal%bank%of%scotland%' or payment_method_bank ilike '%UBS%'
or payment_method_bank ilike '%ABSA%' or payment_method_bank ilike '%anz%'
or payment_method_bank ilike '%AMERICAN%EXPRESS%' or payment_method_bank ilike '%AMEX%'
or payment_method_bank ilike '%bank%of%china%' or payment_method_bank ilike '%china%construction%bank%'
or payment_method_bank ilike '%banco%' or payment_method_bank ilike '%deut%') then card_number end )) as No_of_global_bank_cards_3m,

count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_bank ilike '%hsbc%'
or payment_method_bank ilike '%citi%bank%' or payment_method_bank ilike '%standard%chartered%' or
payment_method_bank ilike '%j%p%morgan%' or 
payment_method_bank ilike '%bank%of%america%' or  payment_method_bank ilike '%barclays%' 
or payment_method_bank ilike '%goldman%' or payment_method_bank ilike '%wells%fargo%'
or  payment_method_bank  ilike '%royal%bank%of%scotland%' or payment_method_bank ilike '%UBS%'
or payment_method_bank ilike '%ABSA%' or payment_method_bank ilike '%anz%'
or payment_method_bank ilike '%AMERICAN%EXPRESS%' or payment_method_bank ilike '%AMEX%'
or payment_method_bank ilike '%bank%of%china%' or payment_method_bank ilike '%china%construction%bank%'
or payment_method_bank ilike '%banco%' or  payment_method_bank ilike '%deut%') then card_number end )) as No_of_global_bank_cards_6m,

count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_bank ilike '%hsbc%'
or payment_method_bank ilike '%citi%bank%' or payment_method_bank ilike '%standard%chartered%' or
payment_method_bank ilike '%j%p%morgan%' or 
payment_method_bank ilike '%bank%of%america%' or  payment_method_bank ilike '%barclays%' 
or payment_method_bank ilike '%goldman%' or payment_method_bank ilike '%wells%fargo%'
or  payment_method_bank  ilike '%royal%bank%of%scotland%' or payment_method_bank ilike '%UBS%'
or payment_method_bank ilike '%ABSA%' or payment_method_bank ilike '%anz%'
or payment_method_bank ilike '%AMERICAN%EXPRESS%' or payment_method_bank ilike '%AMEX%'
or payment_method_bank ilike '%bank%of%china%' or payment_method_bank ilike '%china%construction%bank%'
or payment_method_bank ilike '%banco%' or payment_method_bank ilike '%deut%') then card_number end )) as No_of_global_bank_cards_9m,

count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_bank ilike '%hsbc%'
or payment_method_bank ilike '%citi%bank%' or payment_method_bank ilike '%standard%chartered%' or
payment_method_bank ilike '%j%p%morgan%' or 
payment_method_bank ilike '%bank%of%america%' or  payment_method_bank ilike '%barclays%' 
or payment_method_bank ilike '%goldman%' or payment_method_bank ilike '%wells%fargo%'
or  payment_method_bank  ilike '%royal%bank%of%scotland%' or payment_method_bank ilike '%UBS%'
or payment_method_bank ilike '%ABSA%' or payment_method_bank ilike '%anz%'
or payment_method_bank ilike '%AMERICAN%EXPRESS%' or payment_method_bank ilike '%AMEX%'
or payment_method_bank ilike '%bank%of%china%' or payment_method_bank ilike '%china%construction%bank%'
or payment_method_bank ilike '%banco%' or payment_method_bank ilike '%deut%') then card_number end )) as No_of_global_bank_cards_12m,

count(distinct(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null) and (payment_method_bank ilike '%hsbc%'
or payment_method_bank ilike '%citi%bank%' or payment_method_bank ilike '%standard%chartered%' or
payment_method_bank ilike '%j%p%morgan%' or 
payment_method_bank ilike '%bank%of%america%' or  payment_method_bank ilike '%barclays%' 
or payment_method_bank ilike '%goldman%' or payment_method_bank ilike '%wells%fargo%'
or  payment_method_bank  ilike '%royal%bank%of%scotland%' or payment_method_bank ilike '%UBS%'
or payment_method_bank ilike '%ABSA%' or payment_method_bank ilike '%anz%'
or payment_method_bank ilike '%AMERICAN%EXPRESS%' or payment_method_bank ilike '%AMEX%'
or payment_method_bank ilike '%bank%of%china%' or payment_method_bank ilike '%china%construction%bank%'
or payment_method_bank ilike '%banco%' or payment_method_bank ilike '%deut%') then card_number end )) as No_of_global_bank_cards_tot,

-- Number of local bank cards in last 1,3,6,9,12 and tot
count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null)
 and (payment_method_bank ilike '%abu%dhabi%commercial%bank%' or 
payment_method_bank ilike '%mashreq%' or payment_method_bank ilike '%emirates%nbd%'
or payment_method_bank ilike '%first%abu%dhabi%bank%' or payment_method_bank ilike '%abu%dhabi%islamic%bank%'
or payment_method_bank ilike '%ajman%bank%' or payment_method_bank ilike '%al%hilal%' 
or payment_method_bank ilike '%sharjah%islamic%bank%' or payment_method_bank ilike '%commercial%bank%of%dubai%' 
or payment_method_bank ilike '%emirates%islamic%bank%' or payment_method_bank ilike '%dubai%islamic%bank%'
or payment_method_bank ilike '%national%bank%fujairah%' or payment_method_bank ilike '%national%bank%ras%'
or payment_method_bank ilike '%noor%bank%' or payment_method_bank ilike '%sharjah%islamic%bank%'
or payment_method_bank ilike '%united%arab%bank%' or payment_method_bank ilike '%united%arab%bank%') then card_number end )) as No_of_local_bank_cards_1m,

count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null)
 and (payment_method_bank ilike '%abu%dhabi%commercial%bank%' or 
payment_method_bank ilike '%mashreq%' or payment_method_bank ilike '%emirates%nbd%'
or payment_method_bank ilike '%first%abu%dhabi%bank%' or payment_method_bank ilike '%abu%dhabi%islamic%bank%'
or payment_method_bank ilike '%ajman%bank%' or payment_method_bank ilike '%al%hilal%' 
or payment_method_bank ilike '%sharjah%islamic%bank%' or payment_method_bank ilike '%commercial%bank%of%dubai%' 
or payment_method_bank ilike '%emirates%islamic%bank%' or payment_method_bank ilike '%dubai%islamic%bank%'
or payment_method_bank ilike '%national%bank%fujairah%' or payment_method_bank ilike '%national%bank%ras%'
or payment_method_bank ilike '%noor%bank%' or payment_method_bank ilike '%sharjah%islamic%bank%'
or payment_method_bank ilike '%united%arab%bank%' or payment_method_bank ilike '%united%arab%bank%') then card_number end )) as No_of_local_bank_cards_3m,

count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null)
 and (payment_method_bank ilike '%abu%dhabi%commercial%bank%' or 
payment_method_bank ilike '%mashreq%' or payment_method_bank ilike '%emirates%nbd%'
or payment_method_bank ilike '%first%abu%dhabi%bank%' or payment_method_bank ilike '%abu%dhabi%islamic%bank%'
or payment_method_bank ilike '%ajman%bank%' or payment_method_bank ilike '%al%hilal%' 
or payment_method_bank ilike '%sharjah%islamic%bank%' or payment_method_bank ilike '%commercial%bank%of%dubai%' 
or payment_method_bank ilike '%emirates%islamic%bank%' or payment_method_bank ilike '%dubai%islamic%bank%'
or payment_method_bank ilike '%national%bank%fujairah%' or payment_method_bank ilike '%national%bank%ras%'
or payment_method_bank ilike '%noor%bank%' or payment_method_bank ilike '%sharjah%islamic%bank%'
or payment_method_bank ilike '%united%arab%bank%' or payment_method_bank ilike '%united%arab%bank%') then card_number end )) as No_of_local_bank_cards_6m,


count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null)
 and (payment_method_bank ilike '%abu%dhabi%commercial%bank%' or 
payment_method_bank ilike '%mashreq%' or payment_method_bank ilike '%emirates%nbd%'
or payment_method_bank ilike '%first%abu%dhabi%bank%' or payment_method_bank ilike '%abu%dhabi%islamic%bank%'
or payment_method_bank ilike '%ajman%bank%' or payment_method_bank ilike '%al%hilal%' 
or payment_method_bank ilike '%sharjah%islamic%bank%' or payment_method_bank ilike '%commercial%bank%of%dubai%' 
or payment_method_bank ilike '%emirates%islamic%bank%' or payment_method_bank ilike '%dubai%islamic%bank%'
or payment_method_bank ilike '%national%bank%fujairah%' or payment_method_bank ilike '%national%bank%ras%'
or payment_method_bank ilike '%noor%bank%' or payment_method_bank ilike '%sharjah%islamic%bank%'
or payment_method_bank ilike '%united%arab%bank%' or payment_method_bank ilike '%united%arab%bank%') then card_number end )) as No_of_local_bank_cards_9m,

count(distinct(case when created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null)
 and (payment_method_bank ilike '%abu%dhabi%commercial%bank%' or 
payment_method_bank ilike '%mashreq%' or payment_method_bank ilike '%emirates%nbd%'
or payment_method_bank ilike '%first%abu%dhabi%bank%' or payment_method_bank ilike '%abu%dhabi%islamic%bank%'
or payment_method_bank ilike '%ajman%bank%' or payment_method_bank ilike '%al%hilal%' 
or payment_method_bank ilike '%sharjah%islamic%bank%' or payment_method_bank ilike '%commercial%bank%of%dubai%' 
or payment_method_bank ilike '%emirates%islamic%bank%' or payment_method_bank ilike '%dubai%islamic%bank%'
or payment_method_bank ilike '%national%bank%fujairah%' or payment_method_bank ilike '%national%bank%ras%'
or payment_method_bank ilike '%noor%bank%' or payment_method_bank ilike '%sharjah%islamic%bank%'
or payment_method_bank ilike '%united%arab%bank%' or payment_method_bank ilike '%united%arab%bank%') then card_number end )) as No_of_local_bank_cards_12m,

count(distinct(case when created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and (status='captured' and num_instalments>1 and currency='AED' and total_amount<>0 and card_first_six_digits is not null and card_last_four_digits is not null)
 and (payment_method_bank ilike '%abu%dhabi%commercial%bank%' or 
payment_method_bank ilike '%mashreq%' or payment_method_bank ilike '%emirates%nbd%'
or payment_method_bank ilike '%first%abu%dhabi%bank%' or payment_method_bank ilike '%abu%dhabi%islamic%bank%'
or payment_method_bank ilike '%ajman%bank%' or payment_method_bank ilike '%al%hilal%' 
or payment_method_bank ilike '%sharjah%islamic%bank%' or payment_method_bank ilike '%commercial%bank%of%dubai%' 
or payment_method_bank ilike '%emirates%islamic%bank%' or payment_method_bank ilike '%dubai%islamic%bank%'
or payment_method_bank ilike '%national%bank%fujairah%' or payment_method_bank ilike '%national%bank%ras%'
or payment_method_bank ilike '%noor%bank%' or payment_method_bank ilike '%sharjah%islamic%bank%'
or payment_method_bank ilike '%united%arab%bank%' or payment_method_bank ilike '%united%arab%bank%') then card_number end )) as No_of_local_bank_cards_tot,



max(days_to_expiry_lst_used_card) days_to_expiry_lst_used_card,
max(months_to_expiry_lst_used_card) months_to_expiry_lst_used_card

from 

(
select
orders.customer_id,
order_id,
created,
card_first_six_digits,
card_last_four_digits,
card_first_six_digits||card_last_four_digits as card_number,
status,
total_amount,
currency,
customer_date_joined,
num_instalments,
payment_method_brand, -- visa,mastercard,discover,visa/dankort,american express,discover,cirrus,diners club international,rupay,maestro
payment_method_expires,-- payment method expiry date
is_apple_pay, -- null,true,false
payment_method_country, -- list of countries the card belongs
payment_method_bank,-- issuing bank or payment processor such as AMEX
payment_method_type,-- debit,DEBIT,charge card,null,'',CREDIT
(case when a.days_to_expiry_lst_used_card < 0 then 0 else a.days_to_expiry_lst_used_card end) as days_to_expiry_lst_used_card,
(case when a.months_to_expiry_lst_used_card <0 then 0 else a.months_to_expiry_lst_used_card end) as months_to_expiry_lst_used_card

from 
dl.orders
join 
(SELECT DISTINCT
  customer_id,
  -- it captures the months and days to expiry of last used card from last order
  FIRST_VALUE(payment_method_expires::date-created::date) OVER (PARTITION BY customer_id ORDER BY created DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS days_to_expiry_lst_used_card,
  round((FIRST_VALUE(payment_method_expires::date-created::date) OVER (PARTITION BY customer_id ORDER BY created DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING))/30,1) AS months_to_expiry_lst_used_card
FROM
  dl.orders
 where orders.payment_method_expires is not null and orders.num_instalments>1 and orders.status='captured' 
and orders.currency='AED' and orders.total_amount <> 0 
) a 
on orders.customer_id=a.customer_id

where dl.orders.payment_method_expires is not null and dl.orders.currency='AED' and dl.orders.num_instalments=3 )
where customer_id<>'' 
group by customer_id),

-- Customer Detail (Demographic)

 -- join this table with instalments plan details
cust_demo as(
select
customer_id, 
CURRENT_DATE::date-created::date Reg_with_postpay_day,
ROUND((CURRENT_DATE::date-created::date)/30,1) Reg_with_postpay_month,
to_number(EXTRACT(YEAR FROM CURRENT_DATE),'9999')-to_number((substring(id_number,4,4)),'9999') as Age_of_cust

from dwh.dl.customers 
where id_number like '784%'),

-- Customer Details (Device)

cust_dev as (
select 
a.customer_id,

-- Number of 'Apple' device transaction in last 1,3,6,9,12 and tot
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%iphone%'
or b.user_agent ilike '%macintosh%') then 1 else 0 end) as No_of_apple_device_transaction_1m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%iphone%'
or b.user_agent ilike '%macintosh%') then 1 else 0 end) as No_of_apple_device_transaction_3m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%iphone%'
or b.user_agent ilike '%macintosh%') then 1 else 0 end) as No_of_apple_device_transaction_6m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%iphone%'
or b.user_agent ilike '%macintosh%') then 1 else 0 end) as No_of_apple_device_transaction_9m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%iphone%'
or b.user_agent ilike '%macintosh%') then 1 else 0 end) as No_of_apple_device_transaction_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%iphone%'
or b.user_agent ilike '%macintosh%') then 1 else 0 end) as No_of_apple_device_transaction_tot,


-- Number of 'Android' device transaction in last 1,3,6,9,12 and tot

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%android%') then 1 else 0 end) as No_of_android_device_transaction_1m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%android%') then 1 else 0 end)  as No_of_android_device_transaction_3m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%android%') then 1 else 0 end) as No_of_android_device_transaction_6m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%android%') then 1 else 0 end) as No_of_android_device_transaction_9m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%android%') then 1 else 0 end) as No_of_android_device_transaction_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%android%') then 1 else 0 end) as No_of_android_device_transaction_tot,

-- Number of 'windows' device transaction in last 1,3,6,9,12 and tot

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%window%') then 1 else 0 end) as No_of_win_device_transaction_1m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%window%') then 1 else 0 end)  as No_of_win_device_transaction_3m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%window%') then 1 else 0 end) as No_of_win_device_transaction_6m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%window%') then 1 else 0 end) as No_of_win_device_transaction_9m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%window%') then 1 else 0 end) as No_of_win_device_transaction_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent ilike '%window%') then 1 else 0 end) as No_of_win_device_transaction_tot,

-- Number of 'missing' device transaction 1,2,3,6,9,12 and tot
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent is null
or b.user_agent ilike '') then 1 else 0 end) as No_of_missing_device_transaction_1m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent is null
or b.user_agent ilike '') then 1 else 0 end)  as No_of_missing_device_transaction_3m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent is null
or b.user_agent ilike '') then 1 else 0 end) as No_of_missing_device_transaction_6m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent is null
or b.user_agent ilike '') then 1 else 0 end) as No_of_missing_device_transaction_9m,

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent is null
or b.user_agent ilike '') then 1 else 0 end) as No_of_missing_device_transaction_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') 
and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and 
a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 and (b.user_agent is null
or b.user_agent ilike '') then 1 else 0 end) as No_of_missing_device_transaction_tot



from dl.instalment_plans a
join dl.orders b 
on a.order_id = b.order_id
where a.currency='AED' and a.num_instalments=3
group by a.customer_id),

-- Merchant details based on clubbed categories for each customer

merchant_det as (
select 
a.customer_id,
-- SQL for creating variables for number of orders in merchant category ''Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids''
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids') then 1 else 0 end) as No_of_orders_Go_others_2m,


sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids') then 1 else 0 end) as No_of_orders_Go_others_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids') then 1 else 0 end) as No_of_orders_Go_others_tot,

-- SQL for average amount ordered in merchant category ''Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids''
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids') then a.total_amount else null end),0) as avg_orders_amt_Go_others_2m,


coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids') then a.total_amount else null end),0) as avg_orders_amt_Go_others_12m,

coalesce(avg(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('Default','Postpay-test','furniture','services','travel','others','auto','pets','government services','kids') then a.total_amount else null end),0) as avg_orders_amt_Go_others_tot,

-- SQL for creating variables for number of orders in merchant category 'health','wellness','clinic','sports and fitness','optics' 
sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('health','wellness','clinic','sports and fitness','optics') then 1 else 0 end) as No_of_orders_Health_well_fitness_2m,


sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('health','wellness','clinic','sports and fitness','optics') then 1 else 0 end) as No_of_orders_Health_well_fitness_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('health','wellness','clinic','sports and fitness','optics') then 1 else 0 end) as No_of_orders_Health_well_fitness_tot,

--SQL for average amount ordered in merchant category 'health','wellness','clinic','sports and fitness','optics'
coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('health','wellness','clinic','sports and fitness','optics') then a.total_amount else null end),0) as avg_orders_amt_health_well_fitness_2m,


coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('health','wellness','clinic','sports and fitness','optics') then a.total_amount else null end),0) as avg_orders_amt_health_well_fitness_12m,

coalesce(avg(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('health','wellness','clinic','sports and fitness','optics') then a.total_amount else null end),0) as avg_orders_amt_health_well_fitness_tot,


---- Creating SQL for number of orders for home applicance,electronic,perfumes

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('home appliances','electronics','perfumes') then 1 else 0 end) as No_of_orders_hom_elec_2m,


sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('home appliances','electronics','perfumes') then 1 else 0 end) as No_of_orders_hom_elec_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('home appliances','electronics','perfumes') then 1 else 0 end) as No_of_orders_hom_elec_tot,

-- SQL for average amount ordered for home applicance,electronic,perfumes

coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('home appliances','electronics','perfumes') then a.total_amount else null end),0) as avg_orders_amt_hom_elec_2m,


coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('home appliances','electronics','perfumes') then a.total_amount else null end),0) as avg_orders_amt_hom_elec_12m,

coalesce(avg(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('home appliances','electronics','perfumes') then a.total_amount else null end),0) as avg_orders_amt_hom_elec_tot,


-- Creating SQL for number of orders for 'gift card','entertainment','beauty','fashion','gifts','jewelry & watches'

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('gift card','entertainment','beauty','fashion','gifts','jewelry & watches') then 1 else 0 end) as No_of_orders_Lifestyle_fashion_en_gift_2m,


sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('gift card','entertainment','beauty','fashion','gifts','jewelry & watches') then 1 else 0 end) as No_of_orders_Lifestyle_fashion_en_gift_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('gift card','entertainment','beauty','fashion','gifts','jewelry & watches') then 1 else 0 end) as No_of_orders_Lifestyle_fashion_en_gift_tot,

-- SQL for average amount ordered for 'gift card','entertainment','beauty','fashion','gifts','jewelry & watches'

coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('gift card','entertainment','beauty','fashion','gifts','jewelry & watches') then a.total_amount else null end),0) as avg_orders_amt_Lifestyle_fashion_en_gift_2m,


coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('gift card','entertainment','beauty','fashion','gifts','jewelry & watches') then a.total_amount else null end),0) as avg_orders_amt_Lifestyle_fashion_en_gift_12m,

coalesce(avg(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('gift card','entertainment','beauty','fashion','gifts','jewelry & watches') then a.total_amount else null end),0) as avg_orders_amt_Lifestyle_fashion_en_gift_tot,
-- Creating SQL for number of orders for 'education platforms','education'

sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('education platforms','education') then 1 else 0 end) as No_of_orders_edu_rel_2m,


sum(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('education platforms','education') then 1 else 0 end) as No_of_orders_edu_rel_12m,

sum(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('education platforms','education') then 1 else 0 end) as No_of_orders_edu_rel_tot,

-- SQL for average amount ordered for 'education platforms','education'

coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-60
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('education platforms','education') then a.total_amount else null end),0) as avg_orders_amt_edu_rel_2m,


coalesce(avg(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('education platforms','education') then a.total_amount else null end),0) as avg_orders_amt_edu_rel_12m,

coalesce(avg(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and
a.currency='AED' and a.downpayment_refunded_amount=0 and c.name in ('education platforms','education') then a.total_amount else null end),0) as avg_orders_amt_edu_rel_tot,

-- Counting Number of merchants shopped in last 1,3,6,9,12 months

count(distinct(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-30
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 then a.merchant_id end)) as No_of_merchants_1m,

count(distinct(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-90
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 then a.merchant_id end)) as No_of_merchants_3m,

count(distinct(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-180
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 then a.merchant_id end)) as No_of_merchants_6m,

count(distinct(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-270
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 then a.merchant_id end)) as No_of_merchants_9m,

count(distinct(case when a.created >= (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second')-365
and a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 then a.merchant_id end)) as No_of_merchants_12m,

count(distinct(case when a.created < (TIMESTAMP 'epoch' + EXTRACT(EPOCH FROM current_timestamp) * INTERVAL '1 second') and a.instalment_plan_status in ('paid','unpaid','due') and a.status='captured' and a.num_instalments=3 and a.currency='AED' and a.downpayment_refunded_amount=0 then a.merchant_id end)) as No_of_merchants_tot




from dwh.dl.instalment_plans a -- merchant_id in Datalake (dl) is id in api_prod.merchants_merchant 
join dwh.api_prod.merchants_merchant b -- and it is connected to merchant categories in api_prod by category_id
on a.merchant_id = b.id
join dwh.api_prod.merchants_category c
on b.category_id = c.id 
where a.num_instalments=3 and a.currency='AED'
group by a.customer_id)





select 
current_timestamp as Data_load_timestamp,
num_ins.*,
avg_ins.Avg_ins_amt_1m,
avg_ins.Avg_ins_amt_3m,
avg_ins.Avg_ins_amt_6m,
avg_ins.Avg_ins_amt_9m,
avg_ins.Avg_ins_amt_12m,
avg_ins.Avg_ins_amt_tot,

sum_prin.Tot_ins_amt_1m,
sum_prin.Tot_ins_amt_3m,
sum_prin.Tot_ins_amt_6m,
sum_prin.Tot_ins_amt_9m,
sum_prin.Tot_ins_amt_12m,
sum_prin.Tot_ins_amt_tot,

num_unpaid_order.No_of_unpaid_orders_1m,
num_unpaid_order.No_of_unpaid_orders_3m,
num_unpaid_order.No_of_unpaid_orders_6m,
num_unpaid_order.No_of_unpaid_orders_9m,
num_unpaid_order.No_of_unpaid_orders_12m,
num_unpaid_order.No_of_unpaid_orders_tot,

avg_unpaid_order.Avg_unpaid_amt_1m,
avg_unpaid_order.Avg_unpaid_amt_3m,
avg_unpaid_order.Avg_unpaid_amt_6m,
avg_unpaid_order.Avg_unpaid_amt_9m,
avg_unpaid_order.Avg_unpaid_amt_12m,
avg_unpaid_order.Avg_unpaid_amt_tot,

tot_amt_due.Total_due_amt_1m,
tot_amt_due.Total_due_amt_3m,

tot_num_ins_due.No_of_due_instalment_1m,
tot_num_ins_due.No_of_due_instalment_3m,

tot_num_ins_before_due.No_of_ins_paid_ontime_1m,
tot_num_ins_before_due.No_of_ins_paid_ontime_3m,
tot_num_ins_before_due.No_of_ins_paid_ontime_6m,
tot_num_ins_before_due.No_of_ins_paid_ontime_9m,
tot_num_ins_before_due.No_of_ins_paid_ontime_12m,
tot_num_ins_before_due.No_of_ins_paid_ontime_tot,

tot_num_ins_aftr_due.No_of_ins_notpaidondue_1m,
tot_num_ins_aftr_due.No_of_ins_notpaidondue_3m,
tot_num_ins_aftr_due.No_of_ins_notpaidondue_6m,
tot_num_ins_aftr_due.No_of_ins_notpaidondue_9m,
tot_num_ins_aftr_due.No_of_ins_notpaidondue_12m,
tot_num_ins_aftr_due.No_of_ins_notpaidondue_tot,

avg_repay_time_hist.avg_repay_time_day_3m,
avg_repay_time_hist.avg_repay_time_day_6m,
avg_repay_time_hist.avg_repay_time_day_9m,
avg_repay_time_hist.avg_repay_time_day_12m,
avg_repay_time_hist.avg_repay_time_day_tot,

debt_to_ordr.Debt_to_order_1m,
debt_to_ordr.Debt_to_order_3m,
debt_to_ordr.Debt_to_order_6m,
debt_to_ordr.Debt_to_order_9m,
debt_to_ordr.Debt_to_order_12m,
debt_to_ordr.Debt_to_order_tot,

order_hist.No_of_items_1m,
order_hist.No_of_items_3m,
order_hist.No_of_items_6m,
order_hist.No_of_items_9m,
order_hist.No_of_items_12m,
order_hist.No_of_items_tot,

order_hist.No_of_days_since_first_order,
order_hist.No_of_mnth_since_first_order,
order_hist.No_of_days_since_last_order,
order_hist.No_of_mnth_since_last_order,

order_hist.total_order_amount_1m,
order_hist.total_order_amount_3m,
order_hist.total_order_amount_6m,
order_hist.total_order_amount_9m,
order_hist.total_order_amount_12m,
order_hist.total_order_amount_tot,

order_hist.average_order_value_1m,
order_hist.average_order_value_3m,
order_hist.average_order_value_6m,
order_hist.average_order_value_9m,
order_hist.average_order_value_12m,
order_hist.average_order_value_tot,

order_hist.total_no_orders,

order_hist.No_of_times_denied_1m,
order_hist.No_of_times_denied_3m,
order_hist.No_of_times_denied_6m,
order_hist.No_of_times_denied_9m,
order_hist.No_of_times_denied_12m,
order_hist.Total_Number_of_denied,

payment_cards.No_of_card_lst_1m,
payment_cards.No_of_card_lst_3m,
payment_cards.No_of_card_lst_6m,
payment_cards.No_of_card_lst_9m,
payment_cards.No_of_card_lst_12m,
payment_cards.No_of_card_tot,

payment_cards.No_of_applepay_trans_1m,
payment_cards.No_of_applepay_trans_3m,
payment_cards.No_of_applepay_trans_6m,
payment_cards.No_of_applepay_trans_9m,
payment_cards.No_of_applepay_trans_12m,
payment_cards.No_of_applepay_trans_tot,

payment_cards.No_of_debit_card_lst_1m,
payment_cards.No_of_debit_card_lst_3m,
payment_cards.No_of_debit_card_lst_6m,
payment_cards.No_of_debit_card_lst_9m,
payment_cards.No_of_debit_card_lst_12m,
payment_cards.No_of_debit_card_tot,

payment_cards.No_of_credit_card_lst_1m,
payment_cards.No_of_credit_card_lst_3m,
payment_cards.No_of_credit_card_lst_6m,
payment_cards.No_of_credit_card_lst_9m,
payment_cards.No_of_credit_card_lst_12m,
payment_cards.No_of_credit_card_tot,

payment_cards.No_of_MASVISA_card_lst_1m,
payment_cards.No_of_MASVISA_card_lst_3m,
payment_cards.No_of_MASVISA_card_lst_6m,
payment_cards.No_of_MASVISA_card_lst_9m,
payment_cards.No_of_MASVISA_card_lst_12m,
payment_cards.No_of_MASVISA_card_tot,

payment_cards.No_of_amex_diner_card_lst_1m,
payment_cards.No_of_amex_diner_card_lst_3m,
payment_cards.No_of_amex_diner_card_lst_6m,
payment_cards.No_of_amex_diner_card_lst_9m,
payment_cards.No_of_amex_diner_card_lst_12m,
payment_cards.No_of_amex_diner_card_tot,

payment_cards.No_of_global_bank_cards_1m,
payment_cards.No_of_global_bank_cards_3m,
payment_cards.No_of_global_bank_cards_6m,
payment_cards.No_of_global_bank_cards_9m,
payment_cards.No_of_global_bank_cards_12m,
payment_cards.No_of_global_bank_cards_tot,

payment_cards.No_of_local_bank_cards_1m,
payment_cards.No_of_local_bank_cards_3m,
payment_cards.No_of_local_bank_cards_6m,
payment_cards.No_of_local_bank_cards_9m,
payment_cards.No_of_local_bank_cards_12m,
payment_cards.No_of_local_bank_cards_tot,

payment_cards.days_to_expiry_lst_used_card,
payment_cards.months_to_expiry_lst_used_card,

cust_demo.Reg_with_postpay_day,
cust_demo.Reg_with_postpay_month,
cust_demo.Age_of_cust,

cust_dev.No_of_apple_device_transaction_1m,
cust_dev.No_of_apple_device_transaction_3m,
cust_dev.No_of_apple_device_transaction_6m,
cust_dev.No_of_apple_device_transaction_9m,
cust_dev.No_of_apple_device_transaction_12m,
cust_dev.No_of_apple_device_transaction_tot,

cust_dev.No_of_android_device_transaction_1m,
cust_dev.No_of_android_device_transaction_3m,
cust_dev.No_of_android_device_transaction_6m,
cust_dev.No_of_android_device_transaction_9m,
cust_dev.No_of_android_device_transaction_12m,
cust_dev.No_of_android_device_transaction_tot,

cust_dev.No_of_win_device_transaction_1m,
cust_dev.No_of_win_device_transaction_3m,
cust_dev.No_of_win_device_transaction_6m,
cust_dev.No_of_win_device_transaction_9m,
cust_dev.No_of_win_device_transaction_12m,
cust_dev.No_of_win_device_transaction_tot,

cust_dev.No_of_missing_device_transaction_1m,
cust_dev.No_of_missing_device_transaction_3m,
cust_dev.No_of_missing_device_transaction_6m,
cust_dev.No_of_missing_device_transaction_9m,
cust_dev.No_of_missing_device_transaction_12m,
cust_dev.No_of_missing_device_transaction_tot,

merchant_det.No_of_orders_Go_others_2m,
merchant_det.No_of_orders_Go_others_12m,
merchant_det.No_of_orders_Go_others_tot,
merchant_det.avg_orders_amt_Go_others_2m,
merchant_det.avg_orders_amt_Go_others_12m,
merchant_det.avg_orders_amt_Go_others_tot,

merchant_det.No_of_orders_Health_well_fitness_2m,
merchant_det.No_of_orders_Health_well_fitness_12m,
merchant_det.No_of_orders_Health_well_fitness_tot,
merchant_det.avg_orders_amt_health_well_fitness_2m,
merchant_det.avg_orders_amt_health_well_fitness_12m,
merchant_det.avg_orders_amt_health_well_fitness_tot,

merchant_det.No_of_orders_hom_elec_2m,
merchant_det.No_of_orders_hom_elec_12m,
merchant_det.No_of_orders_hom_elec_tot,
merchant_det.avg_orders_amt_hom_elec_2m,
merchant_det.avg_orders_amt_hom_elec_12m,
merchant_det.avg_orders_amt_hom_elec_tot,

merchant_det.No_of_orders_Lifestyle_fashion_en_gift_2m,
merchant_det.No_of_orders_Lifestyle_fashion_en_gift_12m,
merchant_det.No_of_orders_Lifestyle_fashion_en_gift_tot,
merchant_det.avg_orders_amt_Lifestyle_fashion_en_gift_2m,
merchant_det.avg_orders_amt_Lifestyle_fashion_en_gift_12m,
merchant_det.avg_orders_amt_Lifestyle_fashion_en_gift_tot,

merchant_det.No_of_orders_edu_rel_2m,
merchant_det.No_of_orders_edu_rel_12m,
merchant_det.No_of_orders_edu_rel_tot,
merchant_det.avg_orders_amt_edu_rel_2m,
merchant_det.avg_orders_amt_edu_rel_12m,
merchant_det.avg_orders_amt_edu_rel_tot,

merchant_det.No_of_merchants_1m,
merchant_det.No_of_merchants_3m,
merchant_det.No_of_merchants_6m,
merchant_det.No_of_merchants_9m,
merchant_det.No_of_merchants_12m,
merchant_det.No_of_merchants_tot



from num_ins 
-- Joining Num_ins and avg_ins
join avg_ins
on num_ins.customer_id=avg_ins.customer_id
-- Joining num_ins and sum_prin
join sum_prin 
on num_ins.customer_id= sum_prin.customer_id
-- Joining num_ins and num_unpaid_order
join num_unpaid_order
on num_ins.customer_id= num_unpaid_order.customer_id
-- Joining num_ins and avg_unpaid_order
join avg_unpaid_order
on num_ins.customer_id=avg_unpaid_order.customer_id
-- Joining num_ins and tot_amt_due
join tot_amt_due
on num_ins.customer_id=tot_amt_due.customer_id
-- Joining num_ins and tot_num_ins_due
join tot_num_ins_due
on num_ins.customer_id=tot_num_ins_due.customer_id
-- Joining num_ins and tot_num_ins_before_due
join tot_num_ins_before_due
on num_ins.customer_id=tot_num_ins_before_due.customer_id
-- Joining num_ins and tot_num_ins_aftr_due
join tot_num_ins_aftr_due
on num_ins.customer_id=tot_num_ins_aftr_due.customer_id
-- Joining num_ins and avg_repay_time_hist
left join avg_repay_time_hist
on num_ins.customer_id=avg_repay_time_hist.customer_id
-- joining num_ins and debt_to_ordr
join debt_to_ordr
on num_ins.customer_id=debt_to_ordr.customer_id
-- joining num_ins and order_hist
left join order_hist
on num_ins.customer_id=order_hist.customer_id
-- joining num_ins and payment_cards
left join payment_cards
on num_ins.customer_id=payment_cards.customer_id
-- joining num_ins and cust_demo
join cust_demo
on num_ins.customer_id=cust_demo.customer_id
-- joining num_ins and cust_dev
join cust_dev 
on num_ins.customer_id=cust_dev.customer_id
-- Joining num_ins and merchant_det
join merchant_det
on num_ins.customer_id=merchant_det.customer_id)
















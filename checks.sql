-- name: stale_series
-- Reporter whose latest month is earlier than the latest month in the table.
SELECT reporter_code, reporter_name,
       MAX(period) AS period,
       (SELECT MAX(period) FROM trade_flows) AS overall_latest
FROM trade_flows
GROUP BY reporter_code, reporter_name
HAVING MAX(period) < (SELECT MAX(period) FROM trade_flows);

-- name: missing_months
-- Gap between two reported months.
SELECT reporter_code, reporter_name, period,
       last_period_before_gap,
       month_index - prev_index - 1 AS months_missing
FROM (
    SELECT reporter_code, reporter_name, period, month_index,
           LAG(month_index) OVER (PARTITION BY reporter_code ORDER BY month_index) AS prev_index,
           LAG(period)      OVER (PARTITION BY reporter_code ORDER BY month_index) AS last_period_before_gap
    FROM (
        SELECT reporter_code, reporter_name, period,
               (period / 100) * 12 + (period - (period / 100) * 100) AS month_index
        FROM trade_flows
    ) AS m
) AS l
WHERE prev_index IS NOT NULL AND month_index - prev_index > 1;

-- name: bad_values
-- Missing, zero or negative weight or value.
SELECT reporter_code, reporter_name, period, net_wgt_kg, value_usd, weight_source
FROM trade_flows
WHERE net_wgt_kg IS NULL OR net_wgt_kg <= 0
   OR value_usd  IS NULL OR value_usd  <= 0;

-- name: vs_trailing_avg
-- Weight more than 50% away from the average of the previous 6 months.
SELECT reporter_code, reporter_name, period, net_wgt_kg, trailing_avg_kg,
       100.0 * (net_wgt_kg - trailing_avg_kg) / trailing_avg_kg AS pct_vs_avg
FROM (
    SELECT reporter_code, reporter_name, period, net_wgt_kg,
           AVG(net_wgt_kg) OVER (PARTITION BY reporter_code ORDER BY period
               ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING) AS trailing_avg_kg,
           COUNT(net_wgt_kg) OVER (PARTITION BY reporter_code ORDER BY period
               ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING) AS months_of_history
    FROM trade_flows
) AS t
WHERE months_of_history >= 3
  AND ABS(net_wgt_kg - trailing_avg_kg) / trailing_avg_kg > 0.50;

-- name: unit_value_outlier
-- USD per tonne outside 1,000-8,000, or more than 35% from its trailing 6-month average.
-- Out-of-bounds values are left out of the baseline so one gross error cannot distort later months.
SELECT reporter_code, reporter_name, period, usd_per_tonne, trailing_avg_usd_per_tonne
FROM (
    SELECT reporter_code, reporter_name, period, usd_per_tonne,
           AVG(CASE WHEN usd_per_tonne BETWEEN 1000 AND 8000 THEN usd_per_tonne END)
               OVER (PARTITION BY reporter_code ORDER BY period
                     ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING) AS trailing_avg_usd_per_tonne,
           COUNT(CASE WHEN usd_per_tonne BETWEEN 1000 AND 8000 THEN usd_per_tonne END)
               OVER (PARTITION BY reporter_code ORDER BY period
                     ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING) AS months_of_history
    FROM (
        SELECT reporter_code, reporter_name, period,
               value_usd / (net_wgt_kg / 1000.0) AS usd_per_tonne
        FROM trade_flows
        WHERE net_wgt_kg > 0 AND value_usd > 0
    ) AS u
) AS t
WHERE usd_per_tonne NOT BETWEEN 1000 AND 8000
   OR (months_of_history >= 3
       AND ABS(usd_per_tonne - trailing_avg_usd_per_tonne) / trailing_avg_usd_per_tonne > 0.35);
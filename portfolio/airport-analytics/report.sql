-- On-time means departure delay < 15 minutes; cancellations are excluded
-- from the on-time denominator and mean delay, but included in total flights.
SELECT origin,
       COUNT(*) AS total_flights,
       SUM(cancelled) AS cancelled_flights,
       ROUND(100.0 * SUM(cancelled) / COUNT(*), 2) AS cancellation_pct,
       ROUND(AVG(CASE WHEN cancelled = 0 THEN delay_minutes END), 2) AS mean_delay_minutes,
       ROUND(100.0 * SUM(CASE WHEN cancelled = 0 AND delay_minutes < 15 THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN cancelled = 0 THEN 1 ELSE 0 END), 0), 2) AS on_time_pct
FROM flights
GROUP BY origin
ORDER BY total_flights DESC, origin;

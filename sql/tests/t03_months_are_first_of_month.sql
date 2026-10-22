-- Attendu : 0 ligne. Les périodes mensuelles sont converties au premier jour du mois.
SELECT DISTINCT month_start
FROM `{project}.{silver}.fact_indicator_monthly`
WHERE EXTRACT(DAY FROM month_start) != 1;

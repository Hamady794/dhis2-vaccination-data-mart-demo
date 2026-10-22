-- Attendu : 0 ligne. Le grain (indicateur, district, mois) doit être unique.
SELECT indicator_id, org_unit_id, month_start, COUNT(*) AS n
FROM `{project}.{silver}.fact_indicator_monthly`
GROUP BY indicator_id, org_unit_id, month_start
HAVING COUNT(*) > 1;

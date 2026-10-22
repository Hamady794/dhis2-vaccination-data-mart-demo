-- Attendu : 0 ligne. Le serveur de démo de Sierra Leone compte 13 districts (niveau 2).
SELECT COUNT(DISTINCT org_unit_id) AS n_districts
FROM `{project}.{silver}.fact_indicator_monthly`
HAVING COUNT(DISTINCT org_unit_id) != 13;

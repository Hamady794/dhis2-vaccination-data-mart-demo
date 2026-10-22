-- Attendu : 0 ligne. Chaque unité d'organisation de la table de faits existe dans la dimension.
SELECT DISTINCT org_unit_id
FROM `{project}.{silver}.fact_indicator_monthly`
WHERE org_unit_name IS NULL;

-- Attendu : 0 ligne. Les indicateurs non exploitables ne doivent pas être dans la table de faits.
SELECT DISTINCT f.indicator_id
FROM `{project}.{silver}.fact_indicator_monthly` AS f
JOIN `{project}.{silver}.dim_indicator` AS d USING (indicator_id)
WHERE NOT d.is_usable;

-- Attendu : 0 ligne. Une couverture > 200 % indiquerait un problème de définition, pas un simple écart de population.
SELECT indicator_name, org_unit_name, month_start, value
FROM `{project}.{silver}.fact_indicator_monthly`
WHERE indicator_group = 'coverage' AND value > 200;

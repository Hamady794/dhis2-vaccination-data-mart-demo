-- Gold : couvertures vaccinales par district et par mois (pour le tableau de bord)
-- value_display plafonne à 100 pour l'affichage ; la valeur brute reste dans value.
CREATE OR REPLACE TABLE `{project}.{gold}.gold_coverage_by_district_month` AS
SELECT
  org_unit_id,
  org_unit_name AS district,
  month_start,
  indicator_id,
  indicator_name,
  value,
  LEAST(value, 100) AS value_display,
  dq_flag
FROM `{project}.{silver}.fact_indicator_monthly`
WHERE indicator_group = 'coverage'
  AND dq_flag IN ('OK', 'COVERAGE_OVER_100');

-- Gold : synthèse par district et indicateur sur la période extraite
-- Moyenne simple des valeurs mensuelles (pas une moyenne pondérée par la population).
-- Les valeurs négatives (stocks, abandons) sont exclues du calcul : voir gold_data_quality_summary.
CREATE OR REPLACE TABLE `{project}.{gold}.gold_district_summary` AS
SELECT
  org_unit_id,
  org_unit_name AS district,
  indicator_id,
  indicator_name,
  indicator_group,
  COUNT(*)                                   AS months_reported,
  MAX(month_start)                           AS latest_month,
  ARRAY_AGG(value ORDER BY month_start DESC)[OFFSET(0)] AS latest_value,
  ROUND(AVG(value), 2)                       AS avg_value,
  MIN(value)                                 AS min_value,
  MAX(value)                                 AS max_value
FROM `{project}.{silver}.fact_indicator_monthly`
WHERE dq_flag IN ('OK', 'COVERAGE_OVER_100')
GROUP BY org_unit_id, district, indicator_id, indicator_name, indicator_group;

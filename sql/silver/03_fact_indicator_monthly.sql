-- Silver : une ligne par indicateur x district x mois, avec drapeau de qualité (dq_flag)
-- Grain : (indicator_id, org_unit_id, month_start)
CREATE OR REPLACE TABLE `{project}.{silver}.fact_indicator_monthly` AS
WITH base AS (
  SELECT
    a.indicator_id,
    i.indicator_name,
    i.indicator_group,
    i.unit,
    a.org_unit_id,
    o.org_unit_name,
    o.org_unit_type,
    PARSE_DATE('%Y%m%d', CONCAT(a.period, '01')) AS month_start,
    a.value,
    a.extracted_at
  FROM `{project}.{bronze}.bronze_analytics` AS a
  JOIN `{project}.{silver}.dim_indicator` AS i
    ON i.indicator_id = a.indicator_id AND i.is_usable
  LEFT JOIN `{project}.{silver}.dim_org_unit` AS o
    ON o.org_unit_id = a.org_unit_id
)
SELECT
  *,
  CASE
    WHEN value IS NULL THEN 'MISSING'
    WHEN indicator_group = 'stock'    AND value < 0   THEN 'NEGATIVE_STOCK'
    WHEN indicator_group = 'dropout'  AND value < 0   THEN 'NEGATIVE_DROPOUT'
    WHEN indicator_group = 'coverage' AND value < 0   THEN 'NEGATIVE_COVERAGE'
    WHEN indicator_group = 'coverage' AND value > 100 THEN 'COVERAGE_OVER_100'
    ELSE 'OK'
  END AS dq_flag
FROM base;

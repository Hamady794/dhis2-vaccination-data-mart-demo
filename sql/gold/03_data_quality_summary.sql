-- Gold : qualité des données par indicateur (anomalies + complétude)
-- expected_rows = nombre de districts x nombre de mois présents dans la table
CREATE OR REPLACE TABLE `{project}.{gold}.gold_data_quality_summary` AS
WITH grid AS (
  SELECT
    COUNT(DISTINCT org_unit_id)  AS n_districts,
    COUNT(DISTINCT month_start)  AS n_months
  FROM `{project}.{silver}.fact_indicator_monthly`
),
per_indicator AS (
  SELECT
    indicator_id,
    indicator_name,
    indicator_group,
    COUNT(*) AS rows_returned,
    COUNTIF(dq_flag = 'OK') AS rows_ok,
    COUNTIF(dq_flag = 'COVERAGE_OVER_100') AS rows_coverage_over_100,
    COUNTIF(dq_flag = 'NEGATIVE_STOCK') AS rows_negative_stock,
    COUNTIF(dq_flag = 'NEGATIVE_DROPOUT') AS rows_negative_dropout,
    COUNTIF(dq_flag = 'NEGATIVE_COVERAGE') AS rows_negative_coverage,
    COUNTIF(dq_flag = 'MISSING') AS rows_missing_value
  FROM `{project}.{silver}.fact_indicator_monthly`
  GROUP BY indicator_id, indicator_name, indicator_group
)
SELECT
  p.*,
  g.n_districts * g.n_months AS expected_rows,
  ROUND(100 * p.rows_returned / (g.n_districts * g.n_months), 1) AS completeness_pct,
  ROUND(100 * (p.rows_returned - p.rows_ok) / p.rows_returned, 1) AS anomaly_pct
FROM per_indicator AS p
CROSS JOIN grid AS g;

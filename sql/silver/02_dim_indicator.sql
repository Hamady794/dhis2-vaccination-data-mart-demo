-- Silver : dimension des indicateurs, avec leur définition DHIS2
-- is_usable = FALSE pour "FIC <1y - Adjusted for reporting" : la définition
-- utilise #{..REPORTING_RATE} au lieu de R{..REPORTING_RATE}, donc la valeur est 0 partout.
CREATE OR REPLACE TABLE `{project}.{silver}.dim_indicator` AS
SELECT
  indicator_id,
  name AS indicator_name,
  CASE
    WHEN name LIKE '%Stock%'  THEN 'stock'
    WHEN name LIKE 'Dropout%' THEN 'dropout'
    ELSE 'coverage'
  END AS indicator_group,
  IF(indicator_type = 'Per cent', 'percent', 'count') AS unit,
  numerator,
  denominator,
  annualized,
  indicator_id != 'IT8EAeFRAat' AS is_usable,
  IF(indicator_id = 'IT8EAeFRAat',
     'Definition error: REPORTING_RATE referenced as a data element, returns 0 everywhere',
     NULL) AS usability_note
FROM `{project}.{bronze}.bronze_indicator_definitions`;

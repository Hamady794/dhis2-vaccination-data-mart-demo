-- Silver : dimension des unités d'organisation (1 ligne par unité)
CREATE OR REPLACE TABLE `{project}.{silver}.dim_org_unit` AS
SELECT
  o.org_unit_id,
  o.name  AS org_unit_name,
  o.level AS org_unit_level,
  CASE o.level
    WHEN 1 THEN 'country'
    WHEN 2 THEN 'district'
    WHEN 3 THEN 'chiefdom'
    WHEN 4 THEN 'facility'
    ELSE 'other'
  END AS org_unit_type,
  o.parent_id,
  p.name AS parent_name,
  o.path
FROM `{project}.{bronze}.bronze_org_units` AS o
LEFT JOIN `{project}.{bronze}.bronze_org_units` AS p
  ON p.org_unit_id = o.parent_id;

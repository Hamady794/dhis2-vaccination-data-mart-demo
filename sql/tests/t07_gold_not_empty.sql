-- Attendu : 0 ligne. Les tables Gold ne doivent pas être vides.
SELECT 'gold_coverage_by_district_month' AS table_name FROM (SELECT COUNT(*) AS n FROM `{project}.{gold}.gold_coverage_by_district_month`) WHERE n = 0
UNION ALL
SELECT 'gold_district_summary' FROM (SELECT COUNT(*) AS n FROM `{project}.{gold}.gold_district_summary`) WHERE n = 0
UNION ALL
SELECT 'gold_data_quality_summary' FROM (SELECT COUNT(*) AS n FROM `{project}.{gold}.gold_data_quality_summary`) WHERE n = 0;

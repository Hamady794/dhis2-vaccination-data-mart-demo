# Tableau de bord Looker Studio

## Connexion

1. Ouvrir Looker Studio, créer une source de données **BigQuery**.
2. Choisir le projet, puis le dataset `vaccination_gold`.
3. Ajouter les trois tables comme sources distinctes :
   `gold_coverage_by_district_month`, `gold_district_summary`, `gold_data_quality_summary`.

## Page 1 : Couverture vaccinale par district

- Filtre : `indicator_name` (liste déroulante, défaut « Penta 3 Coverage <1y »), plage de dates sur `month_start`.
- Tableau avec mise en forme conditionnelle : `district`, `latest_value`, `avg_value` (source `gold_district_summary`, filtrée sur `indicator_group = coverage`).
- Graphique en barres : `avg_value` par `district`.
- Courbe : `value_display` par `month_start`, une ligne par district (source `gold_coverage_by_district_month`).

## Page 2 : Cascade vaccinale

- Barres groupées par `district` pour BCG, Penta 1, Penta 2, Penta 3, OPV 3 et rougeole (`avg_value`).
- Indicateurs d'abandon : tableau `Dropout rate Penta 1 - 3` et `Dropout rate Penta 1 - Measles` par district.

## Page 3 : Qualité des données

- Tableau `gold_data_quality_summary` : `completeness_pct`, `anomaly_pct`, et les colonnes `rows_negative_*`.
- Une note de bas de page : source (DHIS2 démo, 2.44-SNAPSHOT, 2026-10-22) et limites (moyennes simples, données fictives).

## Publication

Partager le rapport en lecture seule (« toute personne disposant du lien »), tester le lien en navigation privée, puis le coller dans le README du dépôt.

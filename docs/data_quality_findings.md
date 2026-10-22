# Constats de qualité des données

Extraction : serveur DHIS2 2.44-SNAPSHOT (révision `61377d1`), 2026-10-22. Périmètre : 13 districts, 12 mois (202510 à 202609), 16 indicateurs exploitables, 2 325 lignes.

## Tableau récapitulatif

| Constat | Lignes | Indicateurs concernés | Traitement |
|---|---|---|---|
| Stock négatif | 43 | BCG Stock PHU (15), Measles Stock End Balance (14), OPV Stock PHU (14) | `dq_flag = NEGATIVE_STOCK`, valeur conservée, exclue de Gold |
| Taux d'abandon négatif | 17 | Penta 1-3 (8), Penta 1-rougeole (9) | `NEGATIVE_DROPOUT`, valeur conservée, exclue de Gold |
| Couverture > 100 % | 9 | BCG (7), OPV 0 (2) | `COVERAGE_OVER_100`, conservée dans Gold, affichage plafonné à 100 (`value_display`) |
| Indicateur toujours à 0 | 156 | FIC <1y - Adjusted for reporting | Exclu de Silver (`is_usable = FALSE`) |
| Complétude | 145 sur 156 attendues (92,9 %) ; 143 pour les stocks (91,7 %) | Tous | Mesurée dans `gold_data_quality_summary` |

## Explications, d'après les définitions DHIS2 (`indicator_definitions.csv`)

**Taux d'abandon négatifs.** Penta 1-3 est défini par (Penta 1 − Penta 3) / Penta 1. Il devient négatif quand le nombre de doses de Penta 3 dépasse celui de Penta 1 dans le mois, ce qui est une incohérence de saisie ou de calendrier (doses de rattrapage, enfants vaccinés hors zone). Même logique pour Penta 1-rougeole.

**Stocks négatifs.** Les indicateurs de stock sont calculés par une formule à quatre éléments de données (stock initial + reçu − utilisé − perdu). Un résultat négatif signifie que les quatre valeurs saisies ne sont pas cohérentes entre elles, pas qu'un stock réel est négatif.

**Couvertures > 100 %.** Le dénominateur est une estimation de population cible. Une couverture supérieure à 100 % indique en général une population sous-estimée ou des enfants vaccinés hors de leur zone de résidence. Les valeurs maximales observées (112 % pour le BCG, 105,8 % pour l'OPV 0) restent modérées.

**FIC <1y - Adjusted for reporting.** La définition du numérateur est `(#{UOlfIjgN8X6.…}+#{UOlfIjgN8X6.…})*(#{BfMAe6Itzgt.REPORTING_RATE}/100)`. Dans la définition équivalente du BCG ajusté, le taux de rapportage est écrit `R{BfMAe6Itzgt.REPORTING_RATE}`. La version du FIC utilise la syntaxe `#{…}` des éléments de données au lieu de `R{…}` des taux de rapportage, ce qui est cohérent avec une valeur de 0 sur les 156 lignes. C'est une hypothèse déduite des définitions, à confirmer sur le serveur. Le test `test_known_issue_fic_adjusted_is_always_zero` signalera si le serveur corrige l'indicateur.

**Valeurs de couverture Penta 3 basses.** Les valeurs mensuelles vont de 4,2 % à 74,9 % selon le district (moyenne nationale simple de 19,7 % à 33,8 % selon le mois). L'indicateur est annualisé (`annualized = TRUE`, facteur 100), et le dénominateur est une population cible annuelle. La cause exacte de ces niveaux n'a pas été déterminée : l'hypothèse la plus plausible est que les données de démonstration sont partielles ou générées. Western Area (zone urbaine) ressort nettement au-dessus des autres districts dans ces données de démonstration.

## Ce que le projet fait de ces constats

1. Aucune valeur n'est corrigée ni supprimée en Silver, sauf l'indicateur inexploitable.
2. Chaque ligne porte un `dq_flag`.
3. Gold exclut les valeurs aberrantes des synthèses (`gold_district_summary`) et expose les décomptes dans `gold_data_quality_summary`.
4. Les tests (SQL et pytest) vérifient le grain, les clés, les périodes, le nombre de districts et l'absence de valeurs extrêmes.

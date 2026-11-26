<p align="center">
  <img src="assets/logo-mark.svg" width="96" height="96"
       alt="Logo du projet : une jauge dont l aiguille s arrête à 61,9 sur 100">
</p>

# Maturité digitale des entreprises françaises (INSEE 2023)

Ce projet sert à **mesurer à quel point les entreprises françaises utilisent le cloud, l'intelligence artificielle et l'analyse de données**, secteur par secteur et selon leur taille, à partir de statistiques publiques de l'INSEE.

---

## À quoi ça sert

L'**INSEE** (l'Institut national de la statistique et des études économiques) interroge les entreprises sur leur usage du numérique. Cette enquête s'appelle **TIC** (Technologies de l'information et de la communication) ; ce projet en utilise l'édition 2023, dont les fichiers portent le nom `irecotic23`.

Les résultats publiés sont des tableaux de chiffres bruts, du type « sur 2 796 entreprises de l'immobilier, 196 utilisent l'IA ». Difficile d'en tirer une vue d'ensemble.

Ce projet transforme ces tableaux en **un score sur 100 par secteur et par taille d'entreprise**, puis les affiche dans un tableau de bord. On peut ainsi répondre à des questions comme :

- Quels secteurs sont les plus avancés dans le numérique ?
- Les petites entreprises sont-elles en retard par rapport aux grandes ?
- Sur quel pilier (cloud, IA, données) le retard est-il le plus fort ?

Trois technologies sont prises en compte :

- le **cloud** : utiliser des logiciels ou du stockage hébergés sur Internet plutôt que sur ses propres ordinateurs ;
- l'**intelligence artificielle (IA)** : des programmes capables de réaliser des tâches comme reconnaître du texte, de la parole ou des images ;
- l'**analyse de données** (souvent appelée *Big Data*) : exploiter les données de l'entreprise pour prendre des décisions.

---

## Comment ça marche

Le projet suit une chaîne de traitement en quatre étapes. On parle d'**ETL** (*Extract, Transform, Load*, « extraire, transformer, charger ») : récupérer des données, les mettre en forme, puis les ranger là où on va les utiliser.

1. **Récupération** — un script télécharge l'archive officielle de l'enquête sur le site de l'INSEE et en extrait trois tableaux : usage des données, usage du cloud, usage de l'IA.
2. **Rangement** — un deuxième script range ces tableaux dans une **base de données SQLite** : une base de données contenue dans un simple fichier, sans serveur à installer. Les noms de colonnes sont harmonisés (minuscules, sans espaces).
3. **Calcul du score** — un troisième script utilise le **SQL** (le langage standard pour interroger une base de données) pour croiser les trois tableaux et calculer, pour chaque couple « secteur × taille », un score sur 100 :
   - **Cloud** : part des entreprises qui achètent des services cloud, ramenée sur **30 points** ;
   - **IA** : part des entreprises qui utilisent au moins une technologie d'IA, ramenée sur **40 points** ;
   - **Données** : part des entreprises qui analysent des données en interne, ramenée sur **30 points**.

   Exemple : si 50 % des entreprises d'un secteur utilisent le cloud, ce secteur obtient 15 points sur 30 pour le cloud.
4. **Visualisation** — le résultat est affiché dans un tableau de bord **Power BI** (le logiciel de Microsoft pour créer des graphiques interactifs).

Ces pondérations (30 / 40 / 30) sont un choix du projet, pas une norme de l'INSEE.

> **L'échelle n'est pas parcourue de 0 à 100.** Atteindre 100 supposerait que *toutes* les entreprises d'une ligne utilisent les trois technologies. Dans les faits, les scores observés vont de **6,6 à 61,9** : l'IA pèse 40 points pour seulement 5,9 % d'adoption nationale, ce qui plafonne mécaniquement l'ensemble. Le score sert donc à **comparer des lignes entre elles**, pas à dire si un secteur est « bon » — « 61,9 / 100 » est le maximum observé, pas un milieu de tableau.

---

## Résultat / ce qu'on obtient

- Un tableau de **65 lignes** (13 modalités de secteur × 5 catégories de taille) avec, pour chacune : le nombre d'entreprises, les trois sous-scores, la part d'entreprises équipées d'un ERP (logiciel de gestion intégré qui centralise comptabilité, stocks, achats…), le **score global sur 100**, un indicateur `secret_statistique` (`1` si le score n'est pas calculable) et deux indicateurs de structure, `est_agregat` et `est_sous_ensemble`, **à lire impérativement avant toute addition ou moyenne** (voir ci-dessous).
- Ce tableau est disponible dans `data/processed/entreprise_score_final.csv`, versionné dans le dépôt, et dans la table `entreprise_score` de la base SQLite. La base, elle, **n'est pas versionnée** : elle est reconstruite par le pipeline (voir « Pourquoi la base SQLite n'est pas dans le dépôt »).

Quelques valeurs tirées de ce fichier :

| Secteur | Taille | Score global |
|---|---|---|
| Activités spécialisées, scientifiques et techniques | 250 personnes ou plus | 61,9 / 100 (le plus élevé) |
| Ensemble des secteurs | Ensemble des tailles | 18,99 / 100 |

### ⚠️ Les 65 lignes ne sont pas 65 observations

C'est le piège principal de ces données, et il est facile de s'y perdre : **certaines lignes sont des totaux d'autres lignes.** Les additionner revient à compter deux fois les mêmes entreprises.

Les 13 modalités de secteur se décomposent en :

| Nature | Nombre | Détail |
|---|---|---|
| Secteurs réellement disjoints | **11** | industrie, construction, commerce de gros, commerce de détail, transports, hébergement-restauration, information-communication, immobilier, activités spécialisées, services administratifs, énergie-eau-déchets |
| Total | 1 | `Ens` (« Ensemble ») = la somme des 11 |
| **Sous-ensemble** | 1 | `S_TIC`, libellé par l'INSEE « **dont** secteur producteur de TIC » : ses 7 501 entreprises sont **déjà comptées** dans l'industrie et dans l'information-communication |

Et les 5 tailles sont 4 tranches réelles (`po1` à `po4`) plus leur total `Ens`. Pour chaque secteur, la ligne `Ens` est bien la somme de ses `po1..po4` (vérifié ligne à ligne).

Au total, **17 des 65 lignes sont des agrégats** et 5 concernent le sous-ensemble `S_TIC`. Il ne reste que **44 cellules disjointes** (11 secteurs × 4 tailles). La différence n'est pas théorique :

```
somme de total_entreprises sur les 65 lignes        : 704 384
somme sur les 44 cellules disjointes                : 172 348
population réelle (ligne Ens / Ens)                 : 172 345   (écart de 3 : arrondi aléatoire INSEE)
```

D'où les deux colonnes `est_agregat` et `est_sous_ensemble` : **filtrer sur `est_agregat = 0` et `est_sous_ensemble = 0`** avant toute somme, moyenne ou comptage. Les lignes agrégées restent dans le tableau parce qu'elles sont utiles telles quelles — la ligne `Ens`/`Ens` est le chiffre France — mais elles ne doivent jamais entrer dans un calcul avec les autres.

Deuxième précaution, indépendante de la première : **les sous-scores sont des taux, pas des effectifs.** Additionner `score_cloud` sur plusieurs lignes additionne des pourcentages calculés sur des populations différentes ; le résultat ne veut rien dire, même en écartant les agrégats. Pour agréger correctement, il faut repartir des effectifs bruts des tables `insee_*`.

> Secret statistique : certaines cases de l'INSEE sont masquées (valeur `s`) quand l'effectif est trop faible pour être publié. Elles sont chargées comme **valeurs nulles**, jamais comme des 0. Pour 4 lignes sur 65 (énergie / eau-déchets `S_DE` et immobilier `S_L`, tailles `po2` et `po4`), l'indicateur IA est masqué : `score_ia` et `digital_maturity_score` y sont donc vides et la colonne `secret_statistique` vaut `1`. Mieux vaut une case vide qu'un score sous-estimé présenté comme une mesure.

- Un tableau de bord Power BI (`visualisation.pbix`, une page) avec :
  - un graphique en barres des performances Cloud, Data et IA par secteur d'activité ;
  - un graphique en barres empilées à 100 % par secteur ;
  - un filtre par taille d'entreprise.

### Lexique des codes de taille (INSEE)

D'après le dictionnaire des variables fourni (`data/reference/metadonnees_irecotic23.csv`) :

| Code | Signification |
|---|---|
| `Ens` | Ensemble (toutes tailles confondues) |
| `po1` | Moins de 20 personnes occupées |
| `po2` | De 20 à 49 personnes occupées |
| `po3` | De 50 à 249 personnes occupées |
| `po4` | 250 personnes occupées ou plus |

Les codes de secteur (`S_C`, `S_TIC`, `S_M`…) et leurs libellés officiels sont dans le même fichier (variable `ACT_IR`).

---

## Pour les développeurs

### Stack technique

| Rôle | Outil |
|---|---|
| Langage | Python **3.11** (seule version exécutée par la CI ; le code reste compatible avec les versions suivantes) |
| Téléchargement | `requests` |
| Manipulation de données | `pandas` |
| Base de données | SQLite (via `sqlite3`, inclus dans Python, et `SQLAlchemy`) |
| Exploration | Jupyter Notebook (dans `requirements-dev.txt`) |
| Visualisation | Power BI Desktop |

### Installation

```bash
pip install -r requirements.txt
```

`sqlite3` fait partie de la bibliothèque standard de Python : il ne s'installe pas avec `pip`.

Pour contribuer — passer le linter ou relancer le notebook — ajouter les outils de développement :

```bash
pip install -r requirements-dev.txt
```

### Exécution du pipeline

Depuis la racine du dépôt, dans l'ordre :

```bash
python src/01_ingestion.py            # Télécharge le ZIP INSEE et extrait les tables 3, 4 et 5 dans data/raw/
python src/02_load_to_sqlite.py       # Charge chaque CSV de data/raw/ dans data/processed/maturite_digitale.db
python src/03_sql_transformations.py  # Calcule les scores → table entreprise_score + entreprise_score_final.csv
```

Les chemins sont calculés à partir de l'emplacement des scripts : ils peuvent être lancés depuis n'importe quel dossier. Les journaux d'exécution sont ajoutés dans `logs/pipeline.log`, en UTF-8 (dossier créé automatiquement, non versionné ; le fichier est recréé au prochain lancement s'il est supprimé).

Les scripts affichent des icônes dans leurs messages, et **imposent eux-mêmes l'UTF-8 sur leur sortie** : aucune variable d'environnement n'est nécessaire. C'est indispensable dès que la sortie n'est pas une console Windows — redirection vers un fichier, tube, Git Bash, CI : Python retombe alors sur l'encodage de la locale (cp1252 sous Windows), où ces icônes n'existent pas, et le premier `print` levait `UnicodeEncodeError` avant que le script n'ait rien fait. `tests/verifie_pipeline.py` retire délibérément `PYTHONIOENCODING` de l'environnement des scripts qu'il lance, pour que ce défaut ne puisse pas revenir sans faire rougir la CI.

### Vérification

```bash
python tests/verifie_pipeline.py
```

Le script rejoue les étapes 02 et 03 sur une **copie** des données brutes (jamais sur les fichiers versionnés) et contrôle 31 invariants : aucune mesure chargée en texte, les 4 lignes sous secret statistique restent NULL et ne valent jamais 0, les 61 autres gardent un score complet, le score global égale la somme des trois sous-scores et reste dans `[0, 100]`, deux valeurs de référence, le classement qui renvoie les lignes non calculables en dernier, les trois tables brutes qui gardent leurs 65 lignes avec le même `nb_ent`, la cohérence des drapeaux `est_agregat` / `est_sous_ensemble` (une fois les agrégats écartés, les lignes restantes totalisent bien la population réelle), la concordance entre le `entreprise_score_final.csv` versionné et le rejeu (la base n'est plus confrontée : n'étant plus versionnée, elle est reconstruite à chaque fois et ne peut plus être en retard sur le code), et enfin le refus d'un marqueur INSEE inconnu : la dernière vérification remplace `s` par `nd` dans une copie, exige que le chargement **échoue** au lieu de produire un 0 silencieux, et vérifie qu'il n'a laissé derrière lui aucune table à moitié rechargée. C'est ce script que lance la CI.

Détail des étapes :

1. **`01_ingestion.py`** — télécharge `https://www.insee.fr/fr/statistiques/fichier/7729450/irecotic23_csv.zip` (délai maximal 20 s) et extrait les fichiers dont le nom contient `table3`, `table4` et `table5`, renommés en `insee_data.csv`, `insee_cloud.csv` et `insee_ia.csv`. Aucun nettoyage de valeurs n'est fait à cette étape.
2. **`02_load_to_sqlite.py`** — lit chaque CSV (séparateur `;`, UTF-8), convertit le marqueur INSEE de secret statistique `s` en valeur nulle sur toutes les colonnes de mesure (sans quoi la colonne serait chargée en texte et `CAST('s' AS FLOAT)` vaudrait silencieusement 0 dans SQLite), normalise les noms de colonnes (minuscules, espaces / apostrophes / tirets remplacés par `_`) et remplace la table du même nom dans SQLite.

   Trois garde-fous. Toute **autre** valeur non numérique — l'INSEE utilise aussi `nd`, `///`, `nr`, et un champ vide est tout aussi suspect — fait **échouer** le chargement avec le nom du fichier, de la colonne et des valeurs fautives, plutôt que de faire revenir le bug ci-dessus en silence. Les colonnes à trous, que `pandas` remonte en décimal, repassent en entier nullable pour ne pas afficher `172345.0` dans le dashboard. Enfin, **tous les fichiers sont lus et validés avant la moindre écriture**, et les trois tables sont remplacées dans une seule transaction : sans cela, un échec sur le troisième fichier laissait en base deux tables rechargées et une du millésime précédent, et l'étape 3 produisait ensuite un livrable plausible mais faux, en sortant avec un code de succès. La table calculée `entreprise_score` est supprimée au passage, puisqu'elle ne décrit plus les tables qu'on remplace.
3. **`03_sql_transformations.py`** — refuse de démarrer si la base est absente (sinon `sqlite3` en créerait une vide, et le script échouerait ensuite sur « no such table » en laissant derrière lui un `.db` qui ressemble à une base valide) **ou si l'une des trois tables brutes manque**, puis exécute une requête SQL avec trois CTE (`CloudMaturity`, `IAMaturity`, `DataMaturity`) jointes sur `act_ir` et `taille_ir` :

   | Indicateur | Colonne INSEE | Calcul |
   |---|---|---|
   | `score_cloud` | `cloud` | `cloud / nb_ent × 30` |
   | `score_ia` | `ia_tech` | `ia_tech / nb_ent × 40` |
   | `score_data` | `analyse_donnees_int` | `analyse_donnees_int / nb_ent × 30` |
   | `pct_erp_utilisation` | `pgi_erp` | `pgi_erp / nb_ent × 100` |
   | `digital_maturity_score` | — | somme des trois scores ; **nulle si une composante est masquée** |
   | `secret_statistique` | — | `1` si au moins une composante est masquée, sinon `0` |
   | `est_agregat` | — | `1` si `secteur = 'Ens'` ou `taille = 'Ens'` : la ligne est un total, pas une observation |
   | `est_sous_ensemble` | — | `1` si `secteur = 'S_TIC'` : secteur « dont », déjà compté dans les autres |

   Les lignes avec `nb_ent = 0` sont exclues. Le résultat est trié par score décroissant, les lignes non calculables étant renvoyées en fin de classement plutôt que confondues avec de faibles scores.

Le dépôt contient déjà les CSV bruts (`data/raw/`) et le CSV livrable (`data/processed/entreprise_score_final.csv`) : il n'est pas nécessaire de relancer le pipeline pour ouvrir le tableau de bord, qui lit ce CSV.

### Pourquoi la base SQLite n'est pas dans le dépôt

`data/processed/maturite_digitale.db` est dans `.gitignore`. Son contenu est **entièrement dérivé** de `data/raw/` et du code, et SQLite réagence ses pages à chaque reconstruction : le fichier changeait donc d'octets à contenu identique, et salissait l'arbre git après chaque exécution du pipeline. Pour l'obtenir, deux voies :

- lancer les étapes 02 et 03 ci-dessus, ce qui la crée en local ;
- ou la récupérer dans l'artefact `build-donnees` publié par la CI, qui la contient avec le CSV.

Le CSV, lui, **reste versionné** : il est le livrable lisible du projet, la source du tableau de bord, et le contrôle 10 du script de vérification garantit qu'il n'est jamais en retard sur le code.

### Intégration et livraison continues

Les workflows GitHub Actions n'embarquent aucune logique : ils appellent les workflows réutilisables de [`Ramcy-cloud/ci-templates`](https://github.com/Ramcy-cloud/ci-templates) en version `@v1`.

- **`.github/workflows/ci.yml`** — sur chaque pull request et chaque push sur `main` : installe `requirements.txt` et `requirements-dev.txt`, passe le linter (`ruff check .`, bloquant), **reconstruit la base SQLite** en rejouant 02 et 03 (elle n'est pas versionnée, et l'artefact ne peut pas publier un fichier absent), lance `tests/verifie_pipeline.py`, puis publie les données calculées comme artefact `build-donnees`. Cette reconstruction restaure ensuite le CSV versionné avec `git checkout`, car 03 le réécrit : sans cela le contrôle 10 comparerait le rejeu à un fichier tout juste régénéré et ne détecterait plus un CSV périmé. Un second job verrouille le flux de branches : une pull request vers `main` doit venir de `dev`, sinon la CI échoue.
- **`.github/workflows/cd.yml`** — livraison continue : déclenchée par une CI verte sur `main`, elle republie les artefacts en paquet `livraison-<sha>` via l'environnement GitHub `production`. Celui-ci exige une validation manuelle (`Actions` → exécution `CD` → `Review deployments` → `Approve`) : **rien n'est livré automatiquement**.

L'étape `01_ingestion.py` n'est pas rejouée en CI (elle téléchargerait l'archive INSEE) : les CSV bruts sont versionnés dans `data/raw/`.

### Tableau de bord

Ouvrir `visualisation.pbix` avec **Power BI Desktop** (Windows), puis **Actualiser** : le fichier embarque l'instantané de données de sa dernière sauvegarde, antérieure à la correction du secret statistique. Sans actualisation, il affiche encore un score IA de 0 sur les 4 lignes masquées. Si la source n'est pas trouvée à l'ouverture, la repointer vers `data/processed/entreprise_score_final.csv`.

Ce que contient le rapport, pour éviter les surprises :

- **Une page, trois visuels** : des barres groupées (agrégat **Somme**), des barres empilées à 100 % (agrégat **Moyenne**) et un segment sur la taille d'entreprise.
- **Le modèle a deux tables** : `entreprise_score_final`, alimentée par le CSV, et `Dictionnaire_Secteurs`, qui porte les libellés de secteur et **n'a pas de fichier source dans ce dépôt**. C'est le seul élément susceptible de faire échouer une actualisation, sans aucun lien avec le calcul du score.
- **Les libellés affichés ne sont pas ceux de l'INSEE** : la taille apparaît sous son code brut (`Ens`, `po1`…), et le code secteur `Ens` est affiché « Moyenne Nationale », un libellé maison. La correspondance officielle est dans `data/reference/metadonnees_irecotic23.csv`.
- **Les deux graphiques excluent « Moyenne Nationale »** par un filtre de visuel : on compte 13 secteurs dans le CSV, on en voit 12 à l'écran. Le segment est par ailleurs enregistré sur la seule valeur `Ens`.
- **Aucun visuel n'affiche `digital_maturity_score`**, ni `pct_erp_utilisation`, ni `secret_statistique` — seuls les trois sous-scores sont représentés, alors que le score global est ce que ce README met en avant.
- **Les deux graphiques agrègent sur des lignes non disjointes** (voir « Les 65 lignes ne sont pas 65 observations »). Les barres groupées additionnent la ligne `Ens` d'un secteur **avec** ses `po1..po4` : les hauteurs sont gonflées de 12 à 24 % selon le secteur. Les barres empilées font la moyenne d'un total avec ses propres composantes. Et comme ces colonnes sont des taux, la somme affichée en ordonnée n'a de toute façon pas de signification. **Correctif à appliquer dans Power BI** : ajouter un filtre de page `est_agregat = 0` et `est_sous_ensemble = 0` (les deux colonnes sont désormais dans le CSV), et remplacer l'agrégat Somme par une Moyenne — ou mieux, recalculer les taux depuis les effectifs bruts.

Effet de la correction sur les chiffres affichés. Les cellules masquées sont **vides** dans le CSV, donc lues comme nulles et non comme du texte : aucune erreur de type à l'actualisation. Sur les barres groupées (Somme), rien ne change, un zéro et un vide contribuant tous deux zéro. Sur les barres empilées à 100 %, à taille unique un vide donne exactement le même pourcentage qu'un zéro ; mais dès que plusieurs tailles sont sélectionnées, la **Moyenne** exclut les vides alors qu'elle intégrait les faux zéros :

| Secteur | Part IA avant | Part IA après |
|---|---|---|
| `S_DE` — énergie, eau, déchets | 3,4 % | **5,5 %** |
| `S_L` — activités immobilières | 5,6 % | **9,0 %** |

C'est l'effet recherché : la moyenne n'est plus tirée vers le bas par des zéros qui n'étaient pas des mesures. L'ordre des barres de ce visuel, trié sur la moyenne IA, change donc pour ces deux secteurs.

### Notebook

`notebooks/04_EDA_and_Insights.ipynb` contient l'**analyse exploratoire** (EDA, *Exploratory Data Analysis*) et répond aux trois questions posées en haut de ce README. Il est versionné **avec ses sorties**, donc lisible directement sur GitHub sans rien installer.

Il travaille sur la table de scores, pas sur les CSV bruts, et applique la précaution de méthode décrite plus haut : pour chaque question, il lit la ligne **déjà agrégée par l'INSEE au bon niveau** plutôt que de recombiner les cellules lui-même. Classement des secteurs sur les lignes `taille = 'Ens'`, comparaison des tailles sur les lignes `secteur = 'Ens'`. La racine du dépôt est trouvée automatiquement : il fonctionne quel que soit le dossier de travail du noyau.

Ses trois résultats :

| Constat | Chiffre |
|---|---|
| Secteur et taille pèsent **le même poids** — aucune des deux dimensions ne domine | amplitude de 35,6 points entre secteurs, 35,8 points entre tailles |
| L'**IA est le pilier le plus en retard**, et il est aussi le plus lourdement pondéré (40 points), ce qui écrase tous les scores | 5,9 % d'adoption, contre 26,8 % pour le cloud et 28,7 % pour les données |
| Ce retard **ne se rattrape pas avec la taille** | chez les 250 personnes et plus : IA 20,9 %, cloud 67,2 %, données 69,3 % |

Pour le relancer : `pip install -r requirements-dev.txt`, puis `jupyter lab notebooks/04_EDA_and_Insights.ipynb`. La **visualisation** n'est pas dans le notebook : c'est le rôle du tableau de bord Power BI.

### Structure du projet

```
projet-maturite-digitale/
├── .github/workflows/
│   ├── cd.yml                        # Livraison après validation manuelle
│   └── ci.yml                        # Vérification (appelle ci-templates@v1)
├── .gitattributes                    # Fins de ligne, et binaires déclarés (.pbix, .db)
├── .gitignore
├── data/
│   ├── raw/                          # CSV extraits de l'archive INSEE
│   │   ├── insee_data.csv            #   table 3 : usage et analyse des données
│   │   ├── insee_cloud.csv           #   table 4 : cloud
│   │   └── insee_ia.csv              #   table 5 : intelligence artificielle
│   ├── reference/
│   │   └── metadonnees_irecotic23.csv # Dictionnaire des variables et des codes INSEE
│   └── processed/                    # Entièrement régénérable par le pipeline
│       ├── maturite_digitale.db      # Base SQLite — NON versionnée (.gitignore)
│       └── entreprise_score_final.csv # Livrable versionné, source du tableau de bord
├── assets/                           # Logo du projet (voir assets/README.md)
│   ├── logo-mark.svg                 #   marque carrée : README, avatar, favicon
│   ├── logo.svg / logo-dark.svg      #   nom + marque, fond clair / fond sombre
│   └── logo-mark-512.png             #   rendu matriciel (Power BI, diapositives)
├── notebooks/
│   └── 04_EDA_and_Insights.ipynb
├── src/
│   ├── 01_ingestion.py               # Téléchargement et extraction
│   ├── 02_load_to_sqlite.py          # Chargement dans SQLite
│   └── 03_sql_transformations.py     # Calcul du score de maturité
├── tests/
│   └── verifie_pipeline.py           # Rejoue le pipeline et contrôle les invariants
├── requirements.txt                  # Dépendances du pipeline
├── requirements-dev.txt              # Linter et exécution du notebook
├── ruff.toml                         # Règles de lint, figées pour CI et local
├── visualisation.pbix                # Tableau de bord Power BI
├── LICENSE
└── README.md
```

### Source des données

INSEE, enquête TIC 2023 auprès des entreprises (fichiers `irecotic23`), archive téléchargée par `src/01_ingestion.py`.

## Licence

© 2026 Ramcy-cloud. Tous droits réservés.

Ce code est consultable publiquement mais n'est pas sous licence libre : aucun droit d'utilisation, de modification ou de redistribution n'est accordé.

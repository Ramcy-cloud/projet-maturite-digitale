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

---

## Résultat / ce qu'on obtient

- Un tableau de **65 lignes** (13 secteurs, dont « Ensemble », × 5 catégories de taille, dont « Ensemble ») avec, pour chacune : le nombre d'entreprises, les trois sous-scores, la part d'entreprises équipées d'un ERP (logiciel de gestion intégré qui centralise comptabilité, stocks, achats…), le **score global sur 100** et un indicateur `secret_statistique` (`1` si le score n'est pas calculable, voir plus bas).
- Ce tableau est disponible dans `data/processed/entreprise_score_final.csv` et dans la table `entreprise_score` de la base SQLite.

Quelques valeurs tirées de ce fichier :

| Secteur | Taille | Score global |
|---|---|---|
| Activités spécialisées, scientifiques et techniques | 250 personnes ou plus | 61,9 / 100 (le plus élevé) |
| Ensemble des secteurs | Ensemble des tailles | 18,99 / 100 |

> Secret statistique : certaines cases de l'INSEE sont masquées (valeur `s`) quand l'effectif est trop faible pour être publié. Elles sont chargées comme **valeurs nulles**, jamais comme des 0. Pour 4 lignes sur 65 (énergie / eau-déchets `S_DE` et immobilier `S_L`, tailles `po2` et `po4`), l'indicateur IA est masqué : `score_ia` et `digital_maturity_score` y sont donc vides et la colonne `secret_statistique` vaut `1`. Mieux vaut une case vide qu'un score sous-estimé présenté comme une mesure.

- Un tableau de bord Power BI (`visualisation.pbix`, une page) avec :
  - un graphique en barres des performances Cloud, Data et IA par secteur d'activité ;
  - un graphique en barres empilées à 100 % par secteur ;
  - un filtre par taille d'entreprise.

### Lexique des codes de taille (INSEE)

D'après le dictionnaire des variables fourni (`data/processed/metadonnees_irecotic23.csv`) :

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
| Langage | Python **3.12 ou plus récent** (voir ci-dessous) |
| Téléchargement | `requests` |
| Manipulation de données | `pandas` |
| Base de données | SQLite (via `sqlite3`, inclus dans Python, et `SQLAlchemy`) |
| Exploration | Jupyter Notebook |
| Visualisation | Power BI Desktop |

`src/02_load_to_sqlite.py` contient une barre oblique inverse dans une f-string, ce qui n'est accepté qu'à partir de Python 3.12.

### Installation

```bash
pip install -r requirements.txt
```

`sqlite3` fait partie de la bibliothèque standard de Python : il ne s'installe pas avec `pip`.

### Exécution du pipeline

Depuis la racine du dépôt, dans l'ordre :

```bash
python src/01_ingestion.py            # Télécharge le ZIP INSEE et extrait les tables 3, 4 et 5 dans data/raw/
python src/02_load_to_sqlite.py       # Charge chaque CSV de data/raw/ dans data/processed/maturite_digitale.db
python src/03_sql_transformations.py  # Calcule les scores → table entreprise_score + entreprise_score_final.csv
```

Les chemins sont calculés à partir de l'emplacement des scripts : ils peuvent être lancés depuis n'importe quel dossier. Les journaux d'exécution sont ajoutés dans `logs/pipeline.log` (dossier créé automatiquement, non versionné).

Sous Windows, les scripts affichent des emojis : si la console les refuse (`UnicodeEncodeError`), préfixer les commandes par `PYTHONIOENCODING=utf-8` (ou `$env:PYTHONIOENCODING = "utf-8"` sous PowerShell).

### Vérification

```bash
python tests/verifie_pipeline.py
```

Le script rejoue les étapes 02 et 03 sur une **copie** des données brutes (jamais sur les fichiers versionnés) et contrôle 15 invariants : aucune mesure chargée en texte, les 4 lignes sous secret statistique restent NULL et ne valent jamais 0, les 61 autres gardent un score complet, le score global égale la somme des trois sous-scores et reste dans `[0, 100]`, deux valeurs de référence, le classement qui renvoie les lignes non calculables en dernier, et la concordance entre `entreprise_score_final.csv` versionné et le rejeu. C'est ce script que lance la CI.

Détail des étapes :

1. **`01_ingestion.py`** — télécharge `https://www.insee.fr/fr/statistiques/fichier/7729450/irecotic23_csv.zip` (délai maximal 20 s) et extrait les fichiers dont le nom contient `table3`, `table4` et `table5`, renommés en `insee_data.csv`, `insee_cloud.csv` et `insee_ia.csv`. Aucun nettoyage de valeurs n'est fait à cette étape.
2. **`02_load_to_sqlite.py`** — lit chaque CSV (séparateur `;`, UTF-8), convertit le marqueur INSEE de secret statistique `s` en valeur nulle sur toutes les colonnes de mesure (sans quoi la colonne serait chargée en texte et `CAST('s' AS FLOAT)` vaudrait silencieusement 0 dans SQLite), normalise les noms de colonnes (minuscules, espaces / apostrophes / tirets remplacés par `_`) et remplace la table du même nom dans SQLite.
3. **`03_sql_transformations.py`** — requête SQL avec trois CTE (`CloudMaturity`, `IAMaturity`, `DataMaturity`) jointes sur `act_ir` et `taille_ir` :

   | Indicateur | Colonne INSEE | Calcul |
   |---|---|---|
   | `score_cloud` | `cloud` | `cloud / nb_ent × 30` |
   | `score_ia` | `ia_tech` | `ia_tech / nb_ent × 40` |
   | `score_data` | `analyse_donnees_int` | `analyse_donnees_int / nb_ent × 30` |
   | `pct_erp_utilisation` | `pgi_erp` | `pgi_erp / nb_ent × 100` |
   | `digital_maturity_score` | — | somme des trois scores ; **nulle si une composante est masquée** |
   | `secret_statistique` | — | `1` si au moins une composante est masquée, sinon `0` |

   Les lignes avec `nb_ent = 0` sont exclues. Le résultat est trié par score décroissant, les lignes non calculables étant renvoyées en fin de classement plutôt que confondues avec de faibles scores.

Le dépôt contient déjà les fichiers produits par ces trois étapes (`data/raw/` et `data/processed/`) : il n'est pas nécessaire de relancer le pipeline pour ouvrir le tableau de bord.

### Intégration et livraison continues

Les workflows GitHub Actions n'embarquent aucune logique : ils appellent les workflows réutilisables de [`Ramcy-cloud/ci-templates`](https://github.com/Ramcy-cloud/ci-templates) en version `@v1`.

- **`.github/workflows/ci.yml`** — sur chaque pull request et chaque push sur `main` : installe `requirements.txt`, lance `tests/verifie_pipeline.py`, puis publie les données calculées comme artefact `build-donnees`. Un second job vérifie le flux de branches : une pull request vers `main` doit venir de `dev`.
- **`.github/workflows/cd.yml`** — livraison continue : déclenchée par une CI verte sur `main`, elle republie les artefacts en paquet `livraison-<sha>` via l'environnement GitHub `production`. Celui-ci exige une validation manuelle (`Actions` → exécution `CD` → `Review deployments` → `Approve`) : **rien n'est livré automatiquement**.

L'étape `01_ingestion.py` n'est pas rejouée en CI (elle téléchargerait l'archive INSEE) : les CSV bruts sont versionnés dans `data/raw/`.

### Tableau de bord

Ouvrir `visualisation.pbix` avec **Power BI Desktop** (Windows). Les visuels s'appuient sur une table nommée `entreprise_score_final`, avec des colonnes renommées (« Performance Cloud », « Performance Data », « Performance IA », « Secteur d'activité », « Taille de l'Entreprise ») ; les libellés officiels viennent du dictionnaire `metadonnees_irecotic23.csv`. Si la source de données n'est pas trouvée à l'ouverture, il faut la repointer vers le fichier local.

### Notebook

`notebooks/04_EDA_and_Insights.ipynb` charge les trois CSV bruts avec `pandas` et affiche leurs premières lignes. L'analyse exploratoire (EDA, *Exploratory Data Analysis*) n'y est pas encore développée.

### Structure du projet

```
projet-maturite-digitale/
├── .github/workflows/
│   ├── ci.yml                        # Vérification (appelle ci-templates@v1)
│   └── cd.yml                        # Livraison après validation manuelle
├── data/
│   ├── raw/                          # CSV extraits de l'archive INSEE
│   │   ├── insee_data.csv            #   table 3 : usage et analyse des données
│   │   ├── insee_cloud.csv           #   table 4 : cloud
│   │   └── insee_ia.csv              #   table 5 : intelligence artificielle
│   └── processed/
│       ├── maturite_digitale.db      # Base SQLite (tables brutes + entreprise_score)
│       ├── entreprise_score_final.csv
│       └── metadonnees_irecotic23.csv # Dictionnaire des variables et des codes INSEE
├── notebooks/
│   └── 04_EDA_and_Insights.ipynb
├── src/
│   ├── 01_ingestion.py               # Téléchargement et extraction
│   ├── 02_load_to_sqlite.py          # Chargement dans SQLite
│   └── 03_sql_transformations.py     # Calcul du score de maturité
├── tests/
│   └── verifie_pipeline.py           # Rejoue le pipeline et contrôle les invariants
├── requirements.txt                  # Dépendances du pipeline
├── visualisation.pbix                # Tableau de bord Power BI
├── LICENSE
└── README.md
```

### Source des données

INSEE, enquête TIC 2023 auprès des entreprises (fichiers `irecotic23`), archive téléchargée par `src/01_ingestion.py`.

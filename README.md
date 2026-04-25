# 📊 Analyse de la Maturité Digitale des Entreprises (INSEE 2023)

## 📌 Présentation du Projet
Ce projet propose une étude complète de la maturité numérique des entreprises françaises, basée sur les données de l'enquête **i-Recotic 2023 de l'INSEE**. L'objectif est d'évaluer l'adoption de trois technologies piliers :
* **Intelligence Artificielle (IA)**
* **Cloud Computing**
* **Big Data**

Ce dépôt contient l'intégralité du pipeline de données (ETL), allant de l'ingestion des fichiers bruts jusqu'à la création d'un tableau de bord interactif d'aide à la décision.

## 🛠️ Stack Technique
* **Langage :** Python 3.x (Pandas)
* **Base de données :** SQLite
* **Visualisation :** Power BI
* **Gestion de version :** Git / GitHub

## 📁 Architecture du Projet

    projet-maturite-digitale/
    ├── data/
    │   ├── raw/                      # Fichiers bruts (insee_cloud.csv, insee_data.csv, insee_ia.csv)
    │   └── processed/                # Données nettoyées et base SQLite (maturite_digitale.db)
    ├── logs/                         # Fichiers de suivi (pipeline.log)
    ├── notebooks/                    # Exploration de données (04_EDA_and_Insights.ipynb)
    ├── src/                          # Scripts Python du pipeline ETL
    │   ├── 01_ingestion.py           # Nettoyage et normalisation des données brutes
    │   ├── 02_load_to_sqlite.py      # Chargement sécurisé en base de données
    │   └── 03_sql_transformations.py # Calcul des scores de maturité via requêtes SQL
    └── visualisation.pbix            # Dashboard Power BI interactif

## 🚀 Pipeline de Données (ETL)
Le projet suit une logique de traitement structurée :
1. **Extraction & Nettoyage (Ingestion) :** Les scripts Python traitent les fichiers CSV bruts de l'INSEE pour standardiser les formats et gérer les valeurs manquantes.
2. **Stockage Centralisé :** Les données propres sont chargées dans une base de données relationnelle locale (`maturite_digitale.db`).
3. **Modélisation (SQL) :** Des requêtes SQL sont utilisées pour croiser les données et calculer un **Score de Maturité Global** pondéré pour chaque secteur.
4. **Restitution (Power BI) :** Connexion de Power BI à la base de données, application d'un dictionnaire de métadonnées pour intégrer les libellés officiels, et création des visuels analytiques.

## 📊 Visualisation & Insights
Le tableau de bord permet une exploration dynamique des résultats :
* **Par Secteur d'activité :** Mise en évidence des secteurs leaders (ex: Information et Communication) et des opportunités d'accompagnement.
* **Par Taille d'entreprise :** Analyse de la fracture numérique entre les PME et les grandes structures.
* **Par Pilier Technologique :** Détail de la pénétration spécifique du Cloud, de l'IA et de la Data.

## 📖 Lexique des Données (Filtres INSEE)
Dans le tableau de bord, le filtre **"Taille de l'entreprise"** utilise la nomenclature officielle de l'INSEE. Voici la correspondance des codes utilisés :
* **Ens :** Ensemble (Moyenne nationale, toutes tailles confondues)
* **po1 :** 10 à 19 salariés
* **po2 :** 20 à 49 salariés
* **po3 :** 50 à 249 salariés
* **po4 :** 250 salariés ou plus

## ⚙️ Comment utiliser ce projet
1. Cloner le dépôt localement.
2. Installer les dépendances requises (`pip install pandas sqlite3`).
3. Exécuter les scripts du dossier `src/` dans l'ordre (01, 02 puis 03) pour générer la base de données à partir des fichiers bruts.
4. Ouvrir le fichier `visualisation.pbix` avec Power BI Desktop pour explorer le tableau de bord.
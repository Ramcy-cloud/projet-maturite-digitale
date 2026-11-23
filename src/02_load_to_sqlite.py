import logging
import os
import sys
from pathlib import PurePath

import pandas as pd
from sqlalchemy import create_engine, text

# Les messages de ce script contiennent des icônes. Quand sa sortie n'est pas
# une console Windows (redirection vers un fichier, tube, Git Bash, CI), Python
# retombe sur l'encodage de la locale — cp1252 sous Windows — où ces icônes
# n'existent pas, et le premier print levait UnicodeEncodeError : le script
# mourait avant d'avoir fait quoi que ce soit. Même cause que pour le journal
# ci-dessous, donc même correctif : on impose l'UTF-8 sur la sortie.
for flux in (sys.stdout, sys.stderr):
    if hasattr(flux, 'reconfigure'):
        flux.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

# Configuration des logs 
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'pipeline.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filemode='a',
    # Sans cela le journal est ecrit dans l'encodage de la locale (cp1252 sous
    # Windows) : un run local puis un run en CI produisent un fichier a
    # encodage mixte, impossible a relire d'un bloc.
    encoding='utf-8'
)
logger = logging.getLogger('LoadToSQLite')

# Marqueur INSEE du secret statistique : 's' veut dire "valeur non diffusee",
# jamais "zero". Sans na_values, la colonne arrive en TEXT dans SQLite et
# CAST('s' AS FLOAT) y vaut 0.0 silencieusement : les scores calcules en aval
# sont alors sous-estimes sans aucune erreur visible.
INSEE_SECRET = ['s']
# Colonnes d'etiquettes (texte legitime), a ne jamais filtrer.
LABEL_COLS = {'Taille_IR', 'ACT_IR'}
# Table calculee par 03 : elle doit disparaitre des que les tables brutes
# changent, sinon elle survit a un echec de chargement et fait croire que le
# livrable correspond aux donnees presentes.
TABLE_CALCULEE = 'entreprise_score'

# Préparation de l'URL de la base de données pour SQLAlchemy
os.makedirs(PROCESSED_DIR, exist_ok=True)
db_file_path = os.path.join(PROCESSED_DIR, 'maturite_digitale.db')
# SQLAlchemy attend des barres obliques, y compris sous Windows. On passe
# par PurePath plutot que par une f-string contenant une barre oblique
# inverse : celle-ci n'est acceptee qu'a partir de Python 3.12.
DB_URL = 'sqlite:///' + PurePath(db_file_path).as_posix()


def lit_et_valide(file_path, file):
    """Lit un CSV INSEE et refuse tout ce qui n'est pas une mesure numerique.

    Renvoie le DataFrame pret a ecrire et le nombre de cellules reellement
    masquees par le secret statistique.
    """
    # On neutralise le secret statistique colonne par colonne pour que 's'
    # devienne NULL et non 0, sans toucher aux etiquettes.
    header = pd.read_csv(file_path, sep=';', encoding='utf-8', nrows=0).columns
    mesures = [c for c in header if c.strip() not in LABEL_COLS]
    na_map = {c: INSEE_SECRET for c in mesures}

    # Premiere lecture en texte : elle seule permet de distinguer un marqueur
    # de secret statistique d'un champ vide ou d'une valeur aberrante.
    brut = pd.read_csv(file_path, sep=';', encoding='utf-8', dtype=str,
                       keep_default_na=False, na_values=[])
    nb_secret = 0
    for col in mesures:
        valeurs = brut[col].str.strip()
        nb_secret += int(valeurs.isin(INSEE_SECRET).sum())
        # Filet de securite : tout le reste doit etre un entier. Un autre
        # marqueur INSEE ('nd', '///', 'nr'...) ou un champ vide ferait revenir
        # le bug d'origine, colonne en TEXT et CAST a 0.0 ; mieux vaut un
        # chargement qui echoue qu'un score fausse en silence.
        suspectes = valeurs[~valeurs.isin(INSEE_SECRET)]
        inattendues = sorted(set(suspectes[pd.to_numeric(suspectes, errors='coerce').isna()]))
        if inattendues:
            raise ValueError(
                f"{file} / colonne {col} : valeurs non numeriques inattendues "
                f"{inattendues}. S'il s'agit d'un nouveau marqueur INSEE de "
                f"secret statistique, l'ajouter a INSEE_SECRET ; sinon corriger "
                f"la source."
            )

    df = pd.read_csv(file_path, sep=';', encoding='utf-8', na_values=na_map)

    # pandas remonte en float64 toute colonne a trous : on repasse en entier
    # nullable quand les valeurs sont entieres, pour ne pas afficher
    # "172345.0" dans le dashboard.
    for col in df.columns:
        serie = df[col]
        if pd.api.types.is_float_dtype(serie) and serie.dropna().mod(1).eq(0).all():
            df[col] = serie.astype('Int64')

    # Nettoyage des noms de colonnes (Minuscules, pas d'espaces)
    df.columns = df.columns.str.strip().str.lower()
    df.columns = df.columns.str.replace(' ', '_').str.replace("'", "_").str.replace("-", "_")
    return df, nb_secret


def load_data():
    logger.info("Début du chargement en base SQLite.")
    print("🗄️ Connexion à la base de données...")
    engine = create_engine(DB_URL)

    try:
        # Phase 1 : on lit et on valide TOUT avant d'ecrire quoi que ce soit.
        # Sans cela, un echec sur le 3e fichier laisse en base un melange de
        # tables rechargees et de tables du millesime precedent, et 03 produit
        # ensuite un livrable plausible mais faux, en sortant avec un code 0.
        a_ecrire = []
        for file in sorted(os.listdir(RAW_DIR)):
            if file.endswith('.csv'):
                table_name = file[:-len('.csv')]
                file_path = os.path.join(RAW_DIR, file)
                print(f"🔍 Lecture et contrôle de {file}...")
                logger.info(f"Lecture et contrôle de la table : {table_name}")
                df, nb_secret = lit_et_valide(file_path, file)
                a_ecrire.append((table_name, df, nb_secret))

        if not a_ecrire:
            raise FileNotFoundError(f"Aucun CSV à charger dans {RAW_DIR}.")

        # Phase 2 : ecriture, dans UNE seule transaction. Soit les trois tables
        # sont remplacees, soit aucune ne l'est : une base a moitie rechargee
        # ferait produire a 03 un livrable plausible mais faux.
        # La table calculee par 03 est supprimee au passage, puisqu'elle ne
        # decrit plus les tables brutes qu'on remplace.
        with engine.begin() as connexion:
            connexion.execute(text(f'DROP TABLE IF EXISTS "{TABLE_CALCULEE}"'))
            for table_name, df, nb_secret in a_ecrire:
                print(f"⏳ Chargement de {table_name}...")
                df.to_sql(table_name, con=connexion, if_exists='replace', index=False)
                print(f" Table '{table_name}' créée avec {len(df)} lignes "
                      f"({nb_secret} cellules sous secret statistique -> NULL).")
                logger.info(f"Table {table_name} créée avec {len(df)} lignes, "
                            f"{nb_secret} cellules sous secret statistique converties en NULL.")

        print(" Chargement terminé avec succès ! Base dispo dans : data/processed/")

    except Exception as e:
        logger.error(f"Erreur lors du chargement : {e}")
        print(f" ERREUR !!! : Erreur lors du chargement {e}")
        raise

if __name__ == "__main__":
    print("--- Lancement du Script de Chargement SQL ---")
    load_data()

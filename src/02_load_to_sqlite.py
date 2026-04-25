import pandas as pd
from sqlalchemy import create_engine
import logging
import os

# --- Gestion experte des chemins ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

# Configuration des logs (on continue d'écrire dans le même fichier)
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'pipeline.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filemode='a'
)
logger = logging.getLogger('LoadToSQLite')

# Préparation de l'URL de la base de données pour SQLAlchemy
os.makedirs(PROCESSED_DIR, exist_ok=True)
db_file_path = os.path.join(PROCESSED_DIR, 'maturite_digitale.db')
# SQLAlchemy a besoin de slashes forward (/) même sous Windows
DB_URL = f"sqlite:///{db_file_path.replace('//', '/').replace('\\', '/')}"

def load_data():
    logger.info("Début du chargement en base SQLite.")
    print("🗄️ Connexion à la base de données...")
    engine = create_engine(DB_URL)
    
    try:
        # On parcourt tous les fichiers du dossier raw
        for file in os.listdir(RAW_DIR):
            if file.endswith('.csv'):
                table_name = file.replace('.csv', '')
                file_path = os.path.join(RAW_DIR, file)
                
                print(f"⏳ Chargement de {file} dans la table '{table_name}'...")
                logger.info(f"Chargement de la table : {table_name}")
                
                # Lecture (Point-virgule habituel à l'INSEE)
                df = pd.read_csv(file_path, sep=';', encoding='utf-8')
                
                # Nettoyage des noms de colonnes (Minuscules, pas d'espaces)
                # C'est crucial pour ne pas avoir de bugs dans la requête SQL après !
                df.columns = df.columns.str.strip().str.lower()
                df.columns = df.columns.str.replace(' ', '_').str.replace("'", "_").str.replace("-", "_")
                
                # Injection dans SQLite
                df.to_sql(table_name, con=engine, if_exists='replace', index=False)
                
                print(f" Table '{table_name}' créée avec {len(df)} lignes.")
                logger.info(f"Table {table_name} créée avec {len(df)} lignes.")
                
        print(f" Chargement terminé avec succès ! Base dispo dans : data/processed/")
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement : {e}")
        print(f" ERREUR !!! : Erreur lors du chargement {e}")
        raise

if __name__ == "__main__":
    print("--- Lancement du Script de Chargement SQL ---")
    load_data()
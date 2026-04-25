import os
import requests
import zipfile
import io
import logging
import time

# --- Gestion experte des chemins ---
# 1. On récupère le chemin absolu du dossier où se trouve ce script (src)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 2. On remonte d'un cran pour obtenir la racine du projet (projet-maturite-digitale)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# 3. On définit les vrais chemins absolus
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

# Configuration des logs
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'pipeline.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filemode='a'
)
logger = logging.getLogger('IngestionAutomatique')

# URL de l'archive INSEE 
ZIP_URL = "https://www.insee.fr/fr/statistiques/fichier/7729450/irecotic23_csv.zip" 

def run_ingestion():
    logger.info("Début du pipeline : Téléchargement du ZIP INSEE.")
    start_time = time.time()
    os.makedirs(RAW_DIR, exist_ok=True)
    
    try:
        print(f"📥 Téléchargement de l'archive ZIP...")
        response = requests.get(ZIP_URL, timeout=20)
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            all_files = z.namelist()
            print(f" Archive téléchargée. Recherche des tables...")
            
            # Cibles en minuscules comme sur ta capture
            targets = {
                "table3": "insee_data.csv",
                "table4": "insee_cloud.csv",
                "table5": "insee_ia.csv"
            }
            
            for keyword, final_name in targets.items():
                matches = [f for f in all_files if keyword in f and f.endswith('.csv')]
                if matches:
                    original_name = matches[0]
                    target_path = os.path.join(RAW_DIR, final_name)
                    
                    print(f" Extraction de {original_name} -> {final_name}")
                    logger.info(f"Extraction de {original_name} vers {final_name}...")
                    
                    with z.open(original_name) as source, open(target_path, "wb") as target:
                        target.write(source.read())
                else:
                    print(f" Attention !!! : {keyword} introuvable dans le ZIP.")
                    logger.warning(f"Attention : aucun fichier trouvé pour le mot-clé {keyword}")
        
        logger.info("Ingestion terminée avec succès.")
        print(f" Ingestion terminée avec succès dans : {RAW_DIR}")
        
    except Exception as e:
        logger.error(f"Échec critique de l'ingestion : {e}")
        print(f" ERREUR !!! : Échec critique de l'ingestion {e}")
        raise
    finally:
        logger.info(f"Temps total ingestion : {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    print("--- Lancement du Script d'Ingestion ---")
    run_ingestion()
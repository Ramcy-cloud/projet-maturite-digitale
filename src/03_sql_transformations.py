import sqlite3
import pandas as pd
import logging
import os
import time

# --- Gestion experte des chemins ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

# Configuration des logs
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'pipeline.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filemode='a'
)
logger = logging.getLogger('SQLTransform')

DB_PATH = os.path.join(PROCESSED_DIR, 'maturite_digitale.db')

def create_maturity_score(conn):
    """Exécute les jointures SQL et calcule le score de maturité digital."""
    
    # La requête SQL de niveau Consultant/Ingénieur
    # On transforme les valeurs brutes en pourcentage en divisant par nb_ent
    query = """
    WITH CloudMaturity AS (
        SELECT 
            act_ir, 
            taille_ir,
            nb_ent,
            -- Score Cloud (Pondération : 30 points max)
            (CAST(cloud AS FLOAT) / NULLIF(nb_ent, 0)) * 30 AS score_cloud
        FROM insee_cloud
    ),
    
    IAMaturity AS (
        SELECT 
            act_ir, 
            taille_ir,
            -- Score IA (Pondération : 40 points max)
            (CAST(ia_tech AS FLOAT) / NULLIF(nb_ent, 0)) * 40 AS score_ia
        FROM insee_ia
    ),
    
    DataMaturity AS (
        SELECT 
            act_ir, 
            taille_ir,
            -- Score Data (Pondération : 30 points max)
            (CAST(analyse_donnees_int AS FLOAT) / NULLIF(nb_ent, 0)) * 30 AS score_data,
            -- On garde aussi l'info ERP pure pour le dashboard PowerBI
            (CAST(pgi_erp AS FLOAT) / NULLIF(nb_ent, 0)) * 100 AS pct_erp
        FROM insee_data
    )
    
    SELECT 
        c.act_ir AS secteur,
        c.taille_ir AS taille,
        c.nb_ent AS total_entreprises,
        ROUND(c.score_cloud, 2) AS score_cloud,
        ROUND(i.score_ia, 2) AS score_ia,
        ROUND(d.score_data, 2) AS score_data,
        ROUND(d.pct_erp, 2) AS pct_erp_utilisation,
        -- Calcul du score global sur 100 (arrondi à 2 décimales)
        ROUND(COALESCE(c.score_cloud, 0) + COALESCE(i.score_ia, 0) + COALESCE(d.score_data, 0), 2) AS digital_maturity_score
    FROM CloudMaturity c
    JOIN IAMaturity i 
        ON c.act_ir = i.act_ir AND c.taille_ir = i.taille_ir
    JOIN DataMaturity d 
        ON c.act_ir = d.act_ir AND c.taille_ir = d.taille_ir
    WHERE c.nb_ent > 0 -- On exclut les lignes vides
    ORDER BY digital_maturity_score DESC
    """
    
    try:
        logger.info("Exécution de la requête SQL de transformation (CTEs & JOINs)...")
        df_score = pd.read_sql_query(query, conn)
        return df_score
    except Exception as e:
        logger.error(f"Erreur SQL : {e}")
        print(f"❌ ERREUR SQL : {e}")
        raise

if __name__ == '__main__':
    print("--- Lancement de la Modélisation SQL ---")
    start_time = time.time()
    
    print("🗄️ Connexion à la base de données...")
    conn = sqlite3.connect(DB_PATH)
    
    print("⚙️ Calcul du Score de Maturité en cours...")
    df_final = create_maturity_score(conn)
    
    print(f"💾 Sauvegarde de la table 'entreprise_score' ({len(df_final)} lignes traitées)...")
    logger.info("Sauvegarde de la table finale 'entreprise_score' dans la base.")
    df_final.to_sql('entreprise_score', conn, if_exists='replace', index=False)
    
    # On exporte aussi en CSV au cas où Power BI ferait des siennes avec SQLite
    csv_final_path = os.path.join(PROCESSED_DIR, 'entreprise_score_final.csv')
    df_final.to_csv(csv_final_path, index=False)
    
    conn.close()
    
    end_time = time.time()
    logger.info(f"Modélisation terminée en {end_time - start_time:.2f}s")
    print(f"🚀 Terminé avec succès ! La table 'entreprise_score' est prête pour Power BI.")
    print(f"Temps total modélisation : {end_time - start_time:.2f}s")
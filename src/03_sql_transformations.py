import logging
import os
import sqlite3
import time

import pandas as pd

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
    filemode='a',
    # Sans cela le journal est ecrit dans l'encodage de la locale (cp1252 sous
    # Windows) : un run local puis un run en CI produisent un fichier a
    # encodage mixte, impossible a relire d'un bloc.
    encoding='utf-8'
)
logger = logging.getLogger('SQLTransform')

DB_PATH = os.path.join(PROCESSED_DIR, 'maturite_digitale.db')
# Tables que la requete attend ; leur absence signale un chargement incomplet.
TABLES_REQUISES = {'insee_cloud', 'insee_data', 'insee_ia'}

def create_maturity_score(conn):
    """Exécute les jointures SQL et calcule le score de maturité digital."""
    

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
        -- Score global sur 100. Volontairement SANS COALESCE(..., 0) : quand une
        -- composante est sous secret statistique INSEE, le total n'est pas
        -- calculable. Il reste NULL plutôt que d'être sous-estimé et présenté
        -- comme une mesure.
        ROUND(c.score_cloud + i.score_ia + d.score_data, 2) AS digital_maturity_score,
        -- Drapeau pour le dashboard : 1 = au moins une composante non diffusée.
        CASE
            WHEN c.score_cloud IS NULL OR i.score_ia IS NULL OR d.score_data IS NULL THEN 1
            ELSE 0
        END AS secret_statistique,
        -- Les 65 lignes ne sont PAS disjointes : « Ens » est un total, pas une
        -- observation. Pour un secteur donné, la ligne Ens est la somme de ses
        -- po1..po4 (vérifié), et Ens/Ens est le total France. Sommer ou moyenner
        -- sans écarter ces lignes compte deux fois les mêmes entreprises.
        CASE WHEN c.act_ir = 'Ens' OR c.taille_ir = 'Ens' THEN 1 ELSE 0 END AS est_agregat,
        -- S_TIC est libellé « DONT secteur producteur de TIC » dans le
        -- dictionnaire INSEE : c'est un sous-ensemble des autres secteurs, déjà
        -- compté dans S_C et S_J_G95.1, pas un secteur de plus.
        CASE WHEN c.act_ir = 'S_TIC' THEN 1 ELSE 0 END AS est_sous_ensemble
    FROM CloudMaturity c
    JOIN IAMaturity i 
        ON c.act_ir = i.act_ir AND c.taille_ir = i.taille_ir
    JOIN DataMaturity d 
        ON c.act_ir = d.act_ir AND c.taille_ir = d.taille_ir
    WHERE c.nb_ent > 0 -- On exclut les lignes vides
    -- Les lignes incalculables sortent en fin de classement, sans faire croire
    -- à un score faible.
    ORDER BY secret_statistique ASC, digital_maturity_score DESC
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
    
    # sqlite3.connect cree un fichier vide si la base est absente : le script
    # echouerait ensuite sur « no such table », en laissant derriere lui un .db
    # vide qui ressemble a une base valide.
    if not os.path.exists(DB_PATH):
        raise SystemExit(
            f"Base introuvable : {DB_PATH}. "
            "Lancer d'abord src/02_load_to_sqlite.py."
        )

    print("🗄️ Connexion à la base de données...")
    conn = sqlite3.connect(DB_PATH)

    # Un chargement interrompu peut laisser une base incomplète. Vérifier le
    # seul fichier ne suffit pas : sans ce contrôle, le script produirait un
    # livrable plausible à partir de tables de millésimes différents, en
    # sortant avec un code 0.
    presentes = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}
    manquantes = sorted(TABLES_REQUISES - presentes)
    if manquantes:
        conn.close()
        raise SystemExit(
            f"Tables absentes de {DB_PATH} : {', '.join(manquantes)}. "
            "Relancer src/02_load_to_sqlite.py."
        )
    
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
    print("🚀 Terminé avec succès ! La table 'entreprise_score' est prête pour Power BI.")
    print(f"Temps total modélisation : {end_time - start_time:.2f}s")
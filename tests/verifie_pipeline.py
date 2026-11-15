"""Vérification de bout en bout du pipeline, sans dépendance de test externe.

Rejoue les étapes 02 et 03 sur une copie du dépôt (jamais sur les fichiers
versionnés), puis contrôle les invariants du calcul de score. Le garde-fou
principal porte sur le secret statistique INSEE : le marqueur `s` doit devenir
NULL et jamais 0, sans quoi les scores sont sous-estimés en silence.

Usage : python tests/verifie_pipeline.py
"""

import csv
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Lignes dont l'indicateur IA est sous secret statistique dans insee_ia.csv.
LIGNES_MASQUEES = {("S_DE", "po2"), ("S_DE", "po4"), ("S_L", "po2"), ("S_L", "po4")}
NB_LIGNES_ATTENDUES = 65
# Colonnes d'étiquettes : du texte légitime, à ne pas confondre avec une mesure.
COLONNES_ETIQUETTES = {"taille_ir", "act_ir"}
# Valeurs de référence relevées sur les données INSEE irecotic23.
REFERENCES = {("S_M", "po4"): 61.9, ("Ens", "Ens"): 18.99}

erreurs = []


def verifie(condition, message):
    if condition:
        print(f"  ok   {message}")
    else:
        print(f"  ECHEC {message}")
        erreurs.append(message)


def prepare_copie(travail):
    """Copie src/ et data/raw/ dans un dossier temporaire."""
    shutil.copytree(os.path.join(RACINE, "src"), os.path.join(travail, "src"))
    shutil.copytree(
        os.path.join(RACINE, "data", "raw"), os.path.join(travail, "data", "raw")
    )


def lance(script, travail):
    """Lance un script du pipeline dans la copie et renvoie le resultat brut."""
    env = dict(os.environ)
    # Les scripts impriment des emojis : sans cela, la console Windows (cp1252)
    # fait echouer le pipeline sur un UnicodeEncodeError.
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, os.path.join(travail, "src", script)],
        capture_output=True,
        text=True,
        # Les scripts écrivent de l'UTF-8 : sans le préciser, la sortie est
        # décodée avec l'encodage local (cp1252 sous Windows) et les emojis
        # font échouer la lecture du flux.
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def rejoue_pipeline(travail):
    """Relance 02 puis 03 sur une copie, en exigeant leur succes."""
    prepare_copie(travail)
    for script in ("02_load_to_sqlite.py", "03_sql_transformations.py"):
        resultat = lance(script, travail)
        if resultat.returncode != 0:
            print(resultat.stdout)
            print(resultat.stderr, file=sys.stderr)
            raise SystemExit(f"Le script {script} a échoué (code {resultat.returncode}).")


def lit_csv(chemin):
    with open(chemin, newline="", encoding="utf-8") as f:
        return {(l["secteur"], l["taille"]): l for l in csv.DictReader(f)}


def main():
    with tempfile.TemporaryDirectory(prefix="verif-pipeline-") as travail:
        print(f"Rejeu du pipeline dans {travail}")
        rejoue_pipeline(travail)

        db = os.path.join(travail, "data", "processed", "maturite_digitale.db")
        conn = sqlite3.connect(db)

        print("\n1. Secret statistique : aucune mesure chargée en texte")
        for table in ("insee_cloud", "insee_data", "insee_ia"):
            colonnes = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            mesures = [c for c in colonnes if c not in COLONNES_ETIQUETTES]
            textuelles = [
                c
                for c in mesures
                if conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE typeof({c}) = 'text'"
                ).fetchone()[0]
            ]
            verifie(not textuelles, f"{table} : aucune colonne de mesure en TEXT {textuelles or ''}")

        print("\n2. Table finale : forme attendue")
        nb, nb_masquees = conn.execute(
            "SELECT COUNT(*), SUM(secret_statistique) FROM entreprise_score"
        ).fetchone()
        verifie(nb == NB_LIGNES_ATTENDUES, f"{nb} lignes (attendu {NB_LIGNES_ATTENDUES})")
        verifie(
            nb_masquees == len(LIGNES_MASQUEES),
            f"{nb_masquees} lignes signalées sous secret (attendu {len(LIGNES_MASQUEES)})",
        )
        masquees = {
            (s, t)
            for s, t in conn.execute(
                "SELECT secteur, taille FROM entreprise_score WHERE secret_statistique = 1"
            )
        }
        verifie(masquees == LIGNES_MASQUEES, f"lignes masquées = {sorted(LIGNES_MASQUEES)}")

        print("\n3. Une mesure masquée ne vaut jamais 0")
        zeros = conn.execute(
            "SELECT secteur, taille FROM entreprise_score "
            "WHERE secret_statistique = 1 AND (score_ia = 0 OR digital_maturity_score IS NOT NULL)"
        ).fetchall()
        verifie(not zeros, f"score_ia et score global restent NULL sur ces lignes {zeros or ''}")

        print("\n4. Les lignes complètes gardent un score calculé")
        trous = conn.execute(
            "SELECT secteur, taille FROM entreprise_score WHERE secret_statistique = 0 AND ("
            "score_cloud IS NULL OR score_ia IS NULL OR score_data IS NULL "
            "OR digital_maturity_score IS NULL)"
        ).fetchall()
        verifie(not trous, f"aucun trou sur les lignes non masquées {trous or ''}")

        print("\n5. Bornes et pondération (cloud 30 + IA 40 + data 30 = 100)")
        hors_bornes = conn.execute(
            "SELECT secteur, taille, digital_maturity_score FROM entreprise_score "
            "WHERE digital_maturity_score NOT BETWEEN 0 AND 100"
        ).fetchall()
        verifie(not hors_bornes, f"tous les scores globaux dans [0, 100] {hors_bornes or ''}")
        incoherents = conn.execute(
            "SELECT secteur, taille FROM entreprise_score WHERE secret_statistique = 0 AND "
            "ABS(digital_maturity_score - (score_cloud + score_ia + score_data)) > 0.02"
        ).fetchall()
        verifie(not incoherents, f"score global = somme des trois sous-scores {incoherents or ''}")

        print("\n6. Valeurs de référence")
        for (secteur, taille), attendu in REFERENCES.items():
            obtenu = conn.execute(
                "SELECT digital_maturity_score FROM entreprise_score "
                "WHERE secteur = ? AND taille = ?",
                (secteur, taille),
            ).fetchone()
            # Si la ligne existe mais que le score est NULL, fetchone() renvoie
            # (None,) : il faut tester la valeur et pas seulement le tuple, sinon
            # le scénario « une référence passe sous secret statistique » lève un
            # TypeError au lieu d'être signalé comme un échec lisible.
            valeur = obtenu[0] if obtenu else None
            verifie(
                valeur is not None and abs(valeur - attendu) < 0.01,
                f"{secteur}/{taille} = {attendu} "
                f"(obtenu {valeur if valeur is not None else 'NULL ou ligne absente'})",
            )

        print("\n7. Classement : les lignes non calculables sortent en dernier")
        drapeaux = [
            r[0] for r in conn.execute("SELECT secret_statistique FROM entreprise_score")
        ]
        verifie(
            drapeaux == sorted(drapeaux),
            "aucune ligne masquée intercalée dans le classement",
        )

        print("\n8. Dénominateurs cohérents entre les trois tables brutes")
        for table in ("insee_cloud", "insee_data", "insee_ia"):
            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            verifie(
                total == NB_LIGNES_ATTENDUES,
                f"{table} : {total} lignes avant jointure (attendu {NB_LIGNES_ATTENDUES})",
            )
        # Chaque CTE de 03 divise par SON propre nb_ent, alors que le WHERE ne
        # contrôle que celui de insee_cloud : si les trois fichiers divergeaient,
        # les sous-scores ne seraient plus comparables entre eux.
        divergences = conn.execute(
            "SELECT COUNT(*) FROM insee_cloud c "
            "JOIN insee_ia i USING (act_ir, taille_ir) "
            "JOIN insee_data d USING (act_ir, taille_ir) "
            "WHERE c.nb_ent IS NOT i.nb_ent OR c.nb_ent IS NOT d.nb_ent"
        ).fetchone()[0]
        verifie(divergences == 0, f"nb_ent identique dans les trois tables ({divergences} écart(s))")

        conn.close()

        print("\n9. Artefacts versionnés à jour par rapport au code")
        attendu = lit_csv(os.path.join(travail, "data", "processed", "entreprise_score_final.csv"))
        livre = lit_csv(os.path.join(RACINE, "data", "processed", "entreprise_score_final.csv"))
        verifie(set(attendu) == set(livre), "mêmes couples secteur x taille")
        ecarts = [
            (cle, col, livre[cle][col], attendu[cle][col])
            for cle in attendu
            if cle in livre
            for col in attendu[cle]
            if livre[cle][col] != attendu[cle][col]
        ]
        verifie(not ecarts, f"entreprise_score_final.csv identique au rejeu {ecarts[:5] or ''}")

    print("\n10. Un marqueur INSEE inconnu fait échouer le chargement")
    with tempfile.TemporaryDirectory(prefix="verif-marqueur-") as bac:
        prepare_copie(bac)
        cible = os.path.join(bac, "data", "raw", "insee_ia.csv")
        with open(cible, encoding="utf-8") as f:
            texte = f.read()
        # Remplace le « s » isolé par « nd », autre marqueur INSEE, sans toucher
        # aux étiquettes (Ens, S_DE, po1...).
        altere, remplaces = re.subn(r"(?<=;)s(?=[;\r\n]|$)", "nd", texte, flags=re.M)
        with open(cible, "w", encoding="utf-8", newline="") as f:
            f.write(altere)
        verifie(remplaces > 0, f"{remplaces} marqueur(s) remplacé(s) par « nd » dans la copie")
        resultat = lance("02_load_to_sqlite.py", bac)
        verifie(
            resultat.returncode != 0,
            "le chargement refuse « nd » au lieu de le charger comme un 0 silencieux",
        )
        verifie(
            "nd" in (resultat.stdout + resultat.stderr),
            "le message d'erreur nomme la valeur fautive",
        )

    print()
    if erreurs:
        print(f"{len(erreurs)} vérification(s) en échec.")
        return 1
    print("Toutes les vérifications passent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

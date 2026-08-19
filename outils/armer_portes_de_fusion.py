"""Exiger un pipeline vert avant fusion, sur tous les dépôts ADSUM.

Ce réglage est demandé par la gouvernance et il n'est **pas** appliqué d'office, pour
une raison précise : les minutes de calcul partagées du groupe sont épuisées. Aucun
pipeline ne peut aboutir, donc l'activer aujourd'hui rendrait toute fusion impossible
sur les vingt-huit dépôts. Une porte qui refuse tout le monde n'est pas une porte,
c'est un mur, et le premier réflexe serait de la retirer.

Le script refuse donc de s'exécuter tant qu'aucun pipeline vert récent n'existe. Ce
garde-fou n'est pas une précaution théorique : c'est exactement l'erreur que la
situation actuelle invite à commettre.

Usage :

    python outils/armer_portes_de_fusion.py --verifier   # dit ce qui serait fait
    python outils/armer_portes_de_fusion.py --appliquer  # applique

Le jeton est lu dans .secret/gitlab-api-secret.json, jamais affiché.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GROUPE = "sr-media-ai"
PREFIXE = "sr-media-ai/adsum/"

#: Un pipeline vert de moins de trente jours suffit à prouver que la CI peut aboutir.
#: Au-delà, la preuve est trop vieille pour dire quoi que ce soit de l'état actuel.
JOURS_DE_PREUVE = 30


def _jeton() -> tuple[str, str]:
    for candidat in (Path(".secret/gitlab-api-secret.json"),
                     Path("../../../.secret/gitlab-api-secret.json")):
        if candidat.exists():
            s = json.load(io.open(candidat, encoding="utf-8"))
            return s["private_token"], s["gitlab_url"].rstrip("/")
    raise SystemExit("gitlab-api-secret.json introuvable.")


def _api(racine: str, jeton: str, chemin: str, methode: str = "GET",
         charge: dict | None = None):
    donnees = json.dumps(charge).encode() if charge is not None else None
    requete = urllib.request.Request(
        f"{racine}/api/v4{chemin}", data=donnees, method=methode,
        headers={"PRIVATE-TOKEN": jeton, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=60) as reponse:
            corps = reponse.read()
            return reponse.status, (json.loads(corps) if corps.strip() else {})
    except urllib.error.HTTPError as erreur:
        return erreur.code, {}


def _projets(racine: str, jeton: str) -> list[dict]:
    trouves, page = [], 1
    while True:
        code, lot = _api(racine, jeton,
                         f"/groups/{GROUPE}/projects?include_subgroups=true"
                         f"&archived=false&per_page=100&page={page}")
        if code != 200 or not isinstance(lot, list) or not lot:
            break
        trouves += [p for p in lot if p["path_with_namespace"].startswith(PREFIXE)]
        if len(lot) < 100:
            break
        page += 1
    return trouves


def _ci_peut_aboutir(racine: str, jeton: str, projets: list[dict]) -> tuple[bool, str]:
    """Un pipeline vert récent existe-t-il quelque part dans ADSUM.

    Un seul suffit : il prouve qu'un exécuteur répond et que les minutes ne sont pas
    épuisées. En chercher un par dépôt refuserait l'activation pour des dépôts qui
    n'ont simplement rien poussé depuis longtemps.
    """
    limite = (dt.datetime.now(dt.timezone.utc)
              - dt.timedelta(days=JOURS_DE_PREUVE)).isoformat()
    plus_recent = ""
    for projet in projets:
        code, pipelines = _api(racine, jeton,
                               f"/projects/{projet['id']}/pipelines"
                               f"?status=success&per_page=1")
        if code != 200 or not pipelines:
            continue
        quand = str(pipelines[0].get("updated_at") or "")
        plus_recent = max(plus_recent, quand)
        # La fraîcheur compte autant que l'existence. Un vert d'il y a un an prouve
        # qu'un exécuteur a répondu un jour, pas qu'il répondra aujourd'hui, et c'est
        # précisément la question posée avant d'armer une porte qui bloque tout.
        if quand > limite:
            return True, (f"pipeline vert sur {projet['path_with_namespace']} "
                          f"le {quand[:10]}, soit moins de {JOURS_DE_PREUVE} jours.")
    if plus_recent:
        return False, (f"aucun pipeline vert depuis {JOURS_DE_PREUVE} jours. Le plus "
                       f"récent date du {plus_recent[:10]}. Armer la porte "
                       "maintenant rendrait toute fusion impossible.")
    return False, ("aucun pipeline vert dans tout ADSUM. Armer la porte "
                   "maintenant rendrait toute fusion impossible.")


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--appliquer", action="store_true")
    analyseur.add_argument("--forcer", action="store_true",
                           help="Passer outre l'absence de pipeline vert. À n'employer "
                                "qu'en sachant que plus rien ne pourra fusionner.")
    arguments = analyseur.parse_args(argv)

    jeton, racine = _jeton()
    projets = _projets(racine, jeton)
    print(f"{len(projets)} dépôts ADSUM actifs.")

    possible, raison = _ci_peut_aboutir(racine, jeton, projets)
    print(("PREUVE : " if possible else "REFUS : ") + raison)
    if not possible and not arguments.forcer:
        print("\nRien n'a été modifié. Relancer une fois la CI opérationnelle, ou "
              "passer --forcer en connaissance de cause.")
        return 1

    a_faire = [p for p in projets
               if not p.get("only_allow_merge_if_pipeline_succeeds")]
    print(f"{len(a_faire)} dépôt(s) sans la porte.")
    if not arguments.appliquer:
        for p in a_faire:
            print("  " + p["path_with_namespace"])
        print("\nMode vérification. Relancer avec --appliquer.")
        return 0

    faits = 0
    for p in a_faire:
        code, _ = _api(racine, jeton, f"/projects/{p['id']}", "PUT",
                       {"only_allow_merge_if_pipeline_succeeds": True})
        faits += code == 200
        if code != 200:
            print(f"  échec {code} sur {p['path_with_namespace']}")
    print(f"Porte armée sur {faits}/{len(a_faire)} dépôts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

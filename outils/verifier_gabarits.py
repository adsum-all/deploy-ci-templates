"""Vérifier les gabarits CI avant qu'ils ne cassent les pipelines des autres dépôts.

Ce dépôt est consommé par une trentaine de projets. Une erreur ici ne se voit pas
ici : elle se voit chez eux, sous la forme d'un pipeline qui tombe sans créer la
moindre tâche, ce qui est le message le plus opaque que GitLab sache produire. C'est
arrivé trois fois de suite en ajoutant un simple gabarit.

Trois contrôles, choisis parce que ce sont les trois pannes réellement observées.

1. La syntaxe. Un YAML invalide casse tout le monde d'un coup.
2. Les étapes citées mais non déclarées. Retirer une étape du socle est indolore ici
   et fatal chez le consommateur qui l'utilise encore.
3. Les héritages vers un modèle absent du fichier. GitLab ne résout `extends` qu'à
   l'intérieur de la configuration assemblée ; un modèle qui vit dans un autre
   gabarit non inclus produit une erreur au chargement.

Un fichier qui ne rend pas un dictionnaire est signalé, jamais sauté en silence :
c'est ainsi que deux gabarits absents de la branche sont passés inaperçus.
"""
from __future__ import annotations

import pathlib
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - dépendance de CI
    print("FAIL: pyyaml absent. Installer avec : pip install pyyaml")
    raise SystemExit(2) from None

RACINE = pathlib.Path(__file__).resolve().parents[1]
GABARITS = RACINE / "templates"
SOCLE = GABARITS / "base.yml"

#: Clés de premier niveau qui ne sont pas des tâches. Les confondre avec des tâches
#: produirait des manquements imaginaires sur `variables` ou `workflow`.
NON_TACHES = frozenset({"variables", "workflow", "default", "include", "stages"})


def _charger(chemin: pathlib.Path):
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))


def verifier() -> list[str]:
    manquements: list[str] = []
    socle = _charger(SOCLE)
    if not isinstance(socle, dict) or "stages" not in socle:
        return [f"{SOCLE.name} ne déclare aucune étape : tout le reste en dépend."]
    etapes = set(socle["stages"])

    for chemin in sorted(GABARITS.glob("*.yml")):
        try:
            contenu = _charger(chemin)
        except yaml.YAMLError as erreur:
            manquements.append(f"{chemin.name} : syntaxe invalide : {str(erreur)[:140]}")
            continue
        if not isinstance(contenu, dict):
            manquements.append(
                f"{chemin.name} : ne rend pas un dictionnaire. Fichier vide ou mal formé.")
            continue

        taches = {nom: corps for nom, corps in contenu.items()
                  if isinstance(corps, dict) and nom not in NON_TACHES}
        modeles = {nom for nom in taches if nom.startswith(".")}

        for nom, corps in taches.items():
            etape = corps.get("stage")
            if etape and etape not in etapes:
                manquements.append(
                    f"{chemin.name} : « {nom} » cite l'étape « {etape} », "
                    f"absente de {SOCLE.name}.")
            herite = corps.get("extends")
            parents = [herite] if isinstance(herite, str) else (herite or [])
            for parent in parents:
                if str(parent).startswith(".") and parent not in modeles:
                    manquements.append(
                        f"{chemin.name} : « {nom} » hérite de « {parent} », "
                        "qui n'est pas défini dans ce fichier.")
    return manquements


def main() -> int:
    manquements = verifier()
    if manquements:
        print("Gabarits CI : manquements bloquants\n")
        for m in manquements:
            print("  " + m)
        return 1
    nombre = len(list(GABARITS.glob("*.yml")))
    print(f"Les {nombre} gabarits sont valides, leurs étapes déclarées et leurs "
          "héritages résolus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

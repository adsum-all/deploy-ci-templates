"""Vérification des deux politiques d'accès ADSUM.

Un fichier JSON de politique qui n'est pas vérifié devient un document décoratif en
deux versions : celle qu'on lit et celle que le code applique. Cet outil est ce qui
empêche l'écart, et il refuse plus que ce que les schémas peuvent exprimer.

Trois passes.

1. Forme. Chaque politique est validée contre son schéma JSON. C'est la passe qui
   attrape une faute de frappe dans un nom de champ.

2. Cohérence interne. Un rôle cité doit être déclaré, une capacité accordée doit
   exister, un héritage ne doit pas boucler, un événement d'audit référencé doit
   figurer au catalogue. Aucune de ces règles ne s'exprime en JSON Schema, et ce sont
   celles qui pourrissent en premier : on ajoute un rôle, on oublie une référence.

3. Frontière. La seule passe qui compte vraiment. Elle refuse qu'une capacité change
   de côté, qu'une route soit revendiquée par les deux mondes, qu'un rôle porte le
   même nom des deux côtés, ou qu'une route éditeur expose une donnée personnelle
   hors du chemin d'assistance exceptionnelle.

Sortie : rien sur la sortie standard quand tout va, la liste des manquements sinon,
et un code de retour non nul. Une option --json rend le tout exploitable par la CI.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
SCHEMAS = RACINE / "schemas"

#: Ce que la validation traite comme bloquant. Le reste est signalé sans faire échouer,
#: parce qu'une politique en cours d'écriture doit pouvoir être relue avant d'être tenue.
GRAVITES_BLOQUANTES = frozenset({"frontiere", "forme", "coherence"})


class Manquement:
    """Un défaut trouvé, avec de quoi le corriger sans relire tout le fichier."""

    __slots__ = ("categorie", "ou", "quoi", "pourquoi")

    def __init__(self, categorie: str, ou: str, quoi: str, pourquoi: str) -> None:
        self.categorie = categorie
        self.ou = ou
        self.quoi = quoi
        self.pourquoi = pourquoi

    def dictionnaire(self) -> dict[str, str]:
        return {"categorie": self.categorie, "ou": self.ou,
                "quoi": self.quoi, "pourquoi": self.pourquoi}

    def __str__(self) -> str:
        return f"[{self.categorie}] {self.ou} : {self.quoi}\n    {self.pourquoi}"


def _lire(chemin: Path) -> Any:
    return json.load(io.open(chemin, encoding="utf-8"))


# -- Passe 1 : la forme -------------------------------------------------------

def valider_la_forme(politique: Any, schema_nom: str) -> list[Manquement]:
    """Valide contre le schéma JSON, en résolvant les références locales.

    Les schémas se citent par un chemin relatif (common.schema.json#/$defs/...). Sans
    registre, la bibliothèque tenterait de les résoudre sur le réseau, ce qui échoue
    en CI hors ligne et, pire, réussirait un jour contre une version qui n'est pas
    celle du dépôt.
    """
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:
        return [Manquement(
            "outil", schema_nom, "jsonschema absent",
            "Installer jsonschema pour valider la forme : pip install jsonschema")]

    registre = Registry()
    for fichier in SCHEMAS.glob("*.schema.json"):
        contenu = _lire(fichier)
        ressource = Resource.from_contents(contenu)
        # Enregistré sous son nom de fichier, qui est la façon dont les schémas se
        # citent entre eux, et sous son $id, que la bibliothèque suit par défaut.
        registre = registre.with_resource(fichier.name, ressource)
        if "$id" in contenu:
            registre = registre.with_resource(contenu["$id"], ressource)

    schema = _lire(SCHEMAS / schema_nom)
    validateur = Draft202012Validator(schema, registry=registre)
    manquements: list[Manquement] = []
    for erreur in sorted(validateur.iter_errors(politique), key=lambda e: list(e.path)):
        chemin = "/".join(str(p) for p in erreur.path) or "(racine)"
        manquements.append(Manquement("forme", chemin, erreur.message,
                                      f"Contredit le schéma {schema_nom}."))
    return manquements


# -- Passe 2 : la cohérence interne -------------------------------------------

def _capacites_declarees(politique: dict[str, Any], cote: str) -> set[str]:
    """Toutes les capacités que la politique définit quelque part.

    Une capacité accordée à un rôle mais définie nulle part est un droit fantôme :
    personne ne sait ce qu'il ouvre, et le premier lecteur la supprimera ou
    l'élargira au jugé.
    """
    capacites: set[str] = set()
    if cote == "client":
        capacites |= {a["id"] for a in politique.get("actions", [])}
        for module in politique.get("module_entitlements", {}).get("modules", []):
            capacites |= set(module.get("capabilities", []))
    else:
        for cle in ("tenant_operations", "commerce_operations"):
            capacites |= {o["id"] for o in politique.get(cle, [])}
        capacites |= {o["id"] for o in
                      politique.get("support_operations", {}).get("operations", [])}
        capacites |= {o["id"] for o in
                      politique.get("observability_operations", {}).get("operations", [])}
        capacites |= {a["id"] for a in politique.get("privileged_actions", [])}
        bris = politique.get("break_glass", {}).get("id")
        if bris:
            capacites.add(bris)
    return capacites


def _roles_declares(politique: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in politique.get("roles", [])}


def _capacites_effectives(role_id: str, roles: dict[str, dict[str, Any]],
                          vus: frozenset[str] = frozenset()) -> set[str]:
    """Capacités d'un rôle, héritage compris. Un cycle rend un ensemble partiel
    plutôt que de boucler ; le cycle est signalé ailleurs, par _cycles."""
    if role_id in vus or role_id not in roles:
        return set()
    role = roles[role_id]
    acquis = set(role.get("grants", []))
    for parent in role.get("inherits", []):
        acquis |= _capacites_effectives(parent, roles, vus | {role_id})
    return acquis


def _cycles(roles: dict[str, dict[str, Any]]) -> list[list[str]]:
    """Les cycles d'héritage. Un cycle fait qu'aucun des rôles concernés n'a
    d'ensemble de droits défini, et le calcul dépend alors de l'ordre de parcours."""
    trouves: list[list[str]] = []

    def descendre(courant: str, pile: list[str]) -> None:
        if courant in pile:
            trouves.append(pile[pile.index(courant):] + [courant])
            return
        for parent in roles.get(courant, {}).get("inherits", []):
            descendre(parent, pile + [courant])

    for identifiant in roles:
        descendre(identifiant, [])
    return trouves


def verifier_la_coherence(politique: dict[str, Any], cote: str) -> list[Manquement]:
    manquements: list[Manquement] = []
    roles = _roles_declares(politique)
    capacites = _capacites_declarees(politique, cote)
    evenements = {e["event"] for e in politique.get("audit_events", [])}

    for cycle in _cycles(roles):
        manquements.append(Manquement(
            "coherence", " -> ".join(cycle), "héritage circulaire",
            "Aucun de ces rôles n'a d'ensemble de droits défini : le résultat "
            "dépendrait de l'ordre dans lequel on parcourt la chaîne."))

    for identifiant, role in roles.items():
        for parent in role.get("inherits", []):
            if parent not in roles:
                manquements.append(Manquement(
                    "coherence", identifiant, f"hérite de « {parent} », non déclaré",
                    "Un héritage vers un rôle absent n'accorde rien, en silence."))
        for capacite in role.get("grants", []):
            if capacite not in capacites:
                manquements.append(Manquement(
                    "coherence", identifiant, f"accorde « {capacite} », non définie",
                    "Droit fantôme : rien ne dit ce qu'il ouvre, et le prochain "
                    "lecteur l'élargira ou le supprimera au jugé."))
        if role.get("exists_in_code") and not role.get("code_reference"):
            manquements.append(Manquement(
                "coherence", identifiant, "déclaré présent dans le code sans référence",
                "Sans depot:chemin:ligne, l'affirmation n'est pas vérifiable et "
                "survivra à la suppression du code qu'elle décrit."))
        if not role.get("exists_in_code") and not role.get("implementation_ticket"):
            manquements.append(Manquement(
                "coherence", identifiant, "rôle à créer sans référence de suivi",
                "Un rôle déclaré mais jamais implémenté donne l'illusion d'une "
                "couverture qui n'existe pas."))

    for cle, liste in _actions_avec_audit(politique, cote):
        for element in liste:
            evenement = element.get("audit_event")
            if evenement and evenement not in evenements:
                manquements.append(Manquement(
                    "coherence", f"{cle}/{element['id']}",
                    f"référence l'événement « {evenement} », absent du catalogue",
                    "L'action se croit tracée alors que rien ne décrit sa trace."))

    manquements += _verifier_references_de_roles(politique, cote, roles)
    return manquements


def _actions_avec_audit(politique: dict[str, Any], cote: str) -> list[tuple[str, list[Any]]]:
    if cote == "client":
        return [("actions", politique.get("actions", []))]
    return [
        ("tenant_operations", politique.get("tenant_operations", [])),
        ("commerce_operations", politique.get("commerce_operations", [])),
        ("support_operations", politique.get("support_operations", {}).get("operations", [])),
        ("privileged_actions", politique.get("privileged_actions", [])),
    ]


def _verifier_references_de_roles(politique: dict[str, Any], cote: str,
                                  roles: dict[str, dict[str, Any]]) -> list[Manquement]:
    """Tout rôle cité ailleurs dans le fichier doit être déclaré."""
    manquements: list[Manquement] = []

    def controler(ou: str, cites: list[str]) -> None:
        for role in cites:
            if role not in roles:
                manquements.append(Manquement(
                    "coherence", ou, f"cite le rôle « {role} », non déclaré",
                    "Une règle qui vise un rôle inexistant ne s'applique à personne "
                    "et donne l'impression d'un contrôle."))

    if cote == "client":
        for application in politique.get("applications", []):
            controler(f"applications/{application['id']}", application.get("roles_allowed", []))
        for frontiere in politique.get("data_boundaries", []):
            controler("data_boundaries", [frontiere["role"]])
        for action in politique.get("actions", []):
            controler(f"actions/{action['id']}", [action["minimum_role"]])
    else:
        for application in politique.get("internal_applications", []):
            controler(f"internal_applications/{application['id']}",
                      application.get("roles_allowed", []))
        for cle, liste in _actions_avec_audit(politique, cote):
            for element in liste:
                controler(f"{cle}/{element['id']}", [element["minimum_role"]])
        for action in politique.get("privileged_actions", []):
            if action.get("approver_role"):
                controler(f"privileged_actions/{action['id']}", [action["approver_role"]])
        for operation in politique.get("observability_operations", {}).get("operations", []):
            controler(f"observability_operations/{operation['id']}", [operation["minimum_role"]])
        approbateur = politique.get("break_glass", {}).get("approver_role")
        if approbateur:
            controler("break_glass", [approbateur])
    return manquements


# -- Passe 3 : la frontière ---------------------------------------------------

def _toutes_les_routes(politique: dict[str, Any], cote: str) -> list[tuple[str, dict[str, Any]]]:
    cle = "applications" if cote == "client" else "internal_applications"
    return [(application["id"], route)
            for application in politique.get(cle, [])
            for route in application.get("routes", [])]


def verifier_la_frontiere(client: dict[str, Any], editeur: dict[str, Any]) -> list[Manquement]:
    """La passe qui justifie l'existence de l'outil.

    Les schémas imposent déjà les préfixes, donc une capacité ne peut pas
    littéralement figurer des deux côtés. Restent les recouvrements que le préfixe
    ne voit pas : deux routes identiques revendiquées par les deux mondes, un nom de
    rôle identique au préfixe près, une audience partagée, une donnée personnelle
    exposée par une route éditeur.
    """
    manquements: list[Manquement] = []

    capacites_client = _capacites_declarees(client, "client")
    capacites_editeur = _capacites_declarees(editeur, "editor")
    for capacite in sorted(capacites_client & capacites_editeur):
        manquements.append(Manquement(
            "frontiere", capacite, "capacité déclarée des deux côtés",
            "Une capacité partagée efface la frontière : le contrôle ne peut plus "
            "dire de quel monde relève l'appelant."))

    # Le même mot des deux côtés, préfixe retiré. C'est exactement ce qui est arrivé
    # avec « admin » et « super_admin » : le trésorier d'une paroisse présentait un
    # jeton disant « admin » et obtenait la liste de tous les clients d'ADSUM.
    noms_client = {r["id"].removeprefix("client-") for r in client.get("roles", [])}
    noms_editeur = {r["id"].removeprefix("editor-") for r in editeur.get("roles", [])}
    for nom in sorted(noms_client & noms_editeur):
        # Signalé sans bloquer. La nomenclature retenue veut délibérément
        # « client-super-admin » en face de « editor-super-admin » : le préfixe est
        # le mécanisme, et le schéma le rend obligatoire. Ce qui a ouvert la console
        # de l'éditeur, ce n'est pas la ressemblance des mots, c'est qu'un seul mot
        # servait aux deux. Reste que l'homonymie trompe en réunion et en revue, et
        # qu'il vaut mieux la voir écrite que la découvrir dans un malentendu.
        manquements.append(Manquement(
            "vigilance", nom, "radical de rôle commun aux deux côtés",
            f"« client-{nom} » et « editor-{nom} » ne désignent pas la même "
            "autorité. Le préfixe les sépare partout où le code décide ; il ne "
            "sépare rien dans une phrase prononcée à l'oral."))

    routes_client = {(r["method"], r["path"]) for _, r in _toutes_les_routes(client, "client")}
    routes_editeur = {(r["method"], r["path"]) for _, r in _toutes_les_routes(editeur, "editor")}
    for methode, chemin in sorted(routes_client & routes_editeur):
        manquements.append(Manquement(
            "frontiere", f"{methode} {chemin}", "route revendiquée par les deux politiques",
            "Le serveur n'a qu'une table de routage : une seule des deux règles "
            "s'appliquera, et rien ne dit laquelle."))

    audience_client = client.get("scope", {}).get("token_audience")
    audience_editeur = editeur.get("scope", {}).get("token_audience")
    if audience_client and audience_client == audience_editeur:
        manquements.append(Manquement(
            "frontiere", "scope/token_audience", "audience de jeton commune",
            "Un jeton unique ouvrirait les deux mondes : c'est l'état d'avant, où "
            "le même jeton servait la console et l'espace membre."))

    bris = editeur.get("break_glass", {}).get("id")
    for application, route in _toutes_les_routes(editeur, "editor"):
        if route.get("personal_data") and route["capability"] != bris:
            manquements.append(Manquement(
                "frontiere", f"{application} : {route['method']} {route['path']}",
                "route éditeur exposant une donnée personnelle hors assistance",
                "Exploiter la plateforme n'est pas lire les données de ses clients. "
                "Cette lecture doit passer par l'assistance exceptionnelle, qui est "
                "autorisée par le client, bornée dans le temps et notifiée."))

    for role in editeur.get("roles", []):
        if role.get("may_read_client_personal_data"):
            manquements.append(Manquement(
                "frontiere", role["id"], "rôle éditeur lisant des données personnelles",
                "Aucun rôle interne ne donne ce droit par lui-même, propriétaire "
                "compris. Le chemin existe et s'appelle assistance exceptionnelle."))

    return manquements


# -- Preuves ------------------------------------------------------------------

def verifier_les_preuves(politique: dict[str, Any], nom: str) -> list[Manquement]:
    """Une interdiction sans test associé est une intention.

    Signalé sans bloquer : la politique se pose avant les tests qui la prouvent, et
    exiger la preuve dès la première écriture empêcherait d'écrire la politique.
    Le compte, lui, doit descendre à zéro.
    """
    return [
        Manquement("preuve", f"{nom}/{interdiction['id']}", "interdiction non prouvée",
                   "Aucun test ne démontre le refus. Tant que ce champ est vide, la "
                   "règle repose sur la relecture humaine.")
        for interdiction in politique.get("prohibited_capabilities", [])
        if not interdiction.get("test")
    ]


# -- Entrée -------------------------------------------------------------------

def verifier(chemin_client: Path, chemin_editeur: Path) -> list[Manquement]:
    client = _lire(chemin_client)
    editeur = _lire(chemin_editeur)

    manquements: list[Manquement] = []
    manquements += valider_la_forme(client, "client-access-policy.schema.json")
    manquements += valider_la_forme(editeur, "editor-access-policy.schema.json")
    manquements += verifier_la_coherence(client, "client")
    manquements += verifier_la_coherence(editeur, "editor")
    manquements += verifier_la_frontiere(client, editeur)
    manquements += verifier_les_preuves(client, "client")
    manquements += verifier_les_preuves(editeur, "editeur")
    return manquements


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--client", type=Path,
                           default=RACINE / "client-access-policy.json")
    analyseur.add_argument("--editeur", type=Path,
                           default=RACINE / "editor-access-policy.json")
    analyseur.add_argument("--json", action="store_true",
                           help="Sortie exploitable par la CI.")
    analyseur.add_argument("--strict", action="store_true",
                           help="Les interdictions non prouvées font échouer.")
    arguments = analyseur.parse_args(argv)

    manquements = verifier(arguments.client, arguments.editeur)
    bloquants = [m for m in manquements
                 if m.categorie in GRAVITES_BLOQUANTES
                 or (arguments.strict and m.categorie == "preuve")]

    if arguments.json:
        print(json.dumps({
            "total": len(manquements),
            "bloquants": len(bloquants),
            "manquements": [m.dictionnaire() for m in manquements],
        }, ensure_ascii=False, indent=2))
    else:
        for manquement in manquements:
            print(manquement)
        if not manquements:
            print("Les deux politiques sont valides, cohérentes et disjointes.")
        else:
            print(f"\n{len(manquements)} manquement(s), dont {len(bloquants)} bloquant(s).")

    return 1 if bloquants else 0


if __name__ == "__main__":
    sys.exit(main())

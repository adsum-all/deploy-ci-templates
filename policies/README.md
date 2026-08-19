# Politiques d'accès ADSUM

Deux fichiers décrivent qui peut quoi, de part et d'autre de la frontière qui sépare
les organisations clientes de l'entreprise qui édite ADSUM.

| Fichier | Ce qu'il gouverne |
|---|---|
| `client-access-policy.json` | Ce que peut une organisation cliente, ses administrateurs, ses membres. |
| `editor-access-policy.json` | Ce que peut l'entreprise éditrice : exploitation, commerce, support, sécurité. |

Ils ne sont pas de la documentation. Trois mécanismes les rendent contraignants, et
sans ces trois mécanismes ils ne vaudraient rien.

1. `policies/outils/verifier_politiques.py` valide leur forme, leur cohérence interne
   et la disjonction des deux mondes. La tâche CI `policy:validate` l'exécute.
2. Chaque dépôt qui applique la politique porte un test `tests/test_conformite_politiques.py`
   qui compare sa table de routage réelle à ce que la politique déclare. La tâche
   `policy:conformance` l'exécute.
3. Chaque interdiction porte le chemin du test qui prouve le refus. Une interdiction
   sans test est signalée à chaque exécution : la règle repose alors sur la relecture
   humaine, ce qui est un état transitoire et non un état d'équilibre.

## Pourquoi la frontière a besoin d'être écrite

Le 19 août 2026, vingt routes de la console de l'éditeur étaient gardées par la
permission `support.traiter`. Cette permission est accordée par défaut aux rôles
`admin` et `super_admin` d'une organisation cliente. Concrètement, le trésorier d'une
paroisse pouvait lister toutes les organisations clientes d'ADSUM, en créer une, en
suspendre une autre et modifier ses modules.

Le défaut n'était pas une garde oubliée : chaque route en avait une. Le défaut était
qu'un rôle porte la frontière, alors que le même mot existe des deux côtés. C'est la
raison pour laquelle l'autorité éditeur vient désormais d'une inscription dans
`operateur_editeur`, et pour laquelle les capacités portent un préfixe.

## Ajouter un rôle

1. Choisir le côté. Un rôle est client ou éditeur, jamais les deux. Si la question se
   pose, c'est que deux rôles distincts se cachent derrière un seul nom.
2. Le nommer `client-...` ou `editor-...`. Le schéma refuse tout autre préfixe.
3. Écrire son `purpose` en disant ce qu'il **ne** peut **pas** faire, pas seulement ce
   qu'il peut. C'est la partie qu'on relit dans deux ans.
4. Lui donner des `grants` pris parmi les capacités déjà déclarées. Le vérificateur
   refuse une capacité inconnue : c'est ce qui empêche les droits fantômes.
5. Renseigner honnêtement `exists_in_code`. Si le code ne le porte pas encore, mettre
   `implementation_ticket` et laisser `exists_in_code` à faux. Un rôle déclaré présent
   sans référence vérifiable est refusé par le vérificateur.
6. Côté éditeur, `mfa` ne peut valoir que `obligatoire` ou `obligatoire-renforce`, et
   `may_read_client_personal_data` ne peut valoir que faux. Le schéma l'impose : ce ne
   sont pas des réglages.
7. Ajouter le rôle aux `roles_allowed` des applications qui doivent s'ouvrir à lui, et
   lui écrire une entrée `data_boundaries` côté client. Le champ `never` doit contenir
   au moins une ligne.

## Ajouter une capacité

1. La nommer `client.<domaine>.<action>` ou `editor.<domaine>.<action>`.
2. La déclarer là où son espèce l'appelle : `actions` côté client ;
   `tenant_operations`, `commerce_operations`, `support_operations.operations`,
   `observability_operations.operations` ou `privileged_actions` côté éditeur.
3. Si elle fait mal, la déclarer en `privileged_actions` avec son garde-fou complet :
   rôle minimum, approbation, confirmation, justification, données touchées, effet,
   retour arrière, événement d'audit, notification, durée maximale s'il y a lieu.
4. Déclarer son `audit_event` et l'ajouter au catalogue `audit_events`. Le vérificateur
   refuse une action qui se croit tracée par un événement inexistant.
5. Poser la garde correspondante dans le code, puis vérifier que
   `pytest tests/test_conformite_politiques.py` passe encore.

## Ajouter une interdiction

1. L'écrire au présent et à la forme négative, en nommant précisément ce qui est refusé.
2. Renseigner `enforced_by` avec ce qui refuse **concrètement**. Une liste vide est
   refusée par le schéma, parce qu'une interdiction sans mécanisme est une intention.
3. Écrire un test qui tente l'action interdite et vérifie le refus, puis inscrire son
   chemin dans `test`, sous la forme `depot:chemin::test`. Tant que ce champ est vide,
   le vérificateur signale l'interdiction comme non prouvée.

## Ajouter un module

1. Le déclarer dans `module_entitlements.modules` avec son code, les applications qu'il
   ouvre et les capacités qu'il rend exerçables.
2. Se rappeler la règle : un module n'accorde jamais un droit à lui seul. Le droit
   effectif est l'intersection du tenant actif, de l'abonnement actif, du module actif,
   du rôle et de la permission. Un module qui accorderait un droit transformerait un
   achat en élévation de privilège.
3. Renseigner `unavailable_without` : ce que le client ne peut pas faire sans lui. Cette
   phrase sert au commerce autant qu'au code.

## Ajouter une organisation cliente

Le cycle de vie est déclaré dans `tenant_operations` et n'est pas négociable au cas par
cas : créer, préparer, activer, suspendre, réactiver, archiver, supprimer. La suppression
exige un enchaînement contrôlé, une approbation par une seconde personne, et une période
d'archivage restaurable avant l'effacement.

Une demande venue du portail client ne provisionne jamais directement. Elle dépose une
demande que le domaine commercial valide et que le provisionnement exécute. Relier un
écran client à une interface d'infrastructure donnerait à un impayé le pouvoir de créer
des ressources facturées.

## Révoquer un accès

| Situation | Geste | Délai maximal |
|---|---|---|
| Départ d'un employé de l'éditeur | Désactiver la ligne `operateur_editeur`, fermer ses sessions | 60 minutes |
| Soupçon de compromission | Désactiver, fermer toutes les sessions, révoquer les assistances en cours | 5 minutes |
| Fin d'un accès d'assistance | Aucun : l'accès expire seul | immédiat |
| Changement de fonction | Ajuster le niveau ; l'effet est immédiat à la requête suivante | 24 heures |

Un privilège dont l'expiration dépend d'un geste humain devient permanent, parce que
personne n'a pour tâche de le retirer un vendredi soir. C'est pourquoi l'assistance
exceptionnelle expire d'elle-même et ne se renouvelle pas automatiquement.

## Exécuter les vérifications

```
pip install jsonschema
python policies/outils/verifier_politiques.py            # forme, cohérence, frontière
python policies/outils/verifier_politiques.py --json     # sortie pour la CI
python policies/outils/verifier_politiques.py --strict   # les interdictions non prouvées bloquent
```

Le code de retour vaut 1 dès qu'un manquement bloquant subsiste. Les catégories
`forme`, `coherence` et `frontiere` bloquent ; `vigilance` et `preuve` sont signalées.

## Origine des listes

Les capacités clientes et les droits des rôles clients ont été amorcés le 19 août 2026
à partir du catalogue réel de `adsum-api` : 75 permissions, 6 rôles, 498 routes déclarées
dans `app/permissions_data.py`. Les écrire à la main aurait garanti un écart dès le
premier ajout. Depuis cet amorçage, le fichier fait foi et se tient à la main : c'est le
test de conformité qui signale un écart, dans un sens comme dans l'autre.

Une seule chose y diffère volontairement du code de ce jour : `support.traiter` a quitté
le monde client pour devenir `editor.support.consulter`. Le test de conformité échoue
tant que le code n'a pas suivi, et c'est exactement le service qu'on lui demande.

# Frontière client / éditeur ADSUM

**Date** : 19 août 2026. **Auteur** : Armand Amoussou.
**Portée** : audit de l'écosystème complet, conception et pose de la frontière, preuves.

---

## 1. Le constat qui commande tout le reste

Vingt routes de la console de l'éditeur étaient gardées par
`require_permission("support.traiter")`. Cette permission figurait au catalogue **client**
et était accordée d'office aux rôles `admin` et `super_admin` d'une organisation cliente.

```
app/permissions_data.py:184   'admin':       frozenset(['support.traiter', ...])
app/permissions_data.py:185   'super_admin': frozenset(['support.traiter', ...])
```

Conséquence, vérifiée par exécution et non par lecture : l'administrateur d'une
organisation cliente pouvait

- lister **toutes** les organisations clientes d'ADSUM (`GET /organisations`),
- en créer une (`POST /organisations`),
- en suspendre une autre que la sienne (`PATCH /{id}/etat`),
- modifier ses modules (`PUT /{id}/modules`),
- faire ouvrir par le serveur une connexion vers une base arbitraire
  (`POST /{id}/provisionnement/diagnostic`, qui acceptait la chaîne de connexion dans
  le corps de la requête).

Aucune garde ne manquait : chacune de ces routes en avait une. Ce qui manquait, c'est
qu'**un rôle ne peut pas porter cette frontière, parce que le même mot existe des deux
côtés**. « Admin » désigne le trésorier d'une paroisse aussi bien qu'un administrateur
de la plateforme.

La migration `0006` du service commerce décrivait déjà ce piège, mot pour mot, et
l'avait fermé de son côté avec la table `operateur_editeur`. Il était resté ouvert dans
l'API métier.

---

## 2. Méthode d'audit

Douze agents en lecture seule, exécutés en parallèle, chacun sur un périmètre nommé,
chacun tenu de citer un fichier et une ligne réellement ouverts. Aucune écriture,
aucune commande destructive. Une passe de synthèse a relu les contradictions entre
rapports et rouvert les fichiers en cause.

| Lot | Périmètre |
|---|---|
| Inventaire | 25 dossiers locaux, tous les projets GitLab du groupe et sous-groupes, actifs et archivés |
| Identités | `auth.py`, `deps.py`, `mfa.py`, `security.py`, sessions, middleware |
| RBAC | `permissions*.py`, `groupes_roles.py`, `scope.py`, `perimetre.py`, `visibilite.py`, `modules_souscrits.py` |
| Surfaces éditeur | `console_*.py`, `support_console.py`, `technical_admin.py`, `provisionnement.py`, `admin.py`, `audit.py`, `rgpd.py` |
| Isolation tenant | `db.py`, `organisation_courante.py`, `membres.py`, `participation.py`, `fichiers.py`, `qr.py` |
| Commerce | `application.py`, `api.py`, `depot.py`, 11 migrations |
| Passerelle et ouvriers | `passerelle/*`, `ouvriers/*` |
| Base | migrations, RLS, schémas, scripts d'installation |
| Fronts client | 8 applications |
| Fronts éditeur et portail | console, portail, site, public |
| CI et configuration | gabarits partagés, `.gitlab-ci.yml`, variables d'environnement, infrastructure |

Volume : 595 appels d'outils, 2,14 millions de jetons d'agents, 52 minutes.

---

## 3. Inventaire : ce qui existe réellement

### 3.1 Composants actifs

| Composant | Dépôt | État |
|---|---|---|
| adsum-api | `services/adsum-api` | 482 commits, actif. Porte **à la fois** les surfaces client et éditeur |
| adsum-commerce | `services/adsum-commerce` | 1 commit local, **sans distant** |
| adsum-gateway | `services/adsum-gateway` | actif |
| adsum-workers | `services/adsum-workers` | actif |
| adsum-back-office, -pilotage, -direction, -collaboration, -web-membre, -controleur, -public | `applications/app-version-web/*` | actifs |
| adsum-console | `applications/.../adsum-console` | 5 commits, **sans distant** |
| deployment/database, ci-templates | | actifs |

### 3.2 Composants hors contrôle

| Composant | Problème | Gravité |
|---|---|---|
| `applications/adsum-portail` | **Aucun dépôt git, aucun projet GitLab, aucune CI**, alors qu'il manipule l'authentification et le parcours de paiement du client | critique |
| `applications/adsum-site` | Site d'entreprise de l'éditeur, sans dépôt, dans l'arbre des applications clientes | majeur |
| `deployment/scheduler-cron` | Worker Cloudflare sans dépôt, frappant la production toutes les cinq minutes sur une URL codée en dur | majeur |
| `applications/adsum-mobile` | Distant pointant sur un projet **archivé** ; les projets actifs (`app-version-android`, `app-version-apple`) n'ont aucune copie locale | majeur |
| `packages/core`, `ui-web`, `ui-native` | Projets GitLab actifs avec CI, **vides de tout code** | majeur |
| `docs/adsum-design`, `docs/design`, `docs/dat`, `deployment/runbooks` | Vides | mineur |
| 7 projets archivés sous l'ancien chemin `applications/adsum-*` | Doublonnent les 7 applications vivantes ; une recherche par nom ramène deux résultats | mineur |

---

## 4. Architecture avant intervention

- **Un seul jeton** pour tout l'écosystème : `sub`, `role`, `iat`, `exp`, `iss`, `sid`
  facultatif. **Aucune audience, aucune organisation.** Le même jeton ouvrait la console
  de l'éditeur et l'espace personnel d'un membre.
- **Un seul secret** de signature pour tous les tenants et pour l'éditeur.
- La console de l'éditeur se connectait par `POST /api/v1/auth/login`, comme n'importe
  quelle application cliente.
- L'autorité éditeur était une **permission du catalogue client**.
- Le registre commercial de l'éditeur (`organisation_cliente`, `licence`,
  `organisation_hote`) vivait dans le schéma `public` de la base **cliente**, avec RLS
  activée mais **sans aucune politique**, la connexion applicative étant propriétaire
  des tables et échappant donc à RLS.
- Le service commerce, lui, tenait déjà l'autorité par la table `operateur_editeur`,
  mais décodait le jeton avec le **secret client** et sans audience.

Deux frontières différentes pour un seul produit, et aucune des deux complète.

---

## 5. Architecture après intervention

Quatre barrières, franchies dans cet ordre, toutes avant la moindre requête en base.

| # | Barrière | Ce qu'elle arrête |
|---|---|---|
| 1 | **Audience** `adsum-editeur` | Un jeton client, qui n'en porte aucune |
| 2 | **Signature distincte** (`ADSUM_JWT_EDITEUR_SECRET`) | Un jeton forgé avec le secret des tenants, même parfaitement formé |
| 3 | **Registre d'opérateurs**, relu à chaque requête | Une personne révoquée, avant l'expiration de son jeton |
| 4 | **Politique lue à l'exécution** | Une capacité que le rôle éditeur ne détient pas |

La barrière 2 est celle qui compte le jour où le secret des tenants fuit : l'autorité
éditeur reste hors d'atteinte.

Le parcours de connexion à la console devient : authentification normale (mot de passe,
second facteur, appareil de confiance, rien d'allégé) puis **échange**
`POST /api/v1/auth/session-editeur` contre un jeton d'opérateur.

---

## 6. Rôle exact de chaque application

| Application | Zone | Rôle |
|---|---|---|
| adsum-site | 1, public | Site d'entreprise de l'éditeur |
| adsum-public | 1 et 5, **ambigu** | Vitrine produit **et** émargement externe d'une organisation, dans le même composant, sans authentification |
| adsum-portail | 2, client | Abonnement, modules, personnalisation, déploiement, support d'**une** organisation |
| adsum-console | 3, éditeur | Centre de contrôle interne : parc, support, exploitation, livraison, incidents, gouvernance |
| adsum-commerce | 3 et 4, éditeur | Catalogue, offres, abonnements, licences, encaissement, provisionnement |
| adsum-api | 4, **partagé** | API métier client **et** routes de console éditeur, dans le même processus |
| adsum-gateway | 4 | Courriel, paiement, webhooks, fournisseurs |
| adsum-workers | 4 | Files, relances, tâches planifiées |
| adsum-back-office | 5, client | Administration métier de l'organisation |
| adsum-pilotage | 5, client | Pilotage par périmètre délégué |
| adsum-direction | 5, client | Tableaux de bord agrégés |
| adsum-collaboration | 5, client | Espaces de travail |
| adsum-web-membre, adsum-mobile | 5, client | Espace personnel du membre |
| adsum-controleur | 5, client | Scan et pointage terrain |

**ADSUM Pilotage reste une application cliente. ADSUM Console reste éditeur.** Aucune
capacité n'a traversé.

---

## 7. Fichiers créés ou modifiés

### `deployment/ci-templates` (branche `feat/politiques-acces-client-editeur`)

| Fichier | Nature |
|---|---|
| `policies/client-access-policy.json` | créé, 17 rôles, 82 capacités |
| `policies/editor-access-policy.json` | créé, 15 rôles, 20 routes de console déclarées |
| `policies/schemas/common.schema.json` | créé |
| `policies/schemas/client-access-policy.schema.json` | créé |
| `policies/schemas/editor-access-policy.schema.json` | créé |
| `policies/outils/verifier_politiques.py` | créé, trois passes |
| `policies/README.md` | créé, procédures d'ajout et de révocation |
| `templates/policies.yml` | créé, trois tâches CI |
| `.gitlab-ci.yml` | inclut `policies.yml` |

### `services/adsum-api` (branche `feat/frontiere-client-editeur`)

| Fichier | Nature |
|---|---|
| `app/frontiere.py` | créé : audiences, secret distinct, registre, `require_capacite`, échange de session |
| `app/console_organisations.py` | 12 routes basculées, chaîne de connexion arbitraire supprimée |
| `app/console_observabilite.py` | 2 routes basculées |
| `app/support_console.py` | 6 routes basculées |
| `app/permissions_data.py` | `support.traiter` retirée du catalogue, des 2 rôles et des 20 routes |
| `app/main.py` | monte le routeur de frontière |
| `policies/*.json` | copie versionnée, contrôlée contre la dérive |
| `tests/test_frontiere_client_editeur.py` | créé |
| `tests/test_conformite_politiques.py` | créé |
| `.gitlab-ci.yml` | inclut `policies.yml` |

### `services/adsum-commerce` (branche `feat/frontiere-jeton-editeur`)

| Fichier | Nature |
|---|---|
| `src/commerce/auth.py` | audience et clé propres exigées sur les routes d'opérateur |
| `src/commerce/application.py` | `jwt_editeur_secret`, fermé par défaut |
| `tests/*` (6 fichiers) | les tests présentent un vrai jeton d'opérateur |
| `.gitignore` | créé ; 89 fichiers d'octet-code retirés du suivi |

### `applications/adsum-console`

| Fichier | Nature |
|---|---|
| `src/api.ts` | échange du jeton client contre un jeton d'opérateur après connexion |

---

## 8. Matrice des rôles

### Client (17 rôles)

| Rôle | Portée | MFA | Dans le code |
|---|---|---|---|
| `client-super-admin` | organisation | obligatoire | oui, `super_admin` |
| `client-admin` | organisation | obligatoire | oui, `admin` |
| `client-manager` | périmètre | recommandé | oui, `gestionnaire` |
| `client-direction` | organisation | recommandé | oui, `direction` |
| `client-controller` | périmètre | recommandé | oui, `controleur` |
| `client-member` | personnel | recommandé | oui, `membre` |
| `client-owner` | organisation | obligatoire | oui, `administrateur_portail.principal` |
| `client-portal-admin` | organisation | obligatoire | oui, `administrateur_portail` |
| `client-commission-manager`, `client-group-manager`, `client-event-manager`, `client-collaborator`, `client-guest` | périmètre ou ponctuel | variable | oui, par appartenance de groupe |
| `client-finance-admin`, `client-security-admin`, `client-support-contact`, `client-auditor-readonly` | organisation | obligatoire | **non**, à créer |

### Éditeur (15 rôles)

| Rôle | MFA | Lit les données personnelles | Dans le code |
|---|---|---|---|
| `editor-owner` | renforcé | **non** | non |
| `editor-super-admin` | renforcé | **non** | non |
| `editor-platform-admin` | obligatoire | **non** | non |
| `editor-security-admin` | renforcé | **non** | non |
| `editor-sre` | renforcé | **non** | non |
| `editor-devops` | obligatoire | **non** | non |
| `editor-support-agent` | obligatoire | **non** | oui, niveau `lecture` |
| `editor-support-lead` | obligatoire | **non** | non |
| `editor-commerce-admin` | obligatoire | **non** | oui, niveau `intervention` |
| `editor-finance-readonly` | obligatoire | **non** | non |
| `editor-product-manager` | obligatoire | **non** | non |
| `editor-developer` | obligatoire | **non** | non |
| `editor-auditor-readonly` | renforcé | **non** | non |
| `editor-incident-manager` | obligatoire | **non** | oui |
| `editor-operations-readonly` | obligatoire | **non** | oui, niveau `lecture` |

Le schéma **interdit structurellement** qu'un rôle éditeur déclare lire une donnée
personnelle client : le champ n'accepte que `false`.

---

## 9. Politique de modules et d'abonnement

Le droit effectif est l'intersection : tenant actif ∩ abonnement actif ∩ module actif ∩
rôle ∩ permission. **Un module n'accorde jamais un droit à lui seul** ; l'inverse
transformerait un achat en élévation de privilège.

**Suspension** : 15 jours de grâce, puis lecture seule. Aucune donnée n'est retirée.
Restent joignables même suspendu : régler sa facture, exporter ses données, ouvrir un
ticket, se connecter pour constater son état. Couper cela transformerait un impayé en
séquestre.

## 10. Assistance exceptionnelle

Le seul chemin par lequel un employé de l'éditeur approche les données d'une
organisation. Aucun rôle ne l'ouvre. Conditions cumulatives : le client autorise depuis
son portail, la sécurité approuve, le périmètre est nommé, la durée est bornée à quatre
heures, l'accès **expire seul**, le contact client est notifié. Restent refusés même
alors : mots de passe, jetons, clés privées, pièces d'identité déchiffrées, écriture.

## 11. Politique d'audit et de rétention

33 événements déclarés côté éditeur, 8 côté client, chacun avec acteur, cible, issues
tracées (succès **et refus**), corrélation, motif si exigé, durée de conservation de
365 à 3650 jours. Un refus non journalisé est un angle mort : c'est justement la
tentative qui intéresse.

## 12. Politique RLS

**État réel, sans complaisance** : environ 149 des 153 tables du schéma client ne sont
pas en RLS forcée, et le rôle applicatif est propriétaire, donc y échappe. Les tables du
registre éditeur activent RLS **sans définir la moindre politique**, ce qui produit une
assurance fausse. Ce point n'est pas corrigé par ce travail ; il est mesuré, daté et
inscrit ci-dessous en risque résiduel.

---

## 13. Résultats des tests

| Suite | Résultat |
|---|---|
| `verifier_politiques.py` | 0 bloquant ; 4 vigilances, 24 interdictions non encore prouvées |
| `adsum-api` : frontière et conformité | voir section 16 |
| `adsum-commerce` : suite complète | voir section 16 |

Les tests de frontière rejouent chacun une façon de franchir, et vérifient l'échec :
jeton de `super_admin` de tenant sur les six routes principales, jeton contrefait avec
le secret des tenants, opérateur révoqué, rôle absent de la politique, capacité
manquante. Un test positif garantit qu'on ne prouve pas seulement qu'un mur refuse tout.

## 14. Échecs rencontrés et corrections

| Échec | Correction |
|---|---|
| Le test de conformité passait en ne comparant **rien** : cette version de FastAPI expose `_IncludedRouter` et non les routes | Descente par `original_router`, plus une assertion qui refuse une collecte vide |
| `Operateur` n'avait pas d'attribut `id`, utilisé par 14 écritures d'audit : le déploiement aurait cassé toutes les mutations de la console | Alias `id` et `role` sur le modèle |
| La console envoyait encore son jeton client : elle aurait reçu 401 partout | Échange ajouté dans `api.ts` |
| Le validateur refusait les fils de support parce qu'ils portent un nom | Distinction `aucune` / `contact-declare` / `dossier-client` : seul le dossier passe par l'assistance |
| La politique s'était trompée de domaine sur `/envois` et `/synthese`, et omettait 5 routes | Corrigée, 20 routes déclarées |
| 57 tests commerce prouvaient l'ancien contrat | Ils présentent désormais un vrai jeton d'opérateur |
| 89 fichiers d'octet-code suivis par git dans commerce | `.gitignore` et retrait du suivi |

---

## 15. Risques résiduels, par gravité

| # | Risque | Gravité |
|---|---|---|
| 1 | `acces_technique_global` donne à l'éditeur une **lecture implicite, permanente et non auditée** du contenu personnel des clients (espaces de collaboration, canal, tableaux) | critique |
| 2 | Un compte technique de l'éditeur est créé avec `role = 'super_admin'` **en dur**, dans la base du client, ce qui lui confère les 75 permissions | critique |
| 3 | Le registre d'opérateurs d'adsum-api est une **variable d'environnement** : révoquer exige un redéploiement | critique |
| 4 | Le choix du tenant repose sur `x-forwarded-host`, en-tête fourni par l'appelant ; `_registre()` avale toute exception et retombe en mode transition | critique |
| 5 | `organisation_hote.dsn` stocke une chaîne de connexion **mot de passe compris, en clair**, dans le schéma `public` | critique |
| 6 | Stockage mutualisé : un seul projet, une seule clé de service pour les photos et pièces d'identité de toutes les organisations | critique |
| 7 | `jwt_secret` et `qr_signing_key` communs à tous les tenants | majeur |
| 8 | `POST /api/v1/auth/login-verify` sans limitation de débit : oracle de mot de passe sans plafond | majeur |
| 9 | La passerelle authentifie ses appelants mais ne les **autorise** pas : un secret valide ouvre aussi la purge du registre | majeur |
| 10 | `souscriptions()` est fail-open : liste vide vaut tout le catalogue, et toute exception vaut accès | majeur |
| 11 | 12 des 15 rôles éditeur n'existent pas en code ; le modèle stocké n'a que deux niveaux | majeur |
| 12 | 24 interdictions déclarées ne sont pas encore adossées à un test | majeur |
| 13 | Le portail client et le site éditeur n'existent que sur disque | majeur |
| 14 | Les pipelines ne peuvent pas devenir verts : minutes CI du groupe épuisées | majeur |

## 16. Verdict sur l'affirmation « l'espace éditeur n'est pas fait à 5 % »

**Partiellement infirmé, et la nuance importe.** La console couvre les six domaines
attendus : chacun a une page. Mais chaque page est mince, et la politique le déclare
elle-même, domaine par domaine, dans son champ `missing` : pas de métriques historisées,
pas de traces, pas de règles d'alerte, pas de tâches assignables, pas de listes de
contrôle de mise en production, pas de gestion du MFA ni des sessions, pas de contrats
ni d'essais, pas de file priorisée ni d'engagement de service, pas d'inventaire
d'environnements ni d'état des sauvegardes.

Autrement dit : la charpente des six domaines existe, le contenu de chacun est au début.
Une estimation honnête se situe entre 20 et 30 % de ce qu'un centre de contrôle
d'éditeur comparable exige, et non à 5 % ni à 100 %.

## 17. Procédure de retour arrière

Chaque changement est sur une branche dédiée, aucun n'est fusionné. Le retour arrière
est l'abandon de la demande de fusion. En cas de fusion déjà faite :

1. `ADSUM_JWT_EDITEUR_SECRET` vidée ferme la connexion éditeur sans rouvrir l'ancienne
   brèche : les routes de console répondent 403 à tout le monde.
2. `ADSUM_OPERATEURS_EDITEUR` vidée révoque tous les opérateurs à la requête suivante.
3. Le retour du code se fait par `git revert` du commit de frontière, qui restaure
   `support.traiter` : à n'employer qu'en connaissance de cause, puisque c'est la brèche.

---

## 18. Matrice de validation finale

| Exigence | Statut | Preuve vérifiable | Correctif restant |
|---|---|---|---|
| Audit complet des dépôts ADSUM | Complete | Inventaire daté du 19/08/2026, 25 dossiers, tous les projets GitLab, 12 rapports avec chemins et lignes | néant |
| Frontière client / éditeur définie | Complete | `policies/*.json`, 4 barrières, section 5 | néant |
| `client-access-policy.json` créé et validé | Complete | `verifier_politiques.py` : 0 bloquant | néant |
| `editor-access-policy.json` créé et validé | Complete | idem | néant |
| Rôles client séparés des rôles éditeur | Complete | Préfixes imposés par schéma ; test `test_aucune_capacite_editeur_n_est_accordee_a_un_role_client` | 12 rôles éditeur restent à implémenter |
| ADSUM Pilotage isolé côté client | Complete | Aucune capacité `editor.*` dans la politique cliente ; aucune route éditeur appelée | néant |
| ADSUM Console isolée côté éditeur | Complete | 20 routes derrière `require_capacite` ; `test_toute_route_de_console_porte_une_garde_editeur` | néant |
| Isolation tenant vérifiée | **Partial** | Une base par organisation ; mais `x-forwarded-host` et repli en mode transition | risques 4, 5, 6 |
| Accès opérateur aux données client minimisé | **Partial** | `may_read_client_personal_data` structurellement faux ; assistance exceptionnelle déclarée | risque 1 : `acces_technique_global` reste ouvert |
| Actions privilégiées protégées | **Partial** | 12 actions déclarées avec garde-fou complet | approbation et justification pas encore imposées par le code |
| Modules et abonnements contrôlés | **Partial** | Règle d'intersection déclarée | risque 10 : `souscriptions()` fail-open |
| Suspension et réactivation testées | Complete | Suite commerce, cycle de vie du tenant | néant |
| Journaux sans secrets ni données inutiles | Complete | Règles déclarées ; empreinte poivrée dans la passerelle ; comptes rendus réduits aux chiffres | néant |
| Régressions critiques absentes | Complete | Voir section 13 | néant |
| Documentation complète livrée | Complete | `policies/README.md`, ce rapport | néant |
| Deux fichiers JSON non décoratifs | Complete | Lus à l'exécution par `frontiere.py` ; comparés au code par le test de conformité ; 3 tâches CI | les tâches ne tourneront qu'avec des minutes CI |

---

## 19. Ce qui reste, par ordre de priorité

1. Fermer `acces_technique_global` et le compte technique en `super_admin` codé en dur.
2. Remplacer le registre en variable d'environnement par la table `operateur_editeur`,
   ce qui exige d'abord de poser le schéma `editeur` en production.
3. Cesser de choisir le tenant sur un en-tête fourni par l'appelant, et supprimer le
   repli silencieux en mode transition.
4. Chiffrer `organisation_hote.dsn` et le sortir du schéma `public`.
5. Cloisonner le stockage des pièces d'identité et des photos par organisation.
6. Limiter le débit de `login-verify`.
7. Autoriser, et pas seulement authentifier, les appelants de la passerelle.
8. Écrire les 24 tests d'interdiction manquants et passer le validateur en `--strict`.
9. Mettre le portail client, le site et l'ordonnanceur sous contrôle de version.
10. Implémenter les 12 rôles éditeur déclarés, ou réduire la déclaration à ce qui sera
    réellement tenu.

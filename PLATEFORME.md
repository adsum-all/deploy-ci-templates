# Plateforme ADSUM : dépôts, branches, pipelines, déploiements

Ce dépôt est le point unique de la chaîne d'intégration et de livraison ADSUM.
Une trentaine de projets consomment ses gabarits. Une erreur ici ne se voit pas ici,
elle se voit chez eux.

## 1. Cartographie

Le groupe `sr-media-ai` héberge plusieurs produits. ADSUM occupe le sous-groupe
`sr-media-ai/adsum` et compte **28 projets actifs** et 7 archivés.

| Zone | Sous-groupe | Projets | Audience |
|---|---|---|---|
| Applications web | `applications/app-version-web` | back-office, collaboration, console, controleur, direction, pilotage, public, web-membre | client, sauf console |
| Applications mobiles | `applications/app-version-android`, `app-version-apple` | adsum-mobile, adsum-mobile-ios | client |
| Services | `services` | adsum-api, adsum-commerce, adsum-gateway, adsum-workers | transverse et éditeur |
| Paquets partagés | `packages` | core, qr, tokens, ui-native, ui-web | transverse |
| Plateforme | `deployment` | ci-templates, database, infrastructure, runbooks | transverse |
| Documentation | `docs` | adr, adsum-design, dat, design, onboarding | transverse |

**Séparation client / éditeur.** Elle est aujourd'hui portée par le code et par les
deux politiques d'accès (`policies/`), pas par l'arborescence : `adsum-console` est
une application d'éditeur rangée avec les applications clientes, et `adsum-api` porte
les deux mondes dans un même processus. Déplacer la console dans un sous-groupe
`applications/editeur` est souhaitable et demande un plan de migration : URL de
clone, inclusions CI, déploiement Cloudflare, documentation. Ce déplacement n'est pas
fait ; la frontière, elle, l'est, et elle tient dans le jeton avant de tenir dans le
rangement.

## 2. Branches

| Branche | Rôle | Protégée |
|---|---|---|
| `main` | référence, source des déploiements | oui, dans les 28 projets |
| `feature/*`, `fix/*`, `ci/*`, `docs/*`, `security/*` | travail temporaire | non |

Toute évolution passe par une branche temporaire et une demande de fusion. La
suppression de la branche source après fusion est **déjà activée sur les 28 projets**
(`remove_source_branch_after_merge`), et chaque demande ouverte porte le drapeau.

143 branches déjà fusionnées dans `main` subsistent, dont 39 sur `adsum-api` et 36
sur le back-office. Elles datent d'avant l'activation. Le relevé est dans
`docs/plan-nettoyage-branches.md` : chacune est supprimable sans perte, puisque ses
commits sont dans `main`, mais un balayage rétroactif se décide, il ne se subit pas.

## 3. Pipelines

### Gabarits disponibles

| Gabarit | Pour | Contenu |
|---|---|---|
| `base.yml` | tous | étapes, règles de déclenchement, audit de Constitution |
| `security.yml` | tous | sept contrôles DevSecOps |
| `stack-web.yml` | applications web | valide, lint, tests, build |
| `stack-python-service.yml` | services Python | valide, ruff, types, pytest avec couverture |
| `stack-docs.yml` | documentation | liens internes, markdown |
| `policies.yml` | frontière | validation des politiques, conformité, dérive |
| `docker.yml`, `terraform.yml`, `deploy-*.yml` | selon besoin | historique, conservés |

Un dépôt déclare sa pile en cinq lignes :

```yaml
include:
  - project: 'sr-media-ai/adsum/deployment/ci-templates'
    ref: main
    file: '/templates/stack-web.yml'
```

### Étapes

`audit`, `validate`, `quality`, `security`, `test`, `build`, `package`, `deploy`,
`deploy-review`, `deploy-staging`, `deploy-production`.

L'étape `deploy` est historique et conservée : trois gabarits publiés la citent, et
la retirer ferait échouer le chargement de la configuration chez tous leurs
consommateurs.

### Politique de sévérité

`CRITICAL` et `HIGH` arrêtent le pipeline. `MEDIUM` et `LOW` sont rapportées. Faire
bloquer les moyennes est la façon dont un garde-fou finit contourné puis ignoré.

Une exception se déclare dans `docs/security/exceptions.md` avec une date de fin. La
tâche `security:exceptions` refuse une exception périmée : elle se renouvelle
consciemment ou la cause se corrige.

## 4. Vérifier sans consommer de minutes

Deux contrôles tournent hors CI et attrapent les pannes les plus opaques.

```
python outils/verifier_gabarits.py          # syntaxe, étapes, héritages, pièges YAML
python policies/outils/verifier_politiques.py   # forme, cohérence, frontière
```

L'API de validation de GitLab se prononce sur la configuration **assemblée**, sans
lancer de pipeline :

```
POST /projects/:id/ci/lint  {"content": "...", "ref": "<branche>", "dry_run": true}
```

C'est ainsi qu'ont été trouvés deux défauts qu'aucun contrôle local ne voyait : un
`: ` dans un scalaire non quoté, qui fait lire une commande comme un dictionnaire, et
un gabarit tirant son socle de `main` alors que la branche en proposait un autre.

## 5. Déploiements

| Cible | Mécanisme | Source autorisée |
|---|---|---|
| Applications web | Cloudflare Pages, `wrangler pages deploy dist` | `main` |
| Services | Vercel, `vercel deploy --prod` | `main` |
| Base | Alembic via le pooler | `main`, migration relue |

Les déploiements ne passent pas encore par la CI : ils sont lancés à la main avec les
jetons du poste. C'est le principal écart restant, et il se referme quand les
pipelines peuvent tourner.

## 6. Créer un nouveau dépôt

1. Le placer dans le sous-groupe correspondant à son audience.
2. Y écrire un `.gitlab-ci.yml` de cinq lignes incluant le gabarit de sa pile.
3. Protéger `main`.
4. Vérifier que `remove_source_branch_after_merge` est actif.
5. Déclarer son rôle dans la section 1 de ce document.

## 7. Avant une mise en production

- La demande de fusion est relue et son pipeline est vert.
- Les contrôles de sécurité ne laissent aucune vulnérabilité `CRITICAL` ou `HIGH`.
- Les migrations de base sont réversibles ou leur irréversibilité est assumée par écrit.
- Le retour arrière est décrit et réalisable.
- Les variables et secrets requis existent dans l'environnement cible.

## 8. Ce qui n'est pas fait

Écrit ici plutôt que passé sous silence, parce qu'un document de plateforme qui
n'énumère que ses réussites ne sert à personne.

| Écart | Conséquence | Ce qu'il faut |
|---|---|---|
| Minutes de calcul partagées épuisées depuis le 9 août 2026 | Aucun pipeline ne peut aboutir | Rien, ou des minutes, ou un runner. Voir ci-dessous. |
| Déploiements hors CI | Pas de traçabilité entre un commit et ce qui tourne | Des pipelines qui tournent, puis des tâches de déploiement |
| `only_allow_merge_if_pipeline_succeeds` désactivé sur 93 projets | Une fusion peut passer sans vérification | À activer **après** que les pipelines puissent aboutir, sinon plus rien ne fusionne |
| Console éditeur rangée avec les applications clientes | Confusion de lecture, pas de faille | Migration de sous-groupe avec mise à jour des références |
| `adsum-commerce` vide sur GitLab | Le service le plus commercial n'est pas versionné | Rattacher le dépôt local à son projet |
| `adsum-portail`, `adsum-site`, `scheduler-cron` sans projet GitLab | Versionnés en local depuis le 20 août, mais sans distant | Créer les trois projets et rattacher |
| Environnements GitLab non déclarés | Pas de protection ni d'historique de déploiement | Déclarer staging et production une fois la CI opérationnelle |

### Le quota, daté

Le dernier pipeline vert d'ADSUM date du **9 août 2026**. Le même jour, 62 pipelines
sont tombés : c'est l'épuisement des minutes partagées du groupe. Tous les échecs
depuis portent `ci_quota_exceeded`, avec une durée nulle, donc sans exécuter une
ligne.

Les minutes de l'offre gratuite se rechargent le premier de chaque mois. **La chaîne
redevient donc opérationnelle d'elle-même le 1er septembre 2026**, sans achat ni
runner. Acheter des minutes ou rattacher un runner autohébergé avance simplement
cette date.

Ce constat change la nature du blocage : il est daté et borné, pas structurel. Le
script `outils/armer_portes_de_fusion.py` refuse d'armer la porte de fusion tant
qu'aucun pipeline vert de moins de trente jours n'existe, précisément pour qu'on ne
verrouille pas les vingt-huit dépôts pendant cette fenêtre.

## 9. Matrice de maturité CI/CD par dépôt

Relevé du 19 août 2026. « Sécurité » signifie que le dépôt consomme la
chaîne DevSecOps : secrets, SAST OWASP, dépendances, licences, Trivy, IaC.

| Dépôt | Audience | Gabarit | Sécurité | Écart |
|---|---|---|---|---|
| `applications/app-version-android/adsum-mobile` | client | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `applications/app-version-apple/adsum-mobile-ios` | client | aucun | non | demande de fusion ouverte en brouillon |
| `applications/app-version-web/adsum-back-office` | client | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `applications/app-version-web/adsum-collaboration` | client | deploy-web.yml, node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `applications/app-version-web/adsum-console` | éditeur | aucun | non | demande de fusion ouverte en brouillon |
| `applications/app-version-web/adsum-controleur` | client | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `applications/app-version-web/adsum-direction` | client | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `applications/app-version-web/adsum-pilotage` | client | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `applications/app-version-web/adsum-public` | client | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `applications/app-version-web/adsum-web-membre` | client | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `deployment/ci-templates` | plateforme | base.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `deployment/database` | plateforme | deploy-migrate.yml, python.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `deployment/infrastructure` | plateforme | terraform.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `deployment/runbooks` | plateforme | base.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `docs/adr` | documentation | base.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `docs/adsum-design` | documentation | aucun | non | demande de fusion ouverte en brouillon |
| `docs/dat` | documentation | base.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `docs/design` | documentation | base.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `docs/onboarding` | documentation | base.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `packages/core` | transverse | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `packages/qr` | transverse | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `packages/tokens` | transverse | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `packages/ui-native` | transverse | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `packages/ui-web` | transverse | node.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `services/adsum-api` | transverse | deploy-gcp.yml, deploy-web.yml, docker.yml, python-ci.yml, security.yml | oui | aucun |
| `services/adsum-commerce` | éditeur | aucun | non | demande de fusion ouverte en brouillon |
| `services/adsum-gateway` | transverse | python.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |
| `services/adsum-workers` | transverse | python.yml | héritée | hérite de la chaîne dès que ci-templates !6 est fusionnée |

Les gabarits `node.yml`, `python.yml` et `terraform.yml` tirent désormais
`security.yml` eux-mêmes. Les vingt quatre dépôts qui les consomment
héritent donc de la chaîne sans aucune modification chez eux.

**Validation côté serveur**, sans consommer de minute de CI :

| Gabarit | Validé contre | Tâches assemblées |
|---|---|---|
| `node.yml` | adsum-back-office | 14 |
| `python.yml` | adsum-gateway | 13 |
| `terraform.yml` | infrastructure | 12 |
| `stack-web.yml` | adsum-console | 16 |
| `stack-python-service.yml` | adsum-api | 16 |
| `stack-docs.yml` | adsum-design | 13 |


## 10. Dépôts mis sous contrôle de version le 20 août 2026

Trois dossiers actifs n'étaient dans aucun dépôt git. Ils le sont désormais, en local,
avec un `.gitignore` et une CI déclarée. Il leur manque un projet GitLab.

| Dossier | Ce qu'il porte | Pourquoi c'était grave |
|---|---|---|
| `applications/adsum-portail` | Connexion et parcours de paiement d'une organisation cliente | Une régression ou une exfiltration n'aurait été ni traçable ni annulable |
| `applications/adsum-site` | Site d'entreprise de l'éditeur, sept pages publiques | Du texte public livré sans historique est du texte dont personne ne peut prouver la relecture |
| `deployment/scheduler-cron` | Worker Cloudflare appelant la production toutes les cinq minutes | Personne ne pouvait le relire, le réviser ni le restaurer |

### Un échec silencieux corrigé au passage

L'ordonnanceur n'examinait jamais la réponse de son appel. Un `fetch` qui rend 401 est
une promesse tenue, pas une erreur : le jour où `CRON_SECRET` tourne, l'appel
continuait de partir, le journal écrivait « Unauthorized », et la diffusion des
sondages s'arrêtait sans que rien ne le signale. Le statut est désormais vérifié,
l'erreur est journalisée au niveau erreur et relancée pour que Cloudflare compte
l'exécution en échec. Sans cette dernière partie, le tableau de bord affiche cent pour
cent de réussite pendant que rien ne part.

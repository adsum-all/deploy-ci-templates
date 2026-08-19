# Plan de nettoyage des branches fusionnées

Relevé du 19 août 2026. Chaque branche listée est **déjà fusionnée dans la
branche par défaut**, non protégée, et citée par aucune demande de fusion
ouverte. Ses commits sont donc dans `main` : la supprimer ne perd aucun
travail.
**143 branches** sur 10 projets.


Ce balayage n'est pas exécuté d'office. La suppression automatique après
fusion est active sur les 28 projets, ce qui empêche toute nouvelle
accumulation ; ces branches-ci datent d'avant. Les retirer se décide.

Pour en supprimer un lot, depuis un clone à jour :

```
git push origin --delete <branche> [<branche>...]
```

## services/adsum-api (39)

- `feat/activites-onglets-centre-notifications`
- `feat/bandeau-prioritaire-informations`
- `feat/centre-diffusion-communication`
- `feat/emojis-riches-signature-perms`
- `feat/hebdo-heure-envoi-configurable`
- `feat/identite-dates-institutionnelles`
- `feat/info-diffusion-duree-canaux-sondage-badge`
- `feat/informations-diffusion-email`
- `feat/informations-enrichies`
- `feat/membre-cheminement`
- `feat/module-informations`
- `feat/planification-activites-berger-fenetre`
- `feat/retention-archivage-informations-chrono`
- `feat/tts-voix-ciblage-fin`
- `feature/direction-analytique`
- `fix/berger-declaration`
- `fix/calendrier-extras`
- `fix/calendrier-institutionnel`
- `fix/collab-audit-backend`
- `fix/collab-bugs-compteur-stats`
- `fix/collab-corbeille-archives-securite`
- `fix/collab-modeles-globaux`
- `fix/collab-modeles-perso`
- `fix/collab-securite-isolation`
- `fix/direction-taxonomie`
- `fix/hierarchie-fonction-based`
- `fix/informations-entete-edition`
- `fix/informations-export-relance`
- `fix/informations-review`
- `fix/inscription-champs-exhaustifs`
- `fix/organigramme-blocs`
- `fix/organigramme-hierarchie`
- `fix/organigramme-modelisation`
- `fix/organigramme-patriarches`
- `fix/organigramme-statistiques`
- `fix/organigramme-toutes-commissions`
- `fix/prod-hardening-cors-targeting-prefs`
- `fix/taxonomie-attributions`
- `fix/vice-fonctions-interim`

## applications/app-version-web/adsum-back-office (36)

- `feat/centre-diffusion-communication`
- `feat/emojis-riches-signature-perms`
- `feat/evenement-lecture-pieces`
- `feat/formulaires-listes-controlees`
- `feat/hebdo-heure-envoi-configurable`
- `feat/identite-dates-institutionnelles`
- `feat/info-diffusion-duree-canaux-sondage-badge`
- `feat/informations-enrichies`
- `feat/module-informations`
- `feat/planification-activites-berger-fenetre`
- `feat/retention-archivage-informations-chrono`
- `feat/tts-voix-ciblage-fin`
- `fix/activite-edition-jour-p8`
- `fix/berger-declaration`
- `fix/bo-acces-groupes-onglets`
- `fix/bo-gouvernance-interim`
- `fix/bo-identite-calendrier`
- `fix/bo-institutionnel-extras`
- `fix/bo-organigramme-fonction-dominante`
- `fix/bo-permissions-refresh-stale-menu`
- `fix/bo-profil-page-theme`
- `fix/dashboard-presence-fields`
- `fix/governance-ux-hardening`
- `fix/informations-editeur-entete`
- `fix/informations-review`
- `fix/organigramme-blocs`
- `fix/organigramme-edition-liens`
- `fix/organigramme-hierarchie`
- `fix/organigramme-liens-polish`
- `fix/organigramme-modelisation`
- `fix/organigramme-patriarches`
- `fix/organigramme-search-center-perf`
- `fix/organigramme-statistiques`
- `fix/organigramme-toutes-commissions`
- `fix/organigramme-undo-move`
- `fix/taxonomie-attributions`

## applications/app-version-web/adsum-web-membre (28)

- `feat/activites-onglets-centre-notifications`
- `feat/bandeau-prioritaire-informations`
- `feat/collab-lot5-filtres`
- `feat/declaration-participation-trois-questions`
- `feat/emojis-riches-signature-perms`
- `feat/formulaires-listes-controlees`
- `feat/informations-enrichies`
- `feat/membre-cheminement`
- `feat/membre-cloche-notifications`
- `feat/membre-hierarchie-mobile`
- `feat/module-informations`
- `feat/photo-recadrage-rond`
- `feat/planification-activites-berger-fenetre`
- `feat/retention-archivage-informations-chrono`
- `feat/tts-voix-ciblage-fin`
- `fix/banniere-entete-priorites`
- `fix/berger-declaration`
- `fix/informations-review`
- `fix/membre-appui-suppleance-offline`
- `fix/membre-dates-reference`
- `fix/membre-dates-reference-ics`
- `fix/membre-hierarchie-organigramme`
- `fix/membre-photo-dezoom`
- `fix/membre-photo-fond`
- `fix/membre-refresh-garde-onglet`
- `fix/mobile-resilience`
- `fix/taxonomie-attributions`
- `fix/voix-homme-tts`

## deployment/database (20)

- `feat/activites-onglets-centre-notifications`
- `feat/db-groupes-standard-doc-0170`
- `feat/emojis-riches-signature-perms`
- `feat/identite-dates-institutionnelles`
- `feat/info-diffusion-duree-canaux-sondage-badge`
- `feat/membre-cheminement`
- `feat/module-informations`
- `feat/retention-archivage-informations-chrono`
- `feat/tts-voix-ciblage-fin`
- `fix/berger-declaration`
- `fix/calendrier-rls-maj-par-0166`
- `fix/cible-types-favori-prefs`
- `fix/collab-modele-global-0163`
- `fix/collab-modele-perso-migration`
- `fix/identite-calendrier-institutionnel-0165`
- `fix/item-assigne-fk`
- `fix/organigramme-modelisation`
- `fix/reference-version-rappel-0167`
- `fix/taxonomie-attributions`
- `fix/vice-fonctions-interim-0164`

## applications/app-version-web/adsum-collaboration (9)

- `feat/collab-planificateur-organigramme`
- `fix/activite-edition-jour`
- `fix/collab-audit-frontend`
- `fix/collab-centrage-canal-corbeille-audit`
- `fix/collab-etats-mobile-a11y`
- `fix/collab-grille-routage-corbeille-clarte`
- `fix/collab-informations-profil-contraste`
- `fix/collab-modeles-globaux-front`
- `fix/write-gating-personal-favori`

## applications/app-version-web/adsum-direction (4)

- `feat/identite-organisation`
- `feature/direction-analytique`
- `fix/direction-audit-navigateur`
- `integration/fronte-direction-import`

## applications/app-version-web/adsum-controleur (3)

- `fix/controle-double-role`
- `fix/controleur-refresh-garde-onglet`
- `fix/taxonomie-attributions`

## applications/app-version-web/adsum-pilotage (2)

- `feat/identite-organisation`
- `feat/pilotage-absences-excuses`

## applications/app-version-web/adsum-console (1)

- `feat/observabilite-organisations`

## deployment/ci-templates (1)

- `feat/collab-cd-deploy`

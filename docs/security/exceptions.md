# Exceptions de sécurité ADSUM

Une vulnérabilité `CRITICAL` ou `HIGH` arrête le pipeline. Quand la corriger n'est
pas possible tout de suite, l'exception s'écrit ici. Elle ne se prend pas en
désactivant le contrôle : un contrôle désactivé ne se réactive jamais, alors qu'une
exception datée finit par expirer.

La tâche `security:exceptions` lit ce fichier et **refuse une exception périmée**.
C'est le seul mécanisme qui empêche une dérogation temporaire de devenir une
politique par oubli.

## Format

Chaque exception est une section de niveau deux, avec ces cinq lignes exactement. Le
champ `expire` est lu par la CI ; les autres sont lus par les humains, ce qui ne les
rend pas facultatifs.

```
## <identifiant-court-en-minuscules>

- composant: <dépôt et fichier ou dépendance concernée>
- gravite: CRITICAL | HIGH
- raison: <pourquoi la correction n'est pas immédiate>
- compensation: <ce qui réduit le risque en attendant>
- expire: AAAA-MM-JJ
- demandee-par: <personne>
```

## Règles

1. Une exception dure **au plus 90 jours**. Au-delà, ce n'est plus une exception,
   c'est une décision d'architecture, et elle se documente comme telle.
2. Une exception sans compensation est refusée en revue. « On accepte le risque »
   n'est pas une compensation ; « la route n'est joignable que depuis le réseau
   interne » en est une.
3. Renouveler une exception demande une nouvelle revue de sécurité, pas une
   modification de la date.
4. Une exception qui porte sur un chemin de production accessible sans
   authentification n'est pas accordée.

## Exceptions en vigueur

Aucune.

Ce fichier existe vide à dessein. Le créer le jour où l'on a besoin d'une exception,
c'est le créer dans l'urgence, et une procédure écrite dans l'urgence tient toujours
compte du cas particulier qui l'a motivée.

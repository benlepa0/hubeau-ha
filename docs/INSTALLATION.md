# Installation et vérification

État de l'installation sur ce serveur, au 2026-09-21.

## Ce qui a été fait

1. `custom_components/hubeau/` copié dans `~/homeassistant/config/custom_components/`
   (par `docker cp`, le dossier appartenant à root) ;
2. `hass --script check_config` — passé sans erreur ;
3. Home Assistant redémarré par son API, revenu en `RUNNING` en 36 secondes ;
4. intégration configurée par l'API : rayon 25 km → 13 stations → Lavalette
   (`Y320002001`), retenue pour ses 30 ans de chronique là où Trinquat, plus
   proche, n'a ouvert qu'en 2022 ;
5. carte ajoutée à la vue Debug par l'API WebSocket de Lovelace — et non par
   une édition de `.storage`, que Home Assistant aurait écrasée.

Une sauvegarde du tableau de bord précède l'opération :
`.storage/lovelace.dashboard_dashboard.bak-20260921-154311-avant-hubeau`.

## Vérifications

| | |
|---|---|
| entités créées | 10, toutes disponibles |
| hauteur | 0,272 m — rang 8,7 %, régime *étiage* |
| débit | 0,247 m³/s — rang 24,4 % |
| statistiques hauteur | 11 132 jours (30,5 ans), médiane 0,443 m, max 4,40 m le 2014-10-06 |
| statistiques débit | 11 179 jours (30,6 ans), médiane 0,648 m³/s, max 239,42 m³/s le 2002-12-12 |
| erreurs au journal | aucune |
| durée du premier démarrage | 36 s, historique compris |

Les statistiques sont en cache dans `.storage/hubeau.Y320002001.statistiques`
et ne sont recalculées qu'une fois par mois.

## Historique et références

Depuis la version 0.2.0, l'historique externe sert uniquement au calcul des
références de la station. Il n'est plus importé dans le recorder de Home
Assistant. Les statistiques déjà importées par la version précédente restent
en base tant qu'un nettoyage distinct n'a pas été réalisé.

## Retrait

```bash
docker exec homeassistant rm -rf /config/custom_components/hubeau
docker exec homeassistant rm -f /config/.storage/hubeau.Y320002001.statistiques
# puis supprimer l'entrée dans Paramètres → Appareils et services
```

## Déploiement de la carte

`outils/deployer.sh` copie l'intégration et la carte, puis vérifie par somme
de contrôle que ce qui est déployé correspond bien à la source.

Ce script existe parce que l'inverse s'est produit : la carte avait été copiée
une première fois, puis corrigée deux fois dans le dépôt **sans être
redéployée**. La version en place était celle où les vagues étaient masquées
par un rectangle de la même couleur et où les filets de courant, à 18 %
d'opacité sur deux pixels et demi, restaient invisibles. Conclusion légitime de
l'utilisateur : « je ne vois pas d'animation ».

**Le nom du fichier porte le numéro de version**, et pas seulement l'URL.

Home Assistant sert `/hacsfiles` avec `Cache-Control: max-age=2678400`, soit
trente et un jours. Un simple paramètre `?v=` ne suffit pas à s'en défaire :
l'application Companion continue de servir ce qu'elle détient, et l'on croit
que rien n'a changé. Un nom différent, lui, n'a jamais été demandé — il ne
peut pas être en cache. Le script de déploiement dépose donc
`hubeau-card-<version>.js` à côté du nom fixe, ne garde que les trois
dernières, et la ressource Lovelace pointe sur le nom versionné.

La carte refuse aussi de s'enregistrer deux fois : si une version antérieure
est déjà chargée dans la page, `customElements.define` lèverait une erreur et
le reste du fichier ne s'exécuterait pas. Un avertissement le dit dans la
console plutôt que d'échouer en silence.

Pour vérifier la version réellement chargée, la console du navigateur affiche
une ligne `HUBEAU-CARD 0.1.1` au chargement de la carte.

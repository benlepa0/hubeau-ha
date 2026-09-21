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

## Limite au démarrage

Le graphique de la carte est **vide les premiers jours** : Home Assistant ne
connaît pas le passé de ces capteurs et construit son historique au fil de
l'eau. Il sera complet au bout d'une semaine.

Hub'Eau conserve pourtant un mois glissant au pas fin. Injecter ce passé dans
le `recorder` de Home Assistant est faisable — par `recorder.import_statistics`
— mais c'est un travail à part, qui n'alimenterait d'ailleurs qu'une carte de
statistiques et non `mini-graph-card`, laquelle lit l'historique d'états.

## Retrait

```bash
docker exec homeassistant rm -rf /config/custom_components/hubeau
docker exec homeassistant rm -f /config/.storage/hubeau.Y320002001.statistiques
# puis supprimer l'entrée dans Paramètres → Appareils et services
```

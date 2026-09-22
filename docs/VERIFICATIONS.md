# Vérifications sur plusieurs stations

Campagne du 2026-09-21, sur la version 0.2.1. Elle vaut surtout pour ce qu'elle
a mis au jour : les lacunes de la source, et trois défauts du diagnostic qui
n'ont pas été corrigés depuis.

## Protocole

Le client et les calculs déployés ont été exécutés dans un processus isolé,
sans ajouter de station à Home Assistant, sans import ni accès au `recorder`.
`outils/tester_stations.py` reproduit ces contrôles en lecture seule :

```bash
docker exec -i homeassistant python3 -u - < outils/tester_stations.py
```

Les onze stations dans un rayon de 25 km autour du centre de Montpellier ont
été interrogées. Minimums, moyennes et maximums sur sept jours concordent avec
un calcul indépendant. Les références historiques ont été vérifiées pour
Trinquat, Juvignac, Saint-Jean-de-Védas et le Lirou : extrêmes, moyenne et
ordre des percentiles.

## Ce que les onze stations ont donné

| Station | Mesures de hauteur sur sept jours | Observation au moment du test |
|---|---:|---|
| Le Lez à Montpellier - Trinquat | 2009 | Mesures récentes ; références disponibles |
| Le Lez à Montferrier-sur-Lez [Lavalette] | 2009 | Mesures récentes |
| La Mosson à Juvignac | 161 | Dernière hauteur le 15 septembre ; résumé très partiel ; historique trop court |
| Le Lez à Lattes [3ème écluse] | 2010 | Mesures récentes |
| La Mosson à Lavérune | 0 | Aucune hauteur sur sept jours, aucun débit retourné |
| La Mosson à Saint-Jean-de-Védas | 1997 | Hauteur disponible ; aucun débit retourné |
| La Mosson [Ruisseau de l'Avy] à Grabels - Source Avy | 63 | Dernière hauteur le 17 septembre ; résumé partiel |
| Le Salaison à Mauguio | 2009 | Mesures récentes |
| Le Lez [source] à Saint-Clément-de-Rivière | 1997 | Mesures récentes |
| Le Lirou au Triadou [Pont du Lien] | 2010 | Mesures récentes, mais alerte de valeurs figées déclenchée |
| [La Méditerranée] au Grau-du-Roi - Marégraphe de Port-Camargue | 1995 | Hauteur seule ; marégraphe, pas une rivière |

Le rendu JavaScript avec un DOM simulé passe pour ces onze jeux de données, y
compris les valeurs négatives et l'absence de débit. Ce n'est ni un test visuel
dans un navigateur, ni onze installations complètes dans Home Assistant. Des
simulations vérifient en plus la cadence de quinze minutes, l'effacement du
résumé après une panne, la reprise, la série vide, la valeur zéro, l'historique
trop court et le refus d'une pagination incomplète.

## Défauts connus, non corrigés

- **La fraîcheur est calculée sur la plus récente des deux grandeurs.** Une
  hauteur vieille de 48 heures accompagnée d'un débit récent donne
  `obsolete = False`. Le contrôle devrait être distinct pour la hauteur et pour
  le débit.
- **Le critère d'incohérence est trop simple.** Une hauteur négative avec un
  débit positif suffit à déclencher l'alerte, alors que la hauteur est relative
  au zéro de l'échelle, comme le rappelle la [documentation
  HydroPortail](https://hydro.eaufrance.fr/aide/la-station-hydrometrique). Une
  série stable ne prouve pas non plus une panne à elle seule : le message
  « la station répond mais ne mesure plus » est trop affirmatif.
- **Le bandeau ne signale pas une couverture partielle** des sept jours. Les
  dates et le nombre de mesures restent disponibles en attributs.
- **Les catégories de régime ne conviennent pas à un marégraphe**, que la
  recherche par distance peut pourtant proposer.

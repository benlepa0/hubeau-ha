# Hub'Eau pour Home Assistant

Dernière révision : 2026-09-21.

Suivi des cours d'eau français : hauteur, débit, et surtout **ce que ces
chiffres veulent dire**.

Données de l'API publique [Hub'Eau](https://hubeau.eaufrance.fr/) (Office
français de la biodiversité), **sans clé ni compte**.

## Ce que cette intégration apporte

Une hauteur d'eau isolée ne dit rien. « 0,27 m » n'a de sens que rapporté à la
rivière : c'est un étiage marqué sur le Lez, ce serait un lit à sec sur la
Loire. L'intégration télécharge donc **la chronique complète de la station** —
jusqu'à trente ans de valeurs journalières — et en tire les percentiles qui
situent la mesure du moment.

Un capteur annonce alors :

> **0,272 m** — régime *étiage*, rang **8 %**, dans le quart le plus bas de
> 30,5 ans de mesures. Maximum connu : 4,40 m, le 6 octobre 2014.

C'est ce que ne font ni Vigicrues ni les intégrations existantes, qui donnent
la mesure brute ou un seuil fixé à la main.

### Détection des stations défaillantes

Une station hydrométrique peut rester joignable tout en ayant cessé de
mesurer. Deux contrôles la démasquent :

- **capteur figé** — moins de quatre valeurs distinctes sur douze heures. Le
  Lirou au Triadou annonce ainsi 2,65 m³/s depuis des semaines ;
- **incohérence hauteur/débit** — le débit n'est pas mesuré, il se déduit de
  la hauteur par une courbe de tarage. Une hauteur nulle accompagnée d'un
  débit franc signale une station hors d'eau. Ce même Lirou affiche 2,65 m³/s
  pour une hauteur de **−0,002 m**.

## Références historiques

L'historique de la station sert uniquement à calculer les références :
percentiles, médiane, moyenne et extrêmes. Ces résultats sont conservés dans un cache
local et recalculés tous les trente jours. Le classement de la mesure actuelle
ne dépend pas de la durée d'installation de Home Assistant ni de sa base
`recorder` : à série de référence identique, le calcul donne le même résultat.

L'intégration n'importe aucune ancienne mesure dans les statistiques de Home
Assistant. Celui-ci peut enregistrer normalement les nouvelles mesures des
capteurs à partir de leur installation.

La référence porte sur les maximums journaliers pour la hauteur, et sur les
moyennes journalières pour le débit. Le rang compare une mesure instantanée
à cette distribution journalière ; les catégories sont des repères propres
au projet, pas des seuils officiels de vigilance.

## Entités

Par station suivie :

| Entité | Contenu |
|---|---|
| Hauteur d'eau | mètres, avec le rang et la lecture en attributs |
| Débit | m³/s, idem |
| Régime | *étiage sévère → crue majeure*, en percentiles de la station |
| Rang sur la chronique | 0 à 100 % |
| Tendance | cm/h, par régression sur 12 h |
| Dernière mesure / Âge de la mesure | fraîcheur de la donnée |
| Crue *(binaire)* | au-delà du percentile 99, soit ~4 jours par an |
| Données obsolètes *(binaire)* | plus de 2 h sans mesure |
| Capteur figé *(binaire)* | station immobile ou incohérente |

## Installation

Par HACS, en dépôt personnalisé, puis **Paramètres → Appareils et services →
Ajouter une intégration → Hub'Eau**. La configuration se fait entièrement par
l'interface : on choisit un rayon autour du domicile, puis une station dans la
liste triée par distance.

Le premier démarrage télécharge trente ans d'historique et peut prendre une
trentaine de secondes. C'est voulu : les statistiques sont ce qui rend les
mesures lisibles.

## Limites connues

- Hub'Eau ne conserve le **pas de temps fin qu'un mois glissant**. Au-delà,
  seules les valeurs journalières existent — d'où des statistiques fondées sur
  la hauteur *maximale* journalière et le débit *moyen* journalier.
- Les statistiques demandent au moins **trois ans** de chronique. Une station
  récente n'en aura pas ; ses mesures restent exposées, sans lecture.
- Les fortes valeurs de la chronique sont souvent qualifiées « douteuses » par
  le producteur : au-delà d'un certain débit, la courbe de tarage est
  extrapolée faute de jaugeage possible en crue.
- Ce n'est **pas un outil d'alerte**. Pour la vigilance officielle, voir
  [Vigicrues](https://www.vigicrues.gouv.fr/).

## Licence

MIT.

## Historique court

- 2026-09-21 — Campagne de tests sur onze stations et simulations des pannes ;
  calculs du bandeau vérifiés, limites de fraîcheur et de diagnostic documentées.

- 2026-09-21 — Carte 0.3.3 : retrait des traînées blanches et des bulles ;
  les vagues et la transition du niveau restent animées.

- 2026-09-21 — Carte 0.3.4 : minimum, moyenne et maximum du bas de carte
  deviennent des valeurs non cliquables.

- 2026-09-21 — Intégration 0.2.0 : retrait de l'import des anciennes mesures
  dans le recorder ; l'historique sert uniquement au calcul des références.

- 2026-09-21 — Carte 0.4.0 : le bandeau affiche les minimum, moyenne et maximum
  de la série historique de référence, sans requête au recorder. Pour la
  hauteur, la série est constituée des maximums journaliers. Un ancien cache
  sans moyenne est recalculé au prochain chargement.

- 2026-09-21 — Versions 0.2.0 / 0.4.0 activées après redémarrage autorisé
  de Home Assistant. Les dix entités de Lavalette sont disponibles et la
  carte lit les références dans leurs attributs. Série de hauteur du
  1996-01-01 au 2026-09-20 : minimum 0,184 m, moyenne 0,508 m, maximum
  4,403 m (maximums journaliers). Les anciennes statistiques importées
  restent en base ; aucun nettoyage du recorder n'a été effectué.

- 2026-09-21 — Correction 0.2.1 / carte 0.4.1 : le bandeau retrouve le minimum,
  la moyenne arithmétique et le maximum des mesures de hauteur des sept derniers
  jours, récupérées directement auprès de Hub'Eau toutes les quinze minutes.
  Les références sur trente ans restent réservées au classement du niveau.
  Aucun import historique ni accès au recorder pour ce bandeau.
  Déploiement vérifié après redémarrage : 2 011 mesures disponibles sur la
  fenêtre de sept jours, minimum 0,264 m, moyenne 0,272 m et maximum 0,293 m.

## Vérifications sur plusieurs stations — 2026-09-21

Le client déployé a été exécuté dans un processus isolé, sans ajouter de
station à Home Assistant, sans import ni accès au recorder. Le script
`outils/tester_stations.py` permet de reproduire les contrôles en lecture seule :

```bash
docker exec -i homeassistant python3 -u - < outils/tester_stations.py
```

Les onze stations dans un rayon de 25 km autour du centre de Montpellier
ont été interrogées. Les minimums, moyennes et maximums des mesures disponibles
sur sept jours concordent avec un calcul indépendant. Les références
historiques ont été vérifiées pour Trinquat, Juvignac, Saint-Jean-de-Védas et
le Lirou : extrêmes, moyenne et ordre des percentiles. Juvignac manque de
recul ; Saint-Jean-de-Védas n'a pas de série journalière de débit disponible.

| Station | Mesures de hauteur sur sept jours | Observation au moment du test |
|---|---:|---|
| Le Lez à Montpellier - Trinquat | 2009 | Mesures récentes ; références disponibles |
| Le Lez à Montferrier-sur-Lez [Lavalette] | 2009 | Mesures récentes ; station déjà utilisée dans HA |
| La Mosson à Juvignac | 161 | Dernière hauteur le 15 septembre ; résumé très partiel ; historique trop court |
| Le Lez à Lattes [3ème écluse] | 2010 | Mesures récentes |
| La Mosson à Lavérune | 0 | Aucune hauteur sur sept jours, aucun débit retourné |
| La Mosson à Saint-Jean-de-Védas | 1997 | Hauteur disponible ; aucun débit retourné |
| La Mosson [Ruisseau de l'Avy - affluent de la Mosson] à Grabels - Source Avy | 63 | Dernière hauteur le 17 septembre ; résumé partiel |
| Le Salaison à Mauguio | 2009 | Mesures récentes |
| Le Lez [source] à Saint-Clément-de-Rivière | 1997 | Mesures récentes |
| Le Lirou au Triadou [Pont du Lien] | 2010 | Mesures récentes mais alerte de valeurs figées déclenchée |
| [La Méditerranée] au Grau-du-Roi - Marégraphe de Port-Camargue | 1995 | Hauteur seule ; marégraphe, pas une rivière |

Le rendu JavaScript avec un DOM simulé passe pour ces onze jeux de données,
y compris les valeurs négatives et l'absence de débit. Il ne s'agit pas d'un
test visuel dans un navigateur ni de onze installations complètes dans HA.
Des simulations supplémentaires vérifient la cadence de quinze minutes,
l'effacement du résumé après une panne, la reprise, la série vide, la valeur
zéro, l'historique trop court et le refus d'une pagination incomplète.

Limites identifiées, non corrigées pendant cette campagne :

- Le bandeau ne signale pas explicitement une couverture partielle des sept
  jours. Les dates et le nombre de mesures sont disponibles en attributs.
- La fraîcheur est calculée sur la plus récente des deux grandeurs. Une
  hauteur ancienne de 48 heures et un débit récent produisent actuellement
  `obsolete = False` dans le cas simulé ; le contrôle devrait être distinct
  pour la hauteur et le débit.
- Une hauteur négative et un débit positif suffisent à déclencher l'alerte
  d'incohérence. Ce critère n'est pas généralisable : la hauteur est relative
  au zéro de l'échelle, comme le précise la
  [documentation HydroPortail](https://hydro.eaufrance.fr/aide/la-station-hydrometrique).
  Une série stable ne prouve pas non plus à elle seule une panne ; le message
  actuel « la station répond mais ne mesure plus » est trop affirmatif.
- Le choix des stations inclut le marégraphe de Port-Camargue, auquel les
  catégories de régime fluvial ne sont pas adaptées.

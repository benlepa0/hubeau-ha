# Hub'Eau pour Home Assistant

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

## La chronique versée dans Home Assistant

Trente ans de mesures ne serviraient qu'une fois — à calculer onze percentiles —
puis dormiraient dans un fichier de cache, pendant que Home Assistant
n'afficherait que ce qu'il a lui-même enregistré depuis l'installation.

L'intégration **verse donc la chronique journalière dans les statistiques long
terme** du `recorder`, conservées indéfiniment. La station apparaît alors dans
les graphiques natifs comme si elle y avait toujours été suivie. Sur le Lez à
Lavalette : **369 mois depuis décembre 1995**, une pointe de hauteur à 4,40 m
et un débit instantané maximal de **499,27 m³/s**.

Le débit dispose des trois valeurs journalières — moyenne, minimum, maximum —
et l'écart entre elles est parlant : le 29 septembre 2014, la moyenne du jour
valait 80 m³/s pour une pointe à 366. La hauteur n'est publiée qu'en maximum
journalier ; les trois courbes s'y superposent donc, ce qui signale à l'œil
qu'il n'y a qu'une valeur par jour. C'est d'ailleurs celle qui compte,
puisque ce sont les pointes qui font les crues.

Le versement n'a lieu qu'une fois, en tâche de fond, et ne retarde pas le
démarrage.

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

# Dépannage, cache et retrait

Ce que l'on regarde quand quelque chose cloche, où vivent les données, et
comment tout défaire. L'installation est décrite dans le
[README](../README.md).

## Après l'ajout d'une station

Dix entités apparaissent : sept capteurs et trois binaires. Le premier
rafraîchissement télécharge la chronique et prend une trentaine de secondes ;
les entités restent indisponibles pendant ce temps, puis le régime, le rang et
les extrêmes s'affichent d'un coup.

Trois signes que la lecture est correcte :

- le **rang** est cohérent avec le régime annoncé : un régime *étiage* sous
  le percentile 25, une *crue* au-delà du 99 ;
- les **références** en attributs portent une profondeur crédible : nombre de
  jours, date du maximum, médiane ;
- le journal ne contient aucune erreur `hubeau`.

Exemple relevé sur le Lez à Montferrier-sur-Lez (Lavalette, `Y320002001`), qui
a servi de station de mise au point :

| | |
|---|---|
| hauteur | 0,272 m, rang 8,7 %, régime *étiage* |
| débit | 0,247 m³/s, rang 24,4 % |
| références de hauteur | 11 132 jours (30,5 ans), médiane 0,443 m, maximum 4,40 m le 2014-10-06 |
| références de débit | 11 179 jours (30,6 ans), médiane 0,648 m³/s, maximum 239,42 m³/s le 2002-12-12 |
| premier démarrage | 36 s, historique compris |

Une station trop récente n'aura pas de références : ses mesures restent
exposées, sans lecture. Juvignac, ouverte en 2022, est dans ce cas.

## Cache des références

Les références sont conservées dans `.storage/hubeau.<code station>.statistiques`
et recalculées tous les trente jours. Elles ne dépendent ni de la durée
d'installation de Home Assistant, ni du `recorder` : à série identique, le
calcul redonne le même résultat.

L'intégration n'importe aucune ancienne mesure dans les statistiques long
terme de Home Assistant. Une installation antérieure à la version 0.2.0 peut
en avoir laissé en base ; leur nettoyage éventuel est une opération distincte,
à faire depuis les outils de Home Assistant.

## Vérifier la carte réellement chargée

La carte est servie par l'intégration à l'adresse
`/hubeau/hubeau-card.js?v=<version du paquet>`. La console du navigateur
affiche une ligne `HUBEAU-CARD <version>` à son chargement ; c'est le moyen le
plus sûr de savoir ce qui s'exécute, plutôt que ce que l'on croit avoir
déployé.

Si une ancienne copie traîne dans `www/community/hubeau-card/`, héritée d'une
version antérieure à la 0.3.0, elle peut être chargée en plus par une
ressource Lovelace restée déclarée. La carte le signale alors dans la console
au lieu d'échouer en silence : un élément personnalisé ne se définit qu'une
fois par page. Supprimer la ressource et le fichier.

## Retrait

```bash
# depuis la configuration de Home Assistant
rm -rf custom_components/hubeau
rm -f .storage/hubeau.*.statistiques
```

Puis supprimer l'entrée dans **Paramètres → Appareils et services**. Par HACS,
la suppression de l'intégration fait le premier point.

# Dépannage, cache et retrait

Ce que l'on regarde quand quelque chose cloche, où vivent les données, et
comment tout défaire. L'installation est décrite dans le
[README](../README.md).

## Après l'ajout d'une station

Dix entités : sept capteurs, trois binaires. Rang et régime arrivent quelques
secondes après les mesures. Station muette : dernière valeur conservée,
*Données obsolètes* à `on` après 2 h. Indisponible = API injoignable.

Trois signes que la lecture est correcte :

- le **rang** est cohérent avec le régime annoncé : un régime *étiage* sous
  le percentile 25, une *crue* au-delà du 99 ;
- l'attribut `grandeur_reference` vaut `HIXnJ` pour la hauteur et `QIXnJ` pour
  le débit. Un `QmnJ` signale une station qui ne publie pas ses pointes
  journalières, et `reference_fiable_jusqu_au_percentile` dit jusqu'où la
  chronique porte ;
- les **références** en attributs portent une profondeur crédible : nombre de
  jours, date du maximum, médiane ;
- le journal ne contient aucune erreur `hubeau`.

Exemple relevé sur le Lez à Montferrier-sur-Lez (Lavalette, `Y320002001`), qui
a servi de station de mise au point :

| | |
|---|---|
| hauteur | 0,272 m, rang 7,5 %, régime *étiage* |
| débit | 0,247 m³/s, rang 20,6 % |
| références de hauteur | 10 629 jours (29,1 ans), médiane 0,455 m, maximum 4,403 m le 2014-10-06 |
| références de débit | 10 502 jours (28,8 ans), médiane 0,846 m³/s, maximum 298,867 m³/s le 2001-10-09 |
| mise en place / cycle / chronique 30 ans | 0,01 s / 0,09 s / 4,5 s |

Relevé après la version 0.4.0, donc sur des références écrémées des valeurs
non validées, et pour le débit sur les pointes journalières.

Une station trop récente n'aura pas de références : ses mesures restent
exposées, sans lecture. Juvignac, ouverte en 2022, est dans ce cas. Une station
dont le producteur ne valide pas les données non plus, et le journal le dit
alors en toutes lettres : « chronique assez longue mais N valeurs écartées
faute de statut ou de qualification suffisants ».

## Cache des références

Les références sont conservées dans `.storage/hubeau.<code station>.statistiques`
et recalculées tous les trente jours. Un cache antérieur à la version 0.4.0 ne
porte pas la grandeur dont il vient : il est recalculé en arrière-plan. Les
mesures des sept derniers jours sont dans `.storage/hubeau.<code station>.mesures`. Elles ne dépendent ni de la durée
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

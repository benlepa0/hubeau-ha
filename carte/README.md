# Carte Hub'Eau

Carte Lovelace pour l'intégration `hubeau`. Aucune dépendance, aucune
compilation : un élément personnalisé et du SVG.

## Le parti pris

Une rivière ne se lit pas sur une échelle linéaire. Sur le Lez, la médiane
vaut 0,44 m et le record 4,40 : en étiage, une échelle proportionnelle
écraserait l'eau en un filet invisible au bas du cadre.

L'échelle verticale suit donc les **percentiles**. Chaque repère occupe une
position fixe — médiane à 34 % de hauteur, percentile 95 à 70 %, record au
sommet — et l'eau monte selon son rang. La moitié basse du cadre couvre ainsi
la moitié du temps, ce qui rend l'étiage aussi lisible qu'une crue.

## Animations

- **le niveau** monte et descend sur 1,2 s, en transition douce ;
- **les vagues** : deux sinusoïdes, l'une glissant à contresens de l'autre.
  Rien de plus — une troisième onde puis une crête blanche ont été essayées,
  et alourdissaient le tracé sans le rendre plus vivant ;
- **l'écoulement** : des traînées floues filent de gauche à droite, plus
  longues et plus rapides près de la surface, et s'estompent en profondeur ;
- **les bulles** dérivent vers la droite, portées par le courant, avec une
  légère ascension. Les faire monter était un contresens : dans une rivière,
  ce qui renseigne sur la vitesse est ce qui défile, pas ce qui remonte. Les
  bulles du fond traînent — une veine d'eau est freinée par le lit et les
  berges, et la surface file plus vite.

Sous la scène, un bandeau donne le **minimum, la moyenne et le maximum des
sept derniers jours**, lus dans les statistiques long terme du `recorder` et
non dans l'historique détaillé, que Home Assistant purge au bout de quelques
jours.

La vitesse suit le débit sur une échelle **logarithmique** : entre 0,2 et
200 m³/s il y a trois ordres de grandeur, qu'une échelle linéaire écraserait.
Une traversée dure de 8 s en étiage à 1,5 s en crue. Les vagues suivent de
loin — une surface n'accélère pas autant que la veine d'eau qui la porte.

### Pièges rencontrés

La scène est en HTML, et non en SVG : le SVG était étiré par
`preserveAspectRatio="none"`, ce qui aurait transformé chaque bulle ronde en
ellipse. Seules les vagues, qui gagnent à être étirées, restent en SVG.

La dérive des bulles anime la propriété `left`, pas un `translateX` en
pourcentage : un pourcentage de translation se rapporte à la taille de
l'élément, non à celle de son conteneur. Larges de quelques pixels, les bulles
ne parcouraient donc que quelques pixels.

Enfin, les vagues s'appelaient `.v` — comme les valeurs chiffrées du pied de
carte. Les nombres héritaient de l'animation de glissement et **défilaient vers
la gauche en boucle**, sans raison apparente. `outils/verifier_carte.py`
refuse désormais qu'une classe porteuse d'animation soit partagée, et vérifie
aussi qu'aucun accent grave ne s'est glissé dans le bloc de style — ce qui
romprait le littéral de gabarit qui le porte et empêcherait la carte de se
charger. Les deux se sont produits.

`prefers-reduced-motion` est respecté, et `animations: false` les coupe.

## Clic vers l'historique

La hauteur, le débit et les trois valeurs des sept derniers jours ouvrent la
fiche de l'entité, d'où l'on accède à l'historique et aux statistiques long
terme — dont la chronique versée par l'intégration.

L'événement `hass-more-info` doit franchir la frontière du shadow DOM, d'où
`composed: true` : sans cela il resterait enfermé dans la carte et rien ne
s'ouvrirait.

## Configuration

```yaml
type: custom:hubeau-card
hauteur: sensor.le_lez_a_montferrier_sur_lez_lavalette_hauteur_d_eau
```

Les autres capteurs de la station se déduisent du préfixe. Ils peuvent être
nommés un à un — `debit`, `regime`, `rang`, `tendance`, `age` — pour les
installations où les identifiants auraient été renommés. `title` remplace le
titre, `animations: false` fige la scène.

## Démonstration hors Home Assistant

`demo.html` affiche cinq états côte à côte — étiage, normal, fort, crue, et
une station en panne — avec un `hass` simulé. Utile pour travailler le rendu
sans redémarrer quoi que ce soit :

```bash
cd carte && python3 -m http.server 8777
```

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
- **les vagues** : trois ondes d'amplitudes et de vitesses décroissantes,
  dont une à contresens, plus une crête claire qui souligne la surface. Une
  seule onde régulière fait mécanique ; trois qui se croisent font une surface
  qui respire ;
- **l'écoulement** : des traînées floues filent de gauche à droite, plus
  longues et plus rapides près de la surface, et s'estompent en profondeur ;
- **les bulles** montent en dérivant latéralement. Une remontée strictement
  verticale trahirait l'artifice.

La vitesse suit le débit sur une échelle **logarithmique** : entre 0,2 et
200 m³/s il y a trois ordres de grandeur, qu'une échelle linéaire écraserait.
Une traversée dure de 8 s en étiage à 1,5 s en crue. Les vagues suivent de
loin — une surface n'accélère pas autant que la veine d'eau qui la porte.

### Deux pièges rencontrés

La scène est en HTML, et non en SVG : le SVG était étiré par
`preserveAspectRatio="none"`, ce qui aurait transformé chaque bulle ronde en
ellipse. Seules les vagues, qui gagnent à être étirées, restent en SVG.

Et la montée des bulles anime la propriété `bottom`, pas un `translateY` en
pourcentage : un pourcentage de translation se rapporte à la taille de
l'élément, non à celle de son conteneur. Hautes de quelques pixels, les bulles
montaient donc de quelques pixels et restaient collées au fond.

`prefers-reduced-motion` est respecté, et `animations: false` les coupe.

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

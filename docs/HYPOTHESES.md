# Hypothèses scientifiques, sources et vérifications

Vérification du 2026-09-22. Chaque hypothèse de l'intégration est confrontée à
la source officielle, puis, quand c'est possible, mesurée sur la chronique
complète du Lez à Montferrier-sur-Lez (Lavalette, `Y320002001`), du
1996-01-01 au 2026-09-21 : 11 180 débits journaliers et 11 133 hauteurs
journalières.

Les mesures de cette page sont reproductibles : elles n'utilisent que l'API
publique, sans clé.

## 1. Les grandeurs journalières employées comme référence

**Ce que fait l'intégration.** Les références de hauteur viennent de `HIXnJ`,
celles de débit de `QmnJ`.

**La source.** La [documentation de l'API Hub'Eau
hydrométrie](https://hubeau.eaufrance.fr/page/api-hydrometrie) définit
`QmnJ` comme le débit **moyen** journalier, `HIXnJ` comme la hauteur
**instantanée maximale** journalière, et `QIXnJ` comme le débit **instantané
maximal** journalier. Les notations suivent la convention officielle rappelée
par HydroPortail, [données et noms des
variables](https://www.hydro.eaufrance.fr/aide/donnees-et-noms-des-variables) :
`Q` débit, `H` hauteur, `i` instantané, `m` moyen, `J` journalier, `X`
maximum, `N` minimum.

**Verdict : exact, mais dissymétrique.** La hauteur du moment est classée
parmi des **maximums** journaliers, le débit du moment parmi des **moyennes**
journalières. Les deux grandeurs ne sont donc pas lues avec la même règle, et
le débit est le seul des deux à être comparé à une série lissée.

**Mesure.** Sur le Lez, le débit de pointe journalier vaut de 1,2 à 2,8 fois
le débit moyen du même jour selon l'endroit de la distribution :

| percentile | débit moyen journalier | débit de pointe journalier | rapport |
|---|---:|---:|---:|
| 50 | 0,643 m³/s | 0,783 m³/s | 1,22 |
| 75 | 2,018 | 2,591 | 1,28 |
| 90 | 4,634 | 5,508 | 1,19 |
| 95 | 8,388 | 9,922 | 1,18 |
| 99 | 23,446 | 35,571 | 1,52 |
| 99,9 | 59,052 | 164,329 | 2,78 |
| maximum | 239,420 | 499,273 | 2,09 |

Conséquence : une pointe située au percentile 99 des pointes est lue au
percentile **99,64** dans la distribution des moyennes. Le rang de débit
affiché est donc systématiquement surévalué en crue.

## 2. « Crue au-delà du percentile 99, soit environ quatre jours par an »

**La source.** Arithmétique : 1 % de 365,25 jours vaut 3,65 jours.

**Verdict : vrai pour la hauteur, faux quand le débit prend le relais.**
Le capteur binaire s'appuie sur la grandeur principale, et l'intégration
préfère la hauteur quand elle existe. Ce choix est lui-même fondé, voir le
point 4.

**Mesure**, seuil pris au percentile 99 de la chronique de la station :

| grandeur qui porte l'alerte | seuil | jours par an |
|---|---:|---:|
| hauteur, classée dans les maximums journaliers | 1,522 m | **3,7** |
| débit de pointe, classé dans les moyennes journalières | 23,836 m³/s | **6,5** |
| débit de pointe, classé dans les pointes journalières | 35,571 m³/s | 3,7 |

La dernière ligne montre le correctif : prendre `QIXnJ` comme référence de
débit rendrait à l'alerte la fréquence annoncée.

## 3. Les seuils de régime

**Ce que fait l'intégration.** Sept classes, d'étiage sévère à crue majeure,
aux percentiles 5, 25, 75, 90, 99, 99,9 et 100 de la chronique de la station.

**La source.** La démarche, classer une mesure dans la distribution des
valeurs journalières de sa propre station, est celle de la **courbe des débits
classés**, outil standard décrit par l'OFB dans sa [fiche
méthodologique](https://patbiodiv.ofb.fr/fiche-methodologique/hydroelectricite/courbe-debits-classes-111).
En revanche, les indices réglementaires français ne sont pas des percentiles
de cette courbe :

- pour les basses eaux, le **QMNA5**, débit mensuel minimal de fréquence
  quinquennale, est le débit d'étiage de référence pour la police de l'eau, et
  le **VCN3** ou **VCN10** décrit un étiage sévère de courte durée ([OFB,
  débits d'étiage](https://patbiodiv.ofb.fr/fiche-methodologique/hydroelectricite/debits-detiage-qmna-vcn-113)) ;
- pour les hautes eaux, les statistiques officielles sont des **périodes de
  retour** ajustées sur des maximums annuels, `QJ-X` et `Qi-X` dans la
  notation HydroPortail, et non des percentiles de la série complète.

**Verdict : les bornes sont une convention de ce projet.** Elles ne
proviennent d'aucun texte ni d'aucune pratique officielle, contrairement à ce
qu'affirmait le commentaire de `const.py` avant cette vérification. Elles
restent défendables comme lecture relative, mais elles ne se comparent ni au
QMNA5 ni à une crue décennale.

**Piège de vocabulaire.** En hydrologie, `Q95` désigne le débit **dépassé**
95 % du temps, donc un étiage. Le « rang » de l'intégration est l'inverse, un
percentile de non-dépassement : rang 8 % signifie basses eaux, rang 99 %
signifie crue. Un hydrologue lira donc ces deux chiffres à l'envers.

## 4. « Le débit n'est pas mesuré, il se déduit de la hauteur »

**La source.** C'est la pratique de l'hydrométrie : la courbe de tarage est
construite sur des jaugeages, puis extrapolée au-delà du plus fort d'entre
eux. L'INRAE en fait un sujet de recherche à part entière, avec la méthode
bayésienne [BaRatin](https://riverhydraulics.riverly.inrae.fr/recherche/hydrometrie/analyse-d-incertitude),
qui « combine deux sources d'information incertaine, la connaissance a priori
sur les contrôles hydrauliques, et les jaugeages ».

**Verdict : exact**, et c'est ce qui justifie de préférer la hauteur au débit
pour la lecture d'ensemble.

**Réserve de méthode.** Les chiffres d'incertitude qui circulent, de l'ordre
de ±30 % sur la partie haute extrapolée, viennent d'un bilan Cemagref de 2005
dont je n'ai pas pu ouvrir la source directement : le dépôt HAL et le wiki
Wikhydro étaient inaccessibles au moment de la vérification. Aucun chiffre
n'est donc avancé ici.

## 5. La qualification des données

**Ce que fait l'intégration.** Elle demande `date_obs_elab` et
`resultat_obs_elab`, rien d'autre, et retient toutes les valeurs.

**La source.** `obs_elab` publie aussi `code_qualification`, nomenclature
Sandre [508](https://www.sandre.eaufrance.fr/jeu-de-donnees/qualification-de-la-donnée-de-lobservation)
(0 inconnue, 12 incertaine, que Hub'Eau libelle « Douteuse », 16 non
qualifiée, 20 bonne), et `code_statut`, nomenclature Sandre
[510](https://id.eaufrance.fr/nsa/510) (0 sans validation, 4 brute, 8
corrigée, 12 pré-validée, 16 validée). La note méthodologique d'HydroPortail
[Calcul module / QMNA / VCN](https://hydro.eaufrance.fr/uploads/Publications/Calcul_module_QMNA_VCN_vf.pdf)
demande de choisir « le statut des données : prendre le maximum possible sur
l'Hydroportail grand public, à savoir "données pré-validées et validées" ».

**Verdict : l'intégration mélange ce que le producteur distingue.**

**Mesure** sur le Lez :

| | débit `QmnJ` | hauteur `HIXnJ` |
|---|---:|---:|
| jours retenus | 11 180 | 11 133 |
| qualifiés « douteuse » | 680, soit 6,1 % | 432, soit 3,9 % |
| hors « donnée validée » | 9,0 % | 8,8 % |
| part de douteuses au-delà du percentile 99 | 15,2 % | 0 % |
| maximum de la chronique | 239,420 m³/s, **douteux** | 4,403 m, bon |
| maximum parmi les seules valeurs bonnes | 94,525 m³/s | 4,403 m |
| percentile 99,9 sans les douteuses | 48,839, soit −17,2 % | 2,567, soit +3,2 % |

Deux enseignements. D'abord, le « maximum connu » de débit que l'intégration
affiche pour cette station est une valeur que le producteur qualifie lui-même
de douteuse, et elle vaut deux fois et demie le plus fort débit qualifié bon.
Ensuite, l'affirmation « les fortes valeurs sont souvent douteuses » vaut pour
le débit, où 15 % du dernier percentile est douteux, mais pas pour la hauteur
de cette station, où les douteuses sont au contraire des valeurs basses,
médiane 0,336 m contre 0,455 m.

## 6. La détection d'incohérence hauteur / débit

**Ce que fait l'intégration.** Une hauteur nulle ou négative accompagnée d'un
débit franc déclenche l'alerte « capteur figé », avec le message « la station
répond mais ne mesure plus ».

**La source.** HydroPortail rappelle que « les mesures (chroniques de
hauteurs) à la station sont exprimées en **hauteur locale** », rapportées au
zéro de l'échelle limnimétrique dont seule l'altitude est connue ([la station
hydrométrique](https://hydro.eaufrance.fr/aide/la-station-hydrometrique)).

**Verdict : le critère n'est pas généralisable.** Une hauteur nulle ou
négative ne signifie pas un lit à sec, elle signifie que le plan d'eau est au
niveau du zéro de l'échelle, ou en dessous, ce qui dépend de l'implantation de
la station. Le défaut était déjà consigné dans
[VERIFICATIONS.md](VERIFICATIONS.md) ; cette page en donne la raison.

## 7. La profondeur de chronique

**Ce que fait l'intégration.** Trois ans de valeurs journalières au minimum,
trente ans demandés à l'API.

**La source.** Aucun texte consulté ne fixe de durée minimale pour une courbe
des débits classés. HydroPortail conditionne ses analyses publiques à ce que
« le nombre de données pré-validées et validées est suffisant », sans donner
de seuil.

**Verdict : choix de projet, assumé.** Sur trois ans, le percentile 99 ne
repose que sur une dizaine de jours et le percentile 99,9 sur un seul. Les
classes hautes n'ont alors pas de sens statistique, ce que l'intégration
n'indique pas à l'utilisateur.

## 8. Les points vérifiés sans réserve

- **Un mois glissant au pas fin.** La documentation de l'API indique que
  `observations_tr` « maintains a one-month history », mise à jour depuis la
  plateforme PHyC « every 5 minutes ». L'intervalle d'interrogation de
  l'intégration, cinq minutes, est donc exactement celui de la source.
- **Le producteur des données.** Les mesures hydrométriques viennent de la
  plateforme HYDRO centrale, opérée par le Service central Vigicrues, et sont
  diffusées par Hub'Eau, portail de l'OFB et du BRGM, sous Licence Ouverte
  Etalab.
- **Les extrêmes affichés.** Maximum de hauteur 4,403 m le 2014-10-06 et
  médiane 0,443 m : retrouvés à l'identique sur la chronique complète.

## Ce qui reste à corriger dans le code

Par ordre d'effet mesuré, et non fait à ce jour :

1. **Référence de débit sur `QIXnJ`**, avec repli sur `QmnJ` pour les stations
   qui n'en publient pas. Rend à l'alerte de crue sa fréquence annoncée,
   6,5 jours par an contre 3,7 attendus dans le cas où le débit porte la
   lecture.
2. **Filtrer sur `code_statut` et `code_qualification`**, à l'image du réglage
   par défaut d'HydroPortail. Écarte 9 % de la chronique et, sur cette
   station, un maximum de débit douteux qui vaut deux fois et demie le plus
   fort débit qualifié bon.
3. **Signaler une chronique trop courte** plutôt que publier des classes
   hautes calculées sur quelques jours.

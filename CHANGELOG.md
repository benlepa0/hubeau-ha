# Journal des versions

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le
versionnement est [sémantique](https://semver.org/lang/fr/).

## [0.5.0] - 2026-09-22

Home Assistant n'attend plus Hub'Eau (57 s sur 60 au démarrage du 2026-09-22).

### Modifié

- Mise en place sans réseau : état relu sur le disque, API en arrière-plan.
- Une requête par cycle (hauteur et débit, depuis la dernière mesure) au lieu
  de quatre à six.
- Références : une requête par grandeur au lieu de six, en tâche de fond.
- Station muette : dernière valeur conservée, signalée par *Données obsolètes*.
- Délai 20 s, 3 essais. Carte mise en cache, URL à empreinte.

## [0.4.0] - 2026-09-22

Les trois correctifs identifiés par la vérification de la 0.3.2 sont
appliqués. Les références changent de valeur : elles sont recalculées au
premier démarrage, une trentaine de secondes par station.

### Modifié

- **La référence de débit est la pointe journalière `QIXnJ`**, et non plus la
  moyenne `QmnJ`, avec repli sur la moyenne pour les stations qui ne publient
  pas de pointes. On classait une mesure instantanée dans une série lissée :
  sur le Lez, l'alerte de crue se déclenchait 6,5 jours par an au lieu des 3,7
  annoncés. Elle en est revenue à 3,7.
- **Les valeurs non validées ou douteuses sont écartées des références**,
  d'après le statut et la qualification publiés par Hub'Eau, comme le fait
  HydroPortail pour ses analyses publiques. Sur le Lez, le maximum de débit
  passe de 239,420 m³/s, une moyenne que le producteur qualifiait de douteuse,
  à 298,867 m³/s, une pointe qu'il a validée.
- **La portée statistique de la chronique est exposée.** Un percentile n'est
  tenu pour soutenu que si dix jours de mesures le dépassent. Le résultat est
  dans l'attribut `reference_fiable_jusqu_au_percentile` et dans le journal.

### Ajouté

- Attributs `grandeur_reference`, `reference_fiable_jusqu_au_percentile`, et
  `nature_reference` qui distingue maintenant pointes et moyennes journalières.

### Connu

Une station dont le producteur ne valide rien perd ses références plutôt que
d'en recevoir de fausses. Sur onze stations testées, deux perdent celles de
débit et le marégraphe de Port-Camargue les perd toutes. Le journal en donne
la raison.

## [0.3.2] - 2026-09-22

### Modifié

- Vérification des hypothèses scientifiques contre les sources officielles,
  consignée dans [docs/HYPOTHESES.md](docs/HYPOTHESES.md) avec les mesures
  faites sur trente ans de chronique du Lez.
- Trois affirmations corrigées dans la documentation et les commentaires :
  les bornes de régime sont une convention de ce projet et non un usage de
  l'hydrologie officielle ; une hauteur négative ne prouve pas une station
  hors d'eau, puisque les hauteurs sont rapportées au zéro de l'échelle ; le
  rang de débit est surévalué en crue, une pointe étant comparée à des
  moyennes journalières.
- La limite sur les valeurs douteuses dit maintenant ce qu'il en est :
  l'intégration ne filtre ni le statut ni la qualification publiés par
  Hub'Eau.

### Connu, non corrigé

Trois correctifs sont identifiés et mesurés, aucun n'est appliqué : référence
de débit sur `QIXnJ`, filtrage sur `code_statut` et `code_qualification`,
signalement d'une chronique trop courte.

## [0.3.1] - 2026-09-22

### Modifié

- Documentation reprise dans la forme attendue d'une intégration Home
  Assistant : README d'usage avec captures, journal des versions séparé,
  campagne de vérification et dépannage en annexes, modèles d'issue.
- Attribution des données corrigée : les mesures hydrométriques sont produites
  par le Service central Vigicrues et diffusées par Hub'Eau, portail de l'OFB
  et du BRGM, sous Licence Ouverte Etalab.

## [0.3.0] - 2026-09-22

### Ajouté

- La **carte Lovelace est livrée avec l'intégration**, qui la sert elle-même et
  la déclare au frontend. Plus de ressource à ajouter au tableau de bord, plus
  de fichier à copier dans `www/`. Elle apparaît dans le sélecteur de cartes.
- Icône de marque, et validation HACS, hassfest et carte à chaque poussée.

### Modifié

- Le fichier de la carte est servi **sans en-tête de cache** et sous une URL
  portant la version du paquet. Les trente et un jours de `Cache-Control`
  appliqués par défaut aux fichiers statiques masquaient les corrections
  pendant des semaines, y compris dans l'application Companion.
- `manifest.json` déclare ses dépendances `frontend` et `http`.

### Migration depuis 0.2.x

Retirer la ressource Lovelace `hubeau-card.js` et le fichier correspondant dans
`www/community/`. Sans cela l'ancienne copie se charge en plus de la nouvelle,
et c'est la première chargée qui l'emporte : un élément personnalisé ne se
définit qu'une fois par page.

## 0.2.1 - 2026-09-21

### Corrigé

- Le bandeau de la carte retrouve le minimum, la moyenne et le maximum des
  mesures de **hauteur des sept derniers jours**, récupérées directement auprès
  de Hub'Eau toutes les quinze minutes. Les références sur trente ans restent
  réservées au classement du niveau.

## 0.2.0 - 2026-09-21

### Supprimé

- **L'import des anciennes mesures dans le `recorder`.** La chronique ne sert
  plus qu'au calcul des références de la station (percentiles, médiane,
  moyenne, extrêmes), conservées dans un cache local et recalculées tous les
  trente jours.

Les statistiques déjà importées par la version précédente restent en base ;
leur nettoyage est une opération distincte, à faire depuis les outils de Home
Assistant.

## 0.1.0 - 2026-09-21

Première version, installée et vérifiée sur un serveur.

- Configuration par l'interface : rayon autour du domicile, puis station.
- Sept capteurs et trois binaires par station, dont le régime et le rang
  calculés sur la chronique de la station.
- Détection des stations défaillantes : capteur figé, incohérence
  hauteur/débit.
- Carte Lovelace à échelle de percentiles.

Les versions antérieures à la 0.3.0 n'ont pas été publiées en release : le
dépôt était encore privé.

[0.5.0]: https://github.com/benlepa0/hubeau-ha/releases/tag/v0.5.0
[0.4.0]: https://github.com/benlepa0/hubeau-ha/releases/tag/v0.4.0
[0.3.2]: https://github.com/benlepa0/hubeau-ha/releases/tag/v0.3.2
[0.3.1]: https://github.com/benlepa0/hubeau-ha/releases/tag/v0.3.1
[0.3.0]: https://github.com/benlepa0/hubeau-ha/releases/tag/v0.3.0

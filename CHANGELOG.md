# Journal des versions

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le
versionnement est [sémantique](https://semver.org/lang/fr/).

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

[0.3.1]: https://github.com/benlepa0/hubeau-ha/releases/tag/v0.3.1
[0.3.0]: https://github.com/benlepa0/hubeau-ha/releases/tag/v0.3.0

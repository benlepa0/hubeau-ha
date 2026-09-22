# Hub'Eau pour Home Assistant

[![Version][badge-version]][releases]
[![HACS][badge-hacs]][hacs]
[![Validation][badge-ci]][ci]
[![Licence][badge-licence]](https://github.com/benlepa0/hubeau-ha/blob/main/LICENSE)

Suit une station hydrométrique française — hauteur d'eau et débit — et **situe
chaque mesure dans la chronique de cette station** : régime, rang en
percentiles, extrêmes connus. Les données viennent de l'API publique
[Hub'Eau][hubeau], **sans clé ni compte**. Une carte Lovelace est livrée avec
l'intégration.

![La carte, de l'étiage à la crue, et une station en panne](https://raw.githubusercontent.com/benlepa0/hubeau-ha/main/docs/captures/carte-sombre.png)

## Pourquoi

Une hauteur d'eau isolée ne dit rien. « 0,27 m » n'a de sens que rapporté à sa
rivière : c'est un étiage marqué sur le Lez, ce serait un lit à sec sur la
Loire. L'intégration télécharge donc la chronique journalière de la station —
jusqu'à trente ans — et en tire les percentiles qui situent la mesure du
moment :

> **0,272 m** — régime *étiage*, rang **8 %**, dans le quart le plus bas de
> 30,5 ans de mesures. Maximum connu : 4,40 m, le 6 octobre 2014.

Les seuils sont donc **relatifs à chaque station**, jamais absolus.

## Fonctionnalités

- **Régime et rang** calculés sur la chronique de la station, du percentile 0
  au percentile 100 : *étiage sévère* → *crue majeure*.
- **Détection des stations défaillantes.** Une station peut rester joignable
  tout en ayant cessé de mesurer. Deux contrôles la démasquent : moins de
  quatre valeurs distinctes sur douze heures, ou une hauteur nulle
  accompagnée d'un débit franc — signe d'une station hors d'eau dont la courbe
  de tarage invente un débit.
- **Carte Lovelace incluse**, sans ressource à déclarer.
- **Configuration par l'interface** : un rayon autour du domicile, puis une
  station dans la liste triée par distance.
- Aucune écriture dans le `recorder`, aucun import d'anciennes mesures.
- Interface en français et en anglais.

## Installation

### Par HACS

Le dépôt n'est pas encore dans le magasin par défaut ; il s'ajoute en **dépôt
personnalisé**, catégorie *Intégration* :

[![Ouvrir le dépôt dans HACS][badge-my-hacs]][my-hacs]

Ou, à la main : HACS → menu ⋮ → *Dépôts personnalisés* →
`https://github.com/benlepa0/hubeau-ha`, catégorie *Intégration*. Installer
depuis la liste, puis **redémarrer Home Assistant**.

### À la main

Copier `custom_components/hubeau/` dans le dossier `custom_components/` de la
configuration, puis redémarrer Home Assistant.

### Configuration

[![Ajouter l'intégration][badge-my-config]][my-config]

Ou **Paramètres → Appareils et services → Ajouter une intégration →
Hub'Eau**. Tout se fait par l'interface ; rien à écrire dans
`configuration.yaml`. Une entrée par station, autant de stations que voulu.

Le premier démarrage télécharge trente ans d'historique et peut prendre une
trentaine de secondes. C'est voulu : ces références sont ce qui rend les
mesures lisibles. Elles sont ensuite mises en cache et recalculées tous les
trente jours.

## Entités

Par station suivie :

| Entité | Contenu |
|---|---|
| Hauteur d'eau | mètres, avec le rang et la lecture en attributs |
| Débit | m³/s, idem |
| Régime | *étiage sévère* → *crue majeure*, en percentiles de la station |
| Rang sur la chronique | 0 à 100 % |
| Tendance | cm/h, par régression sur 12 h |
| Dernière mesure / Âge de la mesure | fraîcheur de la donnée |
| Crue *(binaire)* | au-delà du percentile 99, soit ~4 jours par an |
| Données obsolètes *(binaire)* | plus de 2 h sans mesure |
| Capteur figé *(binaire)* | station immobile ou incohérente |

La référence porte sur les maximums journaliers pour la hauteur et sur les
moyennes journalières pour le débit ; le rang compare la mesure instantanée à
cette distribution. Les catégories de régime sont des repères propres au
projet, **pas des seuils officiels de vigilance**.

## La carte

Elle vient avec l'intégration et apparaît dans le sélecteur de cartes sous le
nom « Hub'Eau ». Le niveau monte à la hauteur que lui donne son rang, le
courant file à la vitesse du débit, et un bandeau donne les extrêmes des sept
derniers jours.

```yaml
type: custom:hubeau-card
hauteur: sensor.le_lez_a_montferrier_sur_lez_lavalette_hauteur_d_eau
```

Options, échelle en percentiles et thème clair : [docs/CARTE.md](https://github.com/benlepa0/hubeau-ha/blob/main/docs/CARTE.md).

## Dépannage

Entités indisponibles, références absentes, carte qui ne se met pas à jour :
[docs/DEPANNAGE.md](https://github.com/benlepa0/hubeau-ha/blob/main/docs/DEPANNAGE.md).

## Limites connues

- Hub'Eau ne conserve le **pas de temps fin qu'un mois glissant**. Au-delà,
  seules les valeurs journalières existent — d'où des références fondées sur la
  hauteur *maximale* journalière et le débit *moyen* journalier.
- Les références demandent au moins **trois ans** de chronique. Une station
  récente n'en aura pas ; ses mesures restent exposées, sans lecture.
- Les fortes valeurs de la chronique sont souvent qualifiées « douteuses » par
  le producteur : au-delà d'un certain débit, la courbe de tarage est
  extrapolée faute de jaugeage possible en crue.
- Toutes les stations ne publient pas le débit, et certaines cessent de publier
  sans le dire. Voir [docs/VERIFICATIONS.md](https://github.com/benlepa0/hubeau-ha/blob/main/docs/VERIFICATIONS.md) pour ce qui
  a été mesuré sur onze stations, et ce qui reste imparfait.
- **Ce n'est pas un outil d'alerte.** Pour la vigilance officielle, voir
  [Vigicrues](https://www.vigicrues.gouv.fr/).

## Données et attribution

Les données sont diffusées par [Hub'Eau][hubeau], portail d'API du système
d'information sur l'eau, fruit de la collaboration de l'**OFB** et du
**BRGM**. Les données hydrométriques proviennent de la plateforme HYDRO
centrale, opérée par le **Service central Vigicrues**.

Leur réutilisation est régie par la [Licence Ouverte
Etalab](https://www.etalab.gouv.fr/licence-ouverte-open-licence/) : libre et
gratuite, y compris commerciale, à condition de citer la source.

L'intégration interroge l'API toutes les cinq minutes par station et s'annonce
par un en-tête explicite. Hub'Eau est un service public : inutile de
l'interroger plus vite, les mesures ne sont pas publiées plus souvent.

## Contribuer

Les anomalies et les demandes passent par les
[issues](https://github.com/benlepa0/hubeau-ha/issues). Une anomalie utile
donne le **code de la station** (visible dans les attributs de l'entité), la
version de l'intégration et l'extrait de journal correspondant — après un
passage par [docs/DEPANNAGE.md](https://github.com/benlepa0/hubeau-ha/blob/main/docs/DEPANNAGE.md).

Le journal des versions est dans [CHANGELOG.md](https://github.com/benlepa0/hubeau-ha/blob/main/CHANGELOG.md).

## Licence

[MIT](https://github.com/benlepa0/hubeau-ha/blob/main/LICENSE).

<!-- liens -->
[hubeau]: https://hubeau.eaufrance.fr/
[releases]: https://github.com/benlepa0/hubeau-ha/releases
[ci]: https://github.com/benlepa0/hubeau-ha/actions/workflows/validate.yml
[hacs]: https://hacs.xyz/
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=benlepa0&repository=hubeau-ha&category=integration
[my-config]: https://my.home-assistant.io/redirect/config_flow_start/?domain=hubeau
[badge-version]: https://img.shields.io/github/v/release/benlepa0/hubeau-ha?style=for-the-badge
[badge-hacs]: https://img.shields.io/badge/HACS-dépôt%20personnalisé-41BDF5.svg?style=for-the-badge
[badge-ci]: https://img.shields.io/github/actions/workflow/status/benlepa0/hubeau-ha/validate.yml?branch=main&style=for-the-badge&label=validation
[badge-licence]: https://img.shields.io/github/license/benlepa0/hubeau-ha?style=for-the-badge
[badge-my-hacs]: https://my.home-assistant.io/badges/hacs_repository.svg
[badge-my-config]: https://my.home-assistant.io/badges/config_flow_start.svg

<img src="https://raw.githubusercontent.com/benlepa0/hubeau-ha/main/custom_components/hubeau/brand/icon.png" alt="" width="104" align="right">

# Hub'Eau pour Home Assistant

[![Version][badge-version]][releases]
[![HACS][badge-hacs]][hacs]
[![Validation][badge-ci]][ci]
[![Licence][badge-licence]][licence]

Le niveau et le débit d'une rivière française, replacés dans la chronique de
leur propre station : régime, rang en percentiles, extrêmes connus. Les données
viennent de l'API publique [Hub'Eau][hubeau], **sans clé ni compte**, et une
carte Lovelace est livrée avec l'intégration.

![La carte, en étiage, en régime fort et en crue][capture]

## Sommaire

- [Pourquoi](#pourquoi)
- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Entités](#entités)
- [La carte](#la-carte)
- [Exemple d'automatisation](#exemple-dautomatisation)
- [Limites connues](#limites-connues)
- [Données et attribution](#données-et-attribution)
- [Dépannage et contribution](#dépannage-et-contribution)

## Pourquoi

Une hauteur d'eau isolée ne dit rien. « 0,27 m » n'a de sens que rapporté à sa
rivière : c'est un étiage marqué sur le Lez, ce serait un lit à sec sur la
Loire. L'intégration télécharge donc la chronique journalière de la station,
jusqu'à trente ans, et en tire les percentiles qui situent la mesure du moment :

> **0,272 m**, régime *étiage*, rang **8 %**, dans le quart le plus bas de
> 30,5 ans de mesures. Maximum connu : 4,40 m, le 6 octobre 2014.

Les seuils sont donc **relatifs à chaque station**, jamais absolus.

## Fonctionnalités

- **Régime et rang** calculés sur la chronique de la station, du percentile 0
  au percentile 100 : d'*étiage sévère* à *crue majeure*.
- **Détection des stations défaillantes.** Une station peut rester joignable
  tout en ayant cessé de mesurer. Deux contrôles la démasquent : moins de
  quatre valeurs distinctes sur douze heures, ou une hauteur nulle accompagnée
  d'un débit franc, signe d'une station hors d'eau dont la courbe de tarage
  invente un débit.
- **Carte Lovelace incluse**, sans ressource à déclarer dans le tableau de bord.
- **Configuration par l'interface** : un rayon autour du domicile, puis une
  station dans la liste triée par distance. Autant de stations que voulu.
- Aucune écriture dans le `recorder`, aucun import d'anciennes mesures.
- Interface en français et en anglais.

## Installation

### Par HACS

Le dépôt n'est pas encore dans le magasin par défaut. Il s'ajoute en dépôt
personnalisé, catégorie *Intégration* :

[![Ouvrir le dépôt dans HACS][badge-my-hacs]][my-hacs]

1. Ouvrir le lien ci-dessus, ou HACS → menu ⋮ → *Dépôts personnalisés*, puis
   coller `https://github.com/benlepa0/hubeau-ha` en catégorie *Intégration*.
2. Télécharger « Hub'Eau » depuis la liste.
3. Redémarrer Home Assistant.

### À la main

Copier `custom_components/hubeau/` dans le dossier `custom_components/` de la
configuration, puis redémarrer Home Assistant.

### Configuration

[![Ajouter l'intégration][badge-my-config]][my-config]

Ou **Paramètres → Appareils et services → Ajouter une intégration →
Hub'Eau**. Tout se fait par l'interface ; rien à écrire dans
`configuration.yaml`.

Le premier démarrage télécharge trente ans d'historique et peut prendre une
trentaine de secondes. C'est voulu : ces références sont ce qui rend les
mesures lisibles. Elles sont ensuite mises en cache et recalculées tous les
trente jours.

## Entités

Une station suivie donne dix entités :

| Entité | Contenu |
|---|---|
| Hauteur d'eau | mètres, avec le rang et la lecture en attributs |
| Débit | m³/s, idem |
| Régime | d'*étiage sévère* à *crue majeure*, en percentiles de la station |
| Rang sur la chronique | 0 à 100 % |
| Tendance | cm/h, par régression sur 12 h |
| Dernière mesure | horodatage de la dernière valeur publiée |
| Âge de la mesure | minutes écoulées depuis |
| Crue *(binaire)* | au-delà du percentile 99, soit environ 4 jours par an |
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

Les autres capteurs de la station se déduisent du préfixe. Options, échelle en
percentiles et thème clair : [docs/CARTE.md][doc-carte].

![Les cinq états de la carte, en thème clair][capture-claire]

## Exemple d'automatisation

```yaml
automation:
  - alias: Prévenir quand le Lez entre en crue
    triggers:
      - trigger: state
        entity_id: binary_sensor.le_lez_a_montferrier_sur_lez_lavalette_crue
        to: "on"
    actions:
      - action: notify.mobile_app_telephone
        data:
          title: Le Lez est en crue
          message: >
            {{ states('sensor.le_lez_a_montferrier_sur_lez_lavalette_hauteur_d_eau') }} m,
            rang {{ states('sensor.le_lez_a_montferrier_sur_lez_lavalette_rang_sur_la_chronique') }} %.
```

Le capteur *Régime* convient mieux à un affichage, le binaire *Crue* à un
déclenchement. Pour une alerte de sécurité, se reporter à
[Vigicrues](https://www.vigicrues.gouv.fr/) : cette intégration n'en est pas
une.

## Limites connues

- Hub'Eau ne conserve le **pas de temps fin qu'un mois glissant**. Au-delà,
  seules les valeurs journalières existent, d'où des références fondées sur la
  hauteur *maximale* journalière et le débit *moyen* journalier.
- Les références demandent au moins **trois ans** de chronique. Une station
  récente n'en aura pas ; ses mesures restent exposées, sans lecture.
- Les fortes valeurs de la chronique sont souvent qualifiées « douteuses » par
  le producteur : au-delà d'un certain débit, la courbe de tarage est
  extrapolée faute de jaugeage possible en crue.
- Toutes les stations ne publient pas le débit, et certaines cessent de publier
  sans le dire. Ce qui a été mesuré sur onze stations, et les trois défauts de
  diagnostic que la campagne a laissés ouverts : [docs/VERIFICATIONS.md][doc-verif].

## Données et attribution

Les données sont diffusées par [Hub'Eau][hubeau], portail d'API du système
d'information sur l'eau, fruit de la collaboration de l'**OFB** et du **BRGM**.
Les mesures hydrométriques proviennent de la plateforme HYDRO centrale, opérée
par le **Service central Vigicrues**.

Leur réutilisation est régie par la [Licence Ouverte Etalab][etalab] : libre et
gratuite, y compris commerciale, à condition de citer la source.

L'intégration interroge l'API toutes les cinq minutes par station et s'annonce
par un en-tête explicite. Hub'Eau est un service public, et les mesures ne sont
de toute façon pas publiées plus souvent.

## Dépannage et contribution

Entités indisponibles, références absentes, carte qui ne se met pas à jour :
[docs/DEPANNAGE.md][doc-depannage].

Ensuite, les anomalies et les demandes passent par les [issues][issues]. Une
anomalie utile donne le **code de la station**, visible dans les attributs de
l'entité, la version de l'intégration et l'extrait de journal correspondant.

Le journal des versions est dans [CHANGELOG.md][changelog], sous licence
[MIT][licence].

<!-- liens -->
[hubeau]: https://hubeau.eaufrance.fr/
[etalab]: https://www.etalab.gouv.fr/licence-ouverte-open-licence/
[hacs]: https://hacs.xyz/
[releases]: https://github.com/benlepa0/hubeau-ha/releases
[issues]: https://github.com/benlepa0/hubeau-ha/issues
[ci]: https://github.com/benlepa0/hubeau-ha/actions/workflows/validate.yml
[licence]: https://github.com/benlepa0/hubeau-ha/blob/main/LICENSE
[changelog]: https://github.com/benlepa0/hubeau-ha/blob/main/CHANGELOG.md
[doc-carte]: https://github.com/benlepa0/hubeau-ha/blob/main/docs/CARTE.md
[doc-depannage]: https://github.com/benlepa0/hubeau-ha/blob/main/docs/DEPANNAGE.md
[doc-verif]: https://github.com/benlepa0/hubeau-ha/blob/main/docs/VERIFICATIONS.md
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=benlepa0&repository=hubeau-ha&category=integration
[my-config]: https://my.home-assistant.io/redirect/config_flow_start/?domain=hubeau
[capture]: https://raw.githubusercontent.com/benlepa0/hubeau-ha/main/docs/captures/carte.png
[capture-claire]: https://raw.githubusercontent.com/benlepa0/hubeau-ha/main/docs/captures/carte-clair.png
[badge-version]: https://img.shields.io/github/v/release/benlepa0/hubeau-ha?style=for-the-badge&color=41BDF5
[badge-hacs]: https://img.shields.io/badge/HACS-dépôt%20personnalisé-41BDF5.svg?style=for-the-badge
[badge-ci]: https://img.shields.io/github/actions/workflow/status/benlepa0/hubeau-ha/validate.yml?branch=main&style=for-the-badge&label=validation
[badge-licence]: https://img.shields.io/github/license/benlepa0/hubeau-ha?style=for-the-badge&color=41BDF5
[badge-my-hacs]: https://my.home-assistant.io/badges/hacs_repository.svg
[badge-my-config]: https://my.home-assistant.io/badges/config_flow_start.svg

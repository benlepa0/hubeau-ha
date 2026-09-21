"""Versement de la chronique dans l'historique long terme de Home Assistant.

Sans cela, trente ans de mesures ne serviraient qu'une fois -- a calculer onze
percentiles -- puis dormiraient dans un fichier de cache, pendant que Home
Assistant n'afficherait que ce qu'il a lui-meme enregistre depuis
l'installation.

Le `recorder` de Home Assistant tient, a cote de l'historique detaille qu'il
purge au bout de quelques jours, des *statistiques long terme* conservees
indefiniment : une valeur minimale, moyenne et maximale par periode. C'est
exactement la forme des donnees journalieres de Hub'Eau, et
`async_import_statistics` permet de les y verser retroactivement.

Une fois versee, la chronique apparait dans les graphiques natifs de Home
Assistant comme si la station y avait toujours ete suivie.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api import ApiHubEau, ErreurHubEau

_LOGGER = logging.getLogger(__name__)

# Grandeurs journalieres de Hub'Eau, par capteur.
#
# Le debit dispose des trois : moyenne, minimum et maximum du jour. L'ecart
# entre eux est parlant -- le 29 septembre 2014 a Lavalette, la moyenne
# journaliere valait 80 m3/s pour une pointe instantanee a 366.
#
# La hauteur, elle, n'est publiee qu'en maximum journalier. On la verse donc
# telle quelle, minimum et moyenne compris : les trois courbes se superposent
# alors dans les graphiques, ce qui signale a l'oeil qu'il n'y a qu'une valeur
# par jour. C'est d'ailleurs celle qui interesse, puisque ce sont les pointes
# qui font les crues.
GRANDEURS = {
    "hauteur": {"moyenne": "HIXnJ", "minimum": None, "maximum": "HIXnJ",
                "unite": "m", "libelle": "hauteur maximale journalière"},
    "debit": {"moyenne": "QmnJ", "minimum": "QINnJ", "maximum": "QIXnJ",
              "unite": "m³/s", "libelle": "débit journalier"},
}


async def verser(hass: HomeAssistant, api: ApiHubEau, code: str,
                 entity_id: str, grandeur: str, annees: int) -> int:
    """Verse la chronique d'une grandeur. Renvoie le nombre de jours verses."""
    reglage = GRANDEURS[grandeur]
    fin = dt_util.now().date()
    debut = date(fin.year - annees, 1, 1)

    # Chaque grandeur elaboree n'est telechargee qu'une fois, meme quand deux
    # roles pointent dessus : pour la hauteur, moyenne et maximum sont tous
    # deux HIXnJ, et la chronique fait trente ans.
    telecharge: dict[str, dict[date, float]] = {}
    series: dict[str, dict[date, float]] = {}
    for role in ("moyenne", "minimum", "maximum"):
        code_elab = reglage[role]
        if code_elab is None:
            continue
        if code_elab not in telecharge:
            try:
                telecharge[code_elab] = dict(
                    await api.serie_journaliere(code, code_elab, debut, fin))
            except ErreurHubEau as err:
                _LOGGER.warning("%s : chronique %s indisponible (%s)",
                                code, code_elab, err)
                telecharge[code_elab] = {}
        series[role] = telecharge[code_elab]

    if "moyenne" not in series or not series["moyenne"]:
        return 0

    # Chaque journee devient une periode statistique, calee sur minuit local.
    # Home Assistant attend des debuts alignes sur une heure pleine ; minuit
    # en est une, y compris lors des changements d'heure.
    stats: list[StatisticData] = []
    for jour in sorted(series["moyenne"]):
        moyenne = series["moyenne"][jour]
        mini = series.get("minimum", {}).get(jour, moyenne)
        maxi = series.get("maximum", {}).get(jour, moyenne)
        debut_periode = dt_util.as_utc(
            datetime.combine(jour, time.min, tzinfo=dt_util.DEFAULT_TIME_ZONE))
        stats.append(StatisticData(
            start=debut_periode,
            mean=round(moyenne, 4),
            min=round(min(mini, moyenne, maxi), 4),
            max=round(max(mini, moyenne, maxi), 4),
        ))

    metadata = StatisticMetaData(
        # `recorder` designe une statistique rattachee a une entite existante,
        # par opposition a une statistique externe qui vivrait a part.
        source="recorder",
        statistic_id=entity_id,
        name=None,
        unit_of_measurement=reglage["unite"],
        has_mean=True,
        has_sum=False,
    )
    async_import_statistics(hass, metadata, stats)
    _LOGGER.info("%s : %d jours verses dans l'historique long terme (%s)",
                 entity_id, len(stats), reglage["libelle"])
    return len(stats)


async def verser_tout(hass: HomeAssistant, api: ApiHubEau, code: str,
                      entites: dict[str, str], annees: int) -> dict[str, int]:
    """Verse toutes les grandeurs disponibles. `entites` : grandeur -> entity_id."""
    resultats: dict[str, int] = {}
    for grandeur, entity_id in entites.items():
        if grandeur not in GRANDEURS or not entity_id:
            continue
        try:
            resultats[grandeur] = await verser(
                hass, api, code, entity_id, grandeur, annees)
        except Exception:                      # noqa: BLE001
            # Un echec de versement ne doit pas empecher l'integration de
            # fonctionner : les mesures en direct restent le principal.
            _LOGGER.exception("%s : versement de %s impossible", code, grandeur)
            resultats[grandeur] = 0
    return resultats

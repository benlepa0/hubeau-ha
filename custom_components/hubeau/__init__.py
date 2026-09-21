"""Integration Hub'Eau : hydrometrie des cours d'eau francais.

Les donnees viennent de l'API publique Hub'Eau, operee par l'Office francais
de la biodiversite, sans cle ni compte. Ce que cette integration ajoute aux
mesures brutes, c'est leur *lecture* : une hauteur ne veut rien dire seule,
elle se lit rapportee a la chronique de sa propre station.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import ANNEES_REFERENCE, CONF_COURS_EAU, CONF_LIBELLE, CONF_STATION, DOMAINE
from .coordinator import CoordinateurHubEau

_LOGGER = logging.getLogger(__name__)

PLATEFORMES: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type EntreeHubEau = ConfigEntry[CoordinateurHubEau]


async def async_setup_entry(hass: HomeAssistant, entry: EntreeHubEau) -> bool:
    coordinateur = CoordinateurHubEau(
        hass, entry,
        code=entry.data[CONF_STATION],
        libelle=entry.data.get(CONF_LIBELLE, entry.title),
        cours_eau=entry.data.get(CONF_COURS_EAU, ""),
    )
    # Le premier rafraichissement telecharge trente ans d'historique : il peut
    # durer une trentaine de secondes, et c'est voulu -- les statistiques sont
    # ce qui rend les mesures lisibles, mieux vaut les avoir des le depart.
    await coordinateur.async_config_entry_first_refresh()
    entry.runtime_data = coordinateur
    await hass.config_entries.async_forward_entry_setups(entry, PLATEFORMES)
    entry.async_on_unload(entry.add_update_listener(_recharger))

    # Le versement de la chronique dans l'historique long terme se fait en
    # tache de fond : il porte sur des milliers de journees et ne doit pas
    # retarder le demarrage. Il n'a lieu qu'une fois par station.
    hass.async_create_background_task(
        _verser_historique(hass, entry, coordinateur),
        name=f"{DOMAINE} historique {coordinateur.code}",
    )
    return True


async def _verser_historique(hass: HomeAssistant, entry: EntreeHubEau,
                             coordinateur: CoordinateurHubEau) -> None:
    from homeassistant.helpers import entity_registry as er

    from . import historique

    if await coordinateur.historique_deja_verse():
        return

    registre = er.async_get(hass)
    entites: dict[str, str] = {}
    prefixe = f"{coordinateur.code}_"
    for entree in er.async_entries_for_config_entry(registre, entry.entry_id):
        # L'identifiant unique vaut "<code station>_<cle>". On retire le
        # prefixe plutot que de couper au dernier souligne : la cle
        # "tendance_hauteur" se termine elle aussi par "hauteur", et versait
        # la chronique des niveaux dans le capteur de tendance.
        if not entree.unique_id.startswith(prefixe):
            continue
        cle = entree.unique_id[len(prefixe):]
        if cle in ("hauteur", "debit"):
            entites[cle] = entree.entity_id
    _LOGGER.debug("%s : entites a alimenter %s", coordinateur.code, entites)

    if not entites:
        _LOGGER.debug("%s : aucune entite a alimenter", coordinateur.code)
        return

    resultats = await historique.verser_tout(
        hass, coordinateur.api, coordinateur.code, entites, ANNEES_REFERENCE)
    if any(resultats.values()):
        await coordinateur.marquer_historique_verse(resultats)


async def async_unload_entry(hass: HomeAssistant, entry: EntreeHubEau) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATEFORMES)


async def _recharger(hass: HomeAssistant, entry: EntreeHubEau) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

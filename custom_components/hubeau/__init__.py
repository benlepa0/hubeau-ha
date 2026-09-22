"""Integration Hub'Eau : hydrometrie des cours d'eau francais.

Les donnees viennent de l'API publique Hub'Eau, operee par l'Office francais
de la biodiversite, sans cle ni compte. Ce que cette integration ajoute aux
mesures brutes, c'est leur *lecture* : une hauteur ne veut rien dire seule,
elle se lit rapportee a la chronique de sa propre station.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_COURS_EAU, CONF_LIBELLE, CONF_STATION
from .coordinator import CoordinateurHubEau

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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EntreeHubEau) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATEFORMES)


async def _recharger(hass: HomeAssistant, entry: EntreeHubEau) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

"""Integration Hub'Eau : hydrometrie des cours d'eau francais.

Les donnees viennent de l'API publique Hub'Eau, operee par l'Office francais
de la biodiversite, sans cle ni compte. Ce que cette integration ajoute aux
mesures brutes, c'est leur *lecture* : une hauteur ne veut rien dire seule,
elle se lit rapportee a la chronique de sa propre station.
"""

from __future__ import annotations

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    CLE_CARTE,
    CONF_COURS_EAU,
    CONF_LIBELLE,
    CONF_STATION,
    DOMAIN,
    FICHIER_CARTE,
    URL_CARTE,
)
from .coordinator import CoordinateurHubEau

PLATEFORMES: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type EntreeHubEau = ConfigEntry[CoordinateurHubEau]


async def async_setup_entry(hass: HomeAssistant, entry: EntreeHubEau) -> bool:
    await _servir_la_carte(hass)

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


async def _servir_la_carte(hass: HomeAssistant) -> None:
    """Publie la carte Lovelace livree avec l'integration.

    Le fichier est servi depuis le dossier du composant et declare au frontend
    comme module supplementaire : la carte est donc disponible dans le
    selecteur de cartes sans que l'utilisateur ait a ajouter une ressource au
    tableau de bord.

    Deux precautions tirees de l'experience :

    - `cache_headers=False`. Home Assistant sert par defaut ses fichiers
      statiques avec un `Cache-Control` de trente et un jours. La carte etait
      alors servie depuis le cache du navigateur, et surtout de l'application
      Companion, longtemps apres une mise a jour ; on croyait que rien n'avait
      change. Sans en-tete de cache, le client revalide.
    - l'URL porte le numero de version du paquet, ce qui suffit a distinguer
      deux versions meme d'un cache tenace.

    L'enregistrement n'a lieu qu'une fois par demarrage : le routeur HTTP
    refuserait un second chemin statique identique, et le frontend chargerait
    la carte deux fois.
    """
    if hass.data.get(CLE_CARTE):
        return
    hass.data[CLE_CARTE] = True

    integration = await async_get_integration(hass, DOMAIN)
    fichier = integration.file_path / FICHIER_CARTE
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_CARTE, str(fichier), False)]
    )
    add_extra_js_url(hass, f"{URL_CARTE}?v={integration.version}")

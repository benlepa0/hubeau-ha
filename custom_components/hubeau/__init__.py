"""Integration Hub'Eau : hydrometrie des cours d'eau francais.

Les donnees viennent de l'API publique Hub'Eau -- portail de l'OFB et du BRGM,
sans cle ni compte -- et sont produites par le Service central Vigicrues. Ce
que cette integration ajoute aux mesures brutes, c'est leur *lecture* : une
hauteur ne veut rien dire seule, elle se lit rapportee a la chronique de sa
propre station.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

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
    # Aucun appel reseau ici : l'etat vient du disque, et Hub'Eau n'est
    # interroge qu'une fois les entites en place. Jusqu'a la 0.4.0, la mise en
    # place attendait le premier rafraichissement, et avec lui tout Home
    # Assistant : une minute au demarrage du 2026-09-22, et davantage quand
    # l'API laissait pendre une requete.
    await coordinateur.async_charger()
    entry.runtime_data = coordinateur
    await hass.config_entries.async_forward_entry_setups(entry, PLATEFORMES)
    entry.async_on_unload(entry.add_update_listener(_recharger))
    entry.async_create_background_task(
        hass, coordinateur.async_refresh(), f"{DOMAIN} premier cycle")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EntreeHubEau) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATEFORMES):
        return False
    await entry.runtime_data.async_enregistrer()
    return True


async def _recharger(hass: HomeAssistant, entry: EntreeHubEau) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _servir_la_carte(hass: HomeAssistant) -> None:
    """Publie la carte Lovelace livree avec l'integration.

    Le fichier est servi depuis le dossier du composant et declare au frontend
    comme module supplementaire : la carte est donc disponible dans le
    selecteur de cartes sans que l'utilisateur ait a ajouter une ressource au
    tableau de bord.

    L'URL porte une empreinte du *contenu* du fichier, et non le numero de
    version du paquet. Les deux avaient diverge : la carte etait passee en
    0.4.1 alors que le manifeste restait en 0.4.0, et elle etait donc servie
    sous une URL inchangee, que le navigateur et surtout l'application
    Companion gardaient en cache. Une empreinte change a chaque edition de la
    carte et a elle seule : le cache de trente et un jours que Home Assistant
    pose sur ses fichiers statiques redevient sans risque, et la carte ne se
    retelecharge plus a chaque ouverture de l'interface.

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
        [StaticPathConfig(URL_CARTE, str(fichier), True)]
    )
    empreinte = await hass.async_add_executor_job(_empreinte, fichier)
    add_extra_js_url(hass, f"{URL_CARTE}?v={empreinte}")


def _empreinte(fichier: Path) -> str:
    """Douze caracteres tires du contenu de la carte, pour l'URL.

    Lu dans un fil d'execution : la boucle d'evenements ne doit pas toucher au
    disque.
    """
    return hashlib.sha256(fichier.read_bytes()).hexdigest()[:12]

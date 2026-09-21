"""Configuration par l'interface : choix d'une station hydrometrique."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import ApiHubEau, ErreurHubEau
from .const import (
    CONF_COURS_EAU,
    CONF_LIBELLE,
    CONF_RAYON_KM,
    CONF_STATION,
    DOMAINE,
    RAYON_DEFAUT_KM,
)

_LOGGER = logging.getLogger(__name__)


class FluxConfiguration(ConfigFlow, domain=DOMAINE):
    """Deux etapes : on cherche autour de chez soi, puis on choisit."""

    VERSION = 1

    def __init__(self) -> None:
        self._stations: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        erreurs: dict[str, str] = {}

        if user_input is not None:
            rayon = float(user_input[CONF_RAYON_KM])
            api = ApiHubEau(async_get_clientsession(self.hass))
            try:
                self._stations = await api.stations_proches(
                    self.hass.config.longitude, self.hass.config.latitude, rayon)
            except ErreurHubEau as err:
                _LOGGER.error("recherche de stations impossible : %s", err)
                erreurs["base"] = "connexion"
            else:
                if not self._stations:
                    erreurs["base"] = "aucune_station"
                else:
                    return await self.async_step_station()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_RAYON_KM, default=RAYON_DEFAUT_KM):
                    NumberSelector(NumberSelectorConfig(
                        min=1, max=200, step=1,
                        unit_of_measurement="km",
                        mode=NumberSelectorMode.SLIDER)),
            }),
            errors=erreurs,
            description_placeholders={
                "latitude": f"{self.hass.config.latitude:.4f}",
                "longitude": f"{self.hass.config.longitude:.4f}",
            },
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            code = user_input[CONF_STATION]
            station = next(s for s in self._stations
                           if s["code_station"] == code)
            # Une meme station ne doit pas etre ajoutee deux fois.
            await self.async_set_unique_id(code)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=station["libelle_station"],
                data={
                    CONF_STATION: code,
                    CONF_LIBELLE: station["libelle_station"],
                    CONF_COURS_EAU: station.get("libelle_cours_eau") or "",
                },
            )

        deja = {e.unique_id for e in self._async_current_entries()}
        options = [
            SelectOptionDict(
                value=s["code_station"],
                # La distance figure dans le libelle : c'est le critere de
                # choix quand plusieurs stations bordent le meme cours d'eau.
                label=f"{s['libelle_station']} — {s['distance_km']} km",
            )
            for s in self._stations if s["code_station"] not in deja
        ]
        if not options:
            return self.async_abort(reason="toutes_configurees")

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema({
                vol.Required(CONF_STATION): SelectSelector(
                    SelectSelectorConfig(options=options,
                                         mode=SelectSelectorMode.DROPDOWN)),
            }),
            description_placeholders={"nombre": str(len(options))},
        )

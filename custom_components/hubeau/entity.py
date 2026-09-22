"""Base commune aux entites : rattachement a l'appareil « station »."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAINE, FABRICANT
from .coordinator import CoordinateurHubEau


class EntiteHubEau(CoordinatorEntity[CoordinateurHubEau]):
    """Toutes les entites d'une station sont regroupees sous un appareil."""

    _attr_has_entity_name = True

    def __init__(self, coordinateur: CoordinateurHubEau, cle: str) -> None:
        super().__init__(coordinateur)
        self._attr_unique_id = f"{coordinateur.code}_{cle}"
        etat = coordinateur.etat
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAINE, coordinateur.code)},
            name=etat.libelle,
            manufacturer=FABRICANT,
            model=etat.cours_eau or "Station hydrométrique",
            serial_number=coordinateur.code,
            configuration_url=(
                "https://www.vigicrues.gouv.fr/"
                f"?CdStationHydro={coordinateur.code}"
            ),
        )


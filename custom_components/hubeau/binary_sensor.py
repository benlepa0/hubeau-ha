"""Capteurs binaires : sante de la station et regime de crue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EntreeHubEau
from .coordinator import CoordinateurHubEau, EtatStation
from .entity import EntiteHubEau


@dataclass(frozen=True, kw_only=True)
class DescriptionBinaire(BinarySensorEntityDescription):
    valeur: Callable[[EtatStation], bool | None]
    toujours_disponible: bool = False


BINAIRES: tuple[DescriptionBinaire, ...] = (
    DescriptionBinaire(
        key="crue",
        translation_key="crue",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:home-flood",
        # Au-dela du percentile 99 de sa propre chronique : environ quatre
        # jours par an. Un seuil en valeur absolue n'aurait pas de sens d'une
        # riviere a l'autre.
        valeur=lambda e: (None if e.principale.rang is None
                          else e.principale.rang >= 99.0),
    ),
    DescriptionBinaire(
        key="obsolete",
        translation_key="obsolete",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:cloud-off-outline",
        valeur=lambda e: e.obsolete,
        toujours_disponible=True,
    ),
    DescriptionBinaire(
        key="capteur_fige",
        translation_key="capteur_fige",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:pause-octagon-outline",
        # Une station peut repondre tout en ayant cesse de mesurer, ou
        # annoncer un debit pour une hauteur nulle.
        valeur=lambda e: e.suspecte,
        toujours_disponible=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: EntreeHubEau, ajouter: AddEntitiesCallback
) -> None:
    ajouter(BinaireHubEau(entry.runtime_data, d) for d in BINAIRES)


class BinaireHubEau(EntiteHubEau, BinarySensorEntity):
    entity_description: DescriptionBinaire

    def __init__(self, coordinateur: CoordinateurHubEau,
                 description: DescriptionBinaire) -> None:
        super().__init__(coordinateur, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.valeur(self.coordinator.etat)

    @property
    def available(self) -> bool:
        if self.entity_description.toujours_disponible:
            return self.coordinator.last_update_success
        return super().available

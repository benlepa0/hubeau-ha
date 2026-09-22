"""Capteurs d'une station hydrometrique."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfTime, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EntreeHubEau
from .coordinator import CoordinateurHubEau, EtatStation
from .entity import EntiteHubEau

# Hub'Eau donne les debits en m3/s. Home Assistant ne connait pas cette unite
# pour la classe `volume_flow_rate` ; on laisse donc le capteur sans classe
# d'appareil plutot que de convertir en m3/h, qui ne se lit pas pour une
# riviere.
UNITE_DEBIT = "m³/s"


@dataclass(frozen=True, kw_only=True)
class DescriptionHubEau(SensorEntityDescription):
    """Description d'un capteur, avec sa facon de lire l'etat."""

    valeur: Callable[[EtatStation], float | str | None]
    attributs: Callable[[EtatStation], dict] | None = None


# Ce que la reference contient vraiment, grandeur elaboree par grandeur.
NATURE_REFERENCE = {
    "HIXnJ": "maximums_journaliers",
    "QIXnJ": "pointes_journalieres",
    "QmnJ": "moyennes_journalieres",
}


def _attributs_grandeur(nom: str) -> Callable[[EtatStation], dict]:
    def lire(etat: EtatStation) -> dict:
        g = getattr(etat, nom)
        recentes = etat.sept_jours if nom == "hauteur" else {}
        if g.stats is None:
            return dict(recentes)
        return {
            **recentes,
            "rang_percentile": g.rang,
            "regime": g.niveau,
            "lecture": g.commentaire,
            "mediane_30_ans": g.stats.percentiles.get("50"),
            "minimum_reference": g.stats.minimum,
            "moyenne_reference": g.stats.moyenne,
            "maximum_reference": g.stats.maximum,
            "debut_reference": g.stats.debut,
            "fin_reference": g.stats.fin,
            "jours_reference": g.stats.jours,
            "nature_reference": NATURE_REFERENCE.get(
                g.stats.source, "inconnue"),
            "grandeur_reference": g.stats.source,
            "reference_fiable_jusqu_au_percentile": g.stats.percentile_fiable_max,
            "maximum_connu": g.stats.maximum,
            "maximum_connu_le": g.stats.maximum_date,
            "annees_de_reference": g.stats.annees,
            "capteur_fige": g.figee,
        }
    return lire


CAPTEURS: tuple[DescriptionHubEau, ...] = (
    DescriptionHubEau(
        key="hauteur",
        translation_key="hauteur",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:waves-arrow-up",
        valeur=lambda e: e.hauteur.valeur,
        attributs=_attributs_grandeur("hauteur"),
    ),
    DescriptionHubEau(
        key="debit",
        translation_key="debit",
        native_unit_of_measurement=UNITE_DEBIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:waves",
        valeur=lambda e: e.debit.valeur,
        attributs=_attributs_grandeur("debit"),
    ),
    DescriptionHubEau(
        key="regime",
        translation_key="regime",
        device_class=SensorDeviceClass.ENUM,
        options=["etiage_severe", "etiage", "normal", "soutenu",
                 "fort", "crue", "crue_majeure", "indisponible"],
        icon="mdi:information-outline",
        valeur=lambda e: e.principale.niveau or "indisponible",
        attributs=lambda e: {
            "lecture": e.principale.commentaire,
            "rang_percentile": e.principale.rang,
        },
    ),
    DescriptionHubEau(
        key="rang",
        translation_key="rang",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:sort-numeric-variant",
        valeur=lambda e: e.principale.rang,
    ),
    DescriptionHubEau(
        key="tendance_hauteur",
        translation_key="tendance_hauteur",
        native_unit_of_measurement="cm/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:trending-up",
        # La tendance est plus parlante en centimetres par heure : une riviere
        # qui monte de deux centimetres par heure se comprend tout de suite.
        valeur=lambda e: (None if e.hauteur.tendance_par_heure is None
                          else e.hauteur.tendance_par_heure * 100.0),
    ),
    DescriptionHubEau(
        key="derniere_mesure",
        translation_key="derniere_mesure",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        valeur=lambda e: e.derniere_mesure,
    ),
    DescriptionHubEau(
        key="fraicheur",
        translation_key="fraicheur",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:timer-sand",
        valeur=lambda e: e.minutes_depuis_mesure,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: EntreeHubEau, ajouter: AddEntitiesCallback
) -> None:
    coordinateur = entry.runtime_data
    ajouter(CapteurHubEau(coordinateur, d) for d in CAPTEURS)


class CapteurHubEau(EntiteHubEau, SensorEntity):
    entity_description: DescriptionHubEau

    def __init__(self, coordinateur: CoordinateurHubEau,
                 description: DescriptionHubEau) -> None:
        super().__init__(coordinateur, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.valeur(self.coordinator.etat)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.attributs is None:
            return None
        return self.entity_description.attributs(self.coordinator.etat)

"""Coordination des appels a Hub'Eau pour une station."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import statistiques as stats_mod
from .api import ApiHubEau, ErreurHubEau
from .const import (
    ANNEES_REFERENCE,
    DOMAINE,
    ELAB_DEBIT_MOYEN,
    ELAB_HAUTEUR_MAX,
    GRANDEUR_DEBIT,
    GRANDEUR_HAUTEUR,
    HEURES_DETECTION_FIGE,
    INTERVALLE,
    INTERVALLE_STATISTIQUES,
    MINUTES_AVANT_OBSOLESCENCE,
)

_LOGGER = logging.getLogger(__name__)

VERSION_STOCKAGE = 1


@dataclass
class Grandeur:
    """Etat courant d'une grandeur mesuree, et sa lecture statistique."""

    valeur: float | None = None
    date: datetime | None = None
    tendance_par_heure: float | None = None
    figee: bool = False
    stats: stats_mod.Statistiques | None = None

    @property
    def rang(self) -> float | None:
        if self.valeur is None or self.stats is None:
            return None
        return round(self.stats.rang(self.valeur), 1)

    @property
    def niveau(self) -> str | None:
        if self.valeur is None or self.stats is None:
            return None
        return self.stats.niveau(self.valeur)

    @property
    def commentaire(self) -> str | None:
        if self.valeur is None or self.stats is None:
            return None
        return self.stats.commentaire(self.valeur)


@dataclass
class EtatStation:
    """Ce que l'integration expose pour une station."""

    code: str
    libelle: str
    cours_eau: str
    latitude: float | None = None
    longitude: float | None = None
    hauteur: Grandeur = field(default_factory=Grandeur)
    debit: Grandeur = field(default_factory=Grandeur)

    @property
    def derniere_mesure(self) -> datetime | None:
        dates = [g.date for g in (self.hauteur, self.debit) if g.date]
        return max(dates) if dates else None

    @property
    def minutes_depuis_mesure(self) -> float | None:
        d = self.derniere_mesure
        if d is None:
            return None
        return (dt_util.utcnow() - d).total_seconds() / 60.0

    @property
    def obsolete(self) -> bool:
        m = self.minutes_depuis_mesure
        return m is None or m > MINUTES_AVANT_OBSOLESCENCE

    @property
    def figee(self) -> bool:
        return self.hauteur.figee or self.debit.figee

    @property
    def incoherente(self) -> bool:
        """Debit annonce alors que la hauteur est nulle : station hors d'eau."""
        from .statistiques import hauteur_incoherente
        return hauteur_incoherente(self.hauteur.valeur, self.debit.valeur)

    @property
    def suspecte(self) -> bool:
        return self.figee or self.incoherente

    @property
    def principale(self) -> Grandeur:
        """La grandeur qui porte la lecture d'ensemble.

        La hauteur est preferee quand elle existe : c'est elle qui a du sens
        pour un riverain, et elle est mesuree directement, la ou le debit
        resulte d'une courbe de tarage extrapolee en crue.
        """
        return self.hauteur if self.hauteur.valeur is not None else self.debit


class CoordinateurHubEau(DataUpdateCoordinator[EtatStation]):
    """Interroge une station et tient a jour ses statistiques de reference."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, code: str,
                 libelle: str, cours_eau: str) -> None:
        super().__init__(
            hass, _LOGGER, name=f"{DOMAINE} {code}", update_interval=INTERVALLE,
            config_entry=entry,
        )
        self.code = code
        self.api = ApiHubEau(async_get_clientsession(hass))
        self.etat = EtatStation(code=code, libelle=libelle, cours_eau=cours_eau)
        self._store: Store = Store(hass, VERSION_STOCKAGE,
                                   f"{DOMAINE}.{code}.statistiques")
        self._stats_chargees = False
        self._stats_le: datetime | None = None

    # -- statistiques de reference -----------------------------------------

    async def _charger_statistiques(self) -> None:
        """Lit les statistiques en cache, ou les recalcule si elles manquent.

        Le calcul demande une dizaine d'appels a l'API pour trente ans de
        valeurs journalieres : il ne se fait qu'a l'installation puis une fois
        par mois, jamais dans le cycle de rafraichissement courant.
        """
        if self._stats_chargees and self._stats_le and (
                dt_util.utcnow() - self._stats_le < INTERVALLE_STATISTIQUES):
            return

        cache = await self._store.async_load()
        if cache:
            calcule_le = dt_util.parse_datetime(cache.get("calcule_le", "")) \
                if cache.get("calcule_le") else None
            frais = calcule_le and (dt_util.utcnow() - calcule_le
                                    < INTERVALLE_STATISTIQUES)
            for nom, grandeur in (("hauteur", self.etat.hauteur),
                                  ("debit", self.etat.debit)):
                brut = cache.get(nom)
                if brut:
                    grandeur.stats = stats_mod.Statistiques.depuis_dict(brut)
            self._stats_chargees = True
            self._stats_le = calcule_le
            if frais:
                return

        await self._recalculer_statistiques()

    async def _recalculer_statistiques(self) -> None:
        fin = dt_util.now().date()
        debut = date(fin.year - ANNEES_REFERENCE, 1, 1)
        paquet: dict[str, Any] = {"calcule_le": dt_util.utcnow().isoformat()}
        for nom, grandeur_elab, cible in (
            ("hauteur", ELAB_HAUTEUR_MAX, self.etat.hauteur),
            ("debit", ELAB_DEBIT_MOYEN, self.etat.debit),
        ):
            try:
                serie = await self.api.serie_journaliere(
                    self.code, grandeur_elab, debut, fin)
            except ErreurHubEau as err:
                _LOGGER.warning("statistiques %s indisponibles pour %s : %s",
                                nom, self.code, err)
                continue
            s = stats_mod.calculer(serie)
            if s is not None:
                cible.stats = s
                paquet[nom] = s.vers_dict()
                _LOGGER.info(
                    "%s : statistiques %s sur %d jours (%.1f ans), "
                    "mediane %.3f, maximum %.3f le %s",
                    self.code, nom, s.jours, s.annees,
                    s.percentiles["50"], s.maximum, s.maximum_date)
        await self._store.async_save(paquet)
        self._stats_chargees = True
        self._stats_le = dt_util.utcnow()

    # -- cycle courant ------------------------------------------------------

    async def _async_update_data(self) -> EtatStation:
        try:
            await self._charger_statistiques()
            for grandeur_code, cible in ((GRANDEUR_HAUTEUR, self.etat.hauteur),
                                         (GRANDEUR_DEBIT, self.etat.debit)):
                mesure = await self.api.derniere_mesure(self.code, grandeur_code)
                if mesure is None:
                    cible.valeur = None
                    continue
                cible.valeur = round(mesure["valeur"], 3)
                cible.date = mesure["date"]

                serie = await self.api.serie_recente(
                    self.code, grandeur_code, heures=HEURES_DETECTION_FIGE)
                cible.tendance_par_heure = stats_mod.tendance(serie)
                cible.figee = stats_mod.est_figee(serie)
                if cible.figee:
                    _LOGGER.debug("%s : %s figee depuis au moins %d h",
                                  self.code, grandeur_code, HEURES_DETECTION_FIGE)
        except ErreurHubEau as err:
            raise UpdateFailed(str(err)) from err
        return self.etat

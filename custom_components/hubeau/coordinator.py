"""Coordination des appels a Hub'Eau pour une station."""

from __future__ import annotations

import asyncio
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
    ELAB_DEBIT_POINTE,
    DOMAINE,
    ELAB_DEBIT_MOYEN,
    ELAB_HAUTEUR_MAX,
    GRANDEUR_DEBIT,
    GRANDEUR_HAUTEUR,
    HEURES_DETECTION_FIGE,
    INTERVALLE,
    INTERVALLE_STATISTIQUES,
    JOURS_TAMPON,
    MINUTES_AVANT_OBSOLESCENCE,
    RECOUVREMENT,
)

_LOGGER = logging.getLogger(__name__)

VERSION_STOCKAGE = 1

# Le tampon des mesures recentes n'est ecrit sur disque qu'au plus toutes les
# demi-heures, et a l'arret de Home Assistant : il ne sert qu'a repartir de la
# ou l'on en etait, pas a archiver.
DELAI_ECRITURE_TAMPON = 1800


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
    sept_jours: dict = field(default_factory=dict)
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
    """Interroge une station et tient a jour ses statistiques de reference.

    Strategie, depuis la version 0.5.0 :

    - **rien n'attend le reseau au demarrage.** Les references de trente ans
      et les mesures des sept derniers jours sont relues sur le disque ; les
      entites ont une valeur des leur creation. Hub'Eau est ensuite interroge
      en arriere-plan. Avant, la mise en place enchainait quatre a six appels,
      et un seul pouvait pendre deux minutes : Home Assistant attendait.
    - **une seule requete par cycle**, hauteur et debit ensemble, limitee a ce
      qui est arrive depuis la derniere mesure connue. Tendance, detection
      d'un capteur fige et resume sur sept jours se calculent sur le tampon.
    - **les references se recalculent en tache de fond**, a l'installation
      puis tous les trente jours, sans jamais retenir les mesures du moment.
    """

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
        self._store_mesures: Store = Store(hass, VERSION_STOCKAGE,
                                           f"{DOMAINE}.{code}.mesures")
        self._stats_le: datetime | None = None
        self._calcul_en_cours = False
        self._prochain_essai: datetime | None = None
        # Mesures au pas fin, par grandeur : date -> valeur.
        self._mesures: dict[str, dict[datetime, float]] = {
            GRANDEUR_HAUTEUR: {}, GRANDEUR_DEBIT: {}}

    # -- demarrage ----------------------------------------------------------

    async def async_charger(self) -> None:
        """Relit sur le disque ce que les executions precedentes ont appris.

        Ne touche pas au reseau. Si les references manquent ou ont plus de
        trente jours, leur calcul est lance en arriere-plan.
        """
        cache, tampon = await asyncio.gather(
            self._store.async_load(), self._store_mesures.async_load())
        complet = False
        if cache:
            complet = True
            for nom, grandeur in (("hauteur", self.etat.hauteur),
                                  ("debit", self.etat.debit)):
                brut = cache.get(nom)
                if brut:
                    grandeur.stats = stats_mod.Statistiques.depuis_dict(brut)
                    # Un cache anterieur a la 0.4.0 ne dit pas de quelle
                    # grandeur il vient : on le garde en attendant mieux.
                    if (grandeur.stats.moyenne is None
                            or grandeur.stats.source is None):
                        complet = False
            if cache.get("calcule_le"):
                self._stats_le = dt_util.parse_datetime(cache["calcule_le"])
        if not complet:
            self._stats_le = None

        if tampon:
            for g, points in tampon.items():
                if g in self._mesures:
                    self._mesures[g] = {
                        dt_util.utc_from_timestamp(t): v for t, v in points}
            self._deduire(dt_util.utcnow())
        self._verifier_statistiques()

    async def async_enregistrer(self) -> None:
        """Ecrit le tampon tout de suite : appele au dechargement."""
        await self._store_mesures.async_save(self._tampon_serialise())

    def _tampon_serialise(self) -> dict:
        return {g: [[int(d.timestamp()), v] for d, v in sorted(m.items())]
                for g, m in self._mesures.items()}

    # -- statistiques de reference -----------------------------------------

    def _verifier_statistiques(self) -> None:
        """Lance le recalcul en arriere-plan si les references sont perimees."""
        maintenant = dt_util.utcnow()
        if self._calcul_en_cours or (self._prochain_essai
                                     and maintenant < self._prochain_essai):
            return
        if self._stats_le and (dt_util.utcnow() - self._stats_le
                               < INTERVALLE_STATISTIQUES):
            return
        self._calcul_en_cours = True
        self.config_entry.async_create_background_task(
            self.hass, self._recalculer_statistiques(),
            f"{DOMAINE} {self.code} references")

    async def _recalculer_statistiques(self) -> None:
        """Trente ans de valeurs journalieres, une requete par grandeur.

        En cas d'echec, les references precedentes restent en place et le
        calcul est retente une heure plus tard : inutile de redemander trente
        ans de donnees toutes les cinq minutes a une API qui peine.
        """
        try:
            await self._calculer()
        except Exception as err:
            self._prochain_essai = dt_util.utcnow() + timedelta(hours=1)
            _LOGGER.warning("%s : references non recalculees (%s), nouvel "
                            "essai dans une heure", self.code, err)
        finally:
            self._calcul_en_cours = False

    async def _calculer(self) -> None:
        fin = dt_util.now().date()
        debut = date(fin.year - ANNEES_REFERENCE, 1, 1)
        paquet: dict[str, Any] = {"calcule_le": dt_util.utcnow().isoformat()}
        echec = False
        for nom, grandeurs, cible in (
            ("hauteur", (ELAB_HAUTEUR_MAX,), self.etat.hauteur),
            # La pointe d'abord : c'est une mesure instantanee qu'on vient
            # classer. La moyenne journaliere ne sert que de repli, pour les
            # stations qui ne publient pas QIXnJ.
            ("debit", (ELAB_DEBIT_POINTE, ELAB_DEBIT_MOYEN), self.etat.debit),
        ):
            s = None
            for grandeur_elab in grandeurs:
                try:
                    serie, ecartes = await self.api.serie_journaliere(
                        self.code, grandeur_elab, debut, fin)
                except ErreurHubEau as err:
                    _LOGGER.warning("statistiques %s indisponibles pour %s : %s",
                                    nom, self.code, err)
                    echec = True
                    break
                s = stats_mod.calculer(serie, source=grandeur_elab)
                if s is not None:
                    break
                if ecartes and len(serie) + ecartes >= stats_mod.JOURS_MINIMUM:
                    # Le cas existe : le maregraphe de Port-Camargue ne publie
                    # que des donnees brutes, le Lirou au Triadou des valeurs
                    # que le producteur ne valide pas. Mieux vaut pas de
                    # reference qu'une reference batie sur ce qu'il recuse.
                    _LOGGER.warning(
                        "%s %s : chronique assez longue (%d jours) mais %d "
                        "valeurs ecartees faute de statut ou de qualification "
                        "suffisants ; aucune reference calculee",
                        self.code, grandeur_elab, len(serie) + ecartes, ecartes)
                if grandeur_elab is not grandeurs[-1]:
                    _LOGGER.info(
                        "%s : %s trop court, repli sur la grandeur suivante",
                        self.code, grandeur_elab)
                await asyncio.sleep(2.0)     # menagement du service public
            if s is not None:
                cible.stats = s
                paquet[nom] = s.vers_dict()
                _LOGGER.info(
                    "%s : statistiques %s sur %d jours (%.1f ans) depuis %s, "
                    "mediane %.3f, maximum %.3f le %s, fiables jusqu'au "
                    "percentile %s",
                    self.code, nom, s.jours, s.annees, s.source,
                    s.percentiles["50"], s.maximum, s.maximum_date,
                    s.percentile_fiable_max)
            elif cible.stats is not None and echec:
                # Une panne reseau ne doit pas effacer une reference acquise.
                paquet[nom] = cible.stats.vers_dict()
        if echec:
            # On garde l'ancienne date de calcul : un essai suivant retentera.
            raise ErreurHubEau("chronique journaliere incomplete")
        await self._store.async_save(paquet)
        self._stats_le = dt_util.utcnow()
        self.async_update_listeners()

    # -- cycle courant ------------------------------------------------------

    async def _async_update_data(self) -> EtatStation:
        maintenant = dt_util.utcnow()
        self._verifier_statistiques()

        # On ne redemande que ce qui manque, avec un recouvrement : Hub'Eau
        # publie certaines stations par lots et peut completer une heure deja
        # servie.
        plancher = maintenant - timedelta(days=JOURS_TAMPON)
        connues = [max(m) for m in self._mesures.values() if m]
        depuis = max(plancher, max(connues) - RECOUVREMENT) if connues \
            else plancher
        try:
            nouvelles = await self.api.observations(self.code, depuis)
        except ErreurHubEau as err:
            # Une requete perdue n'efface pas des mesures encore fraiches :
            # l'API a des absences de quelques minutes, sans consequence.
            if not self.etat.obsolete:
                _LOGGER.info("%s : cycle manque, mesures conservees : %s",
                             self.code, err)
                self._deduire(maintenant)
                return self.etat
            raise UpdateFailed(str(err)) from err

        for g, points in nouvelles.items():
            if g in self._mesures:
                self._mesures[g].update(points)
        for m in self._mesures.values():
            for d in [d for d in m if d < plancher]:
                del m[d]
        self._deduire(maintenant)
        self._store_mesures.async_delay_save(self._tampon_serialise,
                                             DELAI_ECRITURE_TAMPON)
        return self.etat

    def _deduire(self, maintenant: datetime) -> None:
        """Recalcule l'etat expose a partir du tampon des mesures."""
        fenetre = maintenant - timedelta(hours=HEURES_DETECTION_FIGE)
        for g, cible in ((GRANDEUR_HAUTEUR, self.etat.hauteur),
                         (GRANDEUR_DEBIT, self.etat.debit)):
            serie = sorted(self._mesures[g].items())
            if not serie:
                cible.valeur = cible.date = cible.tendance_par_heure = None
                cible.figee = False
                continue
            cible.date, v = serie[-1]
            cible.valeur = round(v, 3)
            recente = [p for p in serie if p[0] >= fenetre]
            cible.tendance_par_heure = stats_mod.tendance(recente)
            cible.figee = stats_mod.est_figee(recente)
            if cible.figee:
                _LOGGER.debug("%s : %s figee depuis au moins %d h",
                              self.code, g, HEURES_DETECTION_FIGE)
        self.etat.sept_jours = stats_mod.resume_sept_jours(
            sorted(self._mesures[GRANDEUR_HAUTEUR].items()), maintenant)

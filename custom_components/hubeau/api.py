"""Client de l'API Hub'Eau hydrometrie.

L'API est publique, sans cle ni compte, et documentee sur
https://hubeau.eaufrance.fr/page/api-hydrometrie. Elle est servie par un
etablissement public ; on s'y tient donc a un rythme raisonnable et on
s'annonce par un en-tete explicite.

Deux limites gouvernent toute l'integration :

- `observations_tr` ne conserve qu'**un mois glissant** au pas fin ;
- au-dela, seules les valeurs **journalieres** de `obs_elab` existent.

C'est pourquoi les statistiques de reference se construisent sur les valeurs
journalieres, tandis que l'affichage en direct vient du temps reel.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any

import aiohttp
from aiohttp import ClientResponseError, ClientTimeout

from .const import (
    DIVISEUR,
    QUALIFICATION_DOUTEUSE,
    STATUTS_RETENUS,
    URL_BASE,
)

_LOGGER = logging.getLogger(__name__)

AGENT = "home-assistant-hubeau"

# Deux regimes d'attente. Le cycle courant ne demande que quelques lignes, qui
# arrivent d'ordinaire en un dixieme de seconde ; mais l'API laisse parfois une
# requete pendre deux minutes avant de repondre 503 (mesure du 2026-09-22).
# Mieux vaut alors abandonner vite et retenter au cycle suivant. Les references
# de trente ans, elles, se chargent en arriere-plan et ont droit a la patience.
DELAI_COURT = ClientTimeout(total=20)
DELAI_LONG = ClientTimeout(total=120)

# L'API renvoie aussi un 503 quand on l'interroge trop vite : on reprend,
# avec une attente qui double a chaque essai.
ESSAIS = 3
ATTENTE_INITIALE = 2.0

# Plafond de lignes par reponse, pour les deux points d'acces utilises.
TAILLE_MAX = 20000


class ErreurHubEau(Exception):
    """Echec d'appel a l'API."""


class ApiHubEau:
    """Acces asynchrone a l'API, sur la session partagee de Home Assistant."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _obtenir(self, url: str, params: dict[str, Any] | None = None,
                       delai: ClientTimeout = DELAI_COURT) -> dict:
        if not url.startswith("http"):
            url = f"{URL_BASE}/{url}"
        derniere: Exception | None = None
        for essai in range(ESSAIS):
            try:
                async with self._session.get(
                    url, params=params, timeout=delai,
                    headers={"User-Agent": AGENT},
                ) as rep:
                    if rep.status == 503:
                        raise ClientResponseError(
                            rep.request_info, rep.history, status=503,
                            message="service momentanement indisponible")
                    rep.raise_for_status()
                    return await rep.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                derniere = err
                if essai < ESSAIS - 1:
                    await asyncio.sleep(ATTENTE_INITIALE * (2 ** essai))
        raise ErreurHubEau(f"{url.removeprefix(URL_BASE)} : {derniere!r}") \
            from derniere

    async def _pages(self, chemin: str, params: dict[str, Any],
                     delai: ClientTimeout = DELAI_COURT,
                     maxi: int = 10) -> list[dict]:
        """Suit la pagination par curseur jusqu'a epuisement.

        Avec `TAILLE_MAX` lignes par page, une seule suffit dans tous les cas
        d'usage : sept jours au pas de cinq minutes font 4 000 lignes, trente
        ans de valeurs journalieres 11 000. La boucle n'est qu'une securite.
        """
        rep = await self._obtenir(chemin, params, delai)
        lignes: list[dict] = list(rep.get("data", []))
        suivant = rep.get("next")
        pages = 1
        while suivant and pages < maxi:
            await asyncio.sleep(1.0)     # menagement du service public
            rep = await self._obtenir(suivant, None, delai)
            lignes.extend(rep.get("data", []))
            suivant = rep.get("next")
            pages += 1
        if suivant:
            raise ErreurHubEau("serie incomplete : limite de pagination atteinte")
        return lignes

    # -- Referentiel --------------------------------------------------------

    async def stations_proches(self, longitude: float, latitude: float,
                               rayon_km: float) -> list[dict]:
        """Stations en service autour d'un point, triees par distance.

        L'API n'offre pas de recherche par rayon : on interroge une emprise
        rectangulaire, puis on filtre et on trie nous-memes.
        """
        # Un degre de latitude vaut environ 111 km ; en longitude il se
        # resserre avec le cosinus de la latitude.
        import math
        dlat = rayon_km / 111.0
        dlon = rayon_km / (111.0 * max(0.2, math.cos(math.radians(latitude))))
        rep = await self._obtenir("referentiel/stations", {
            "bbox": f"{longitude-dlon},{latitude-dlat},"
                    f"{longitude+dlon},{latitude+dlat}",
            "format": "json", "size": 200, "en_service": "true",
        })
        sorties = []
        for s in rep.get("data", []):
            lon, lat = s.get("longitude_station"), s.get("latitude_station")
            if lon is None or lat is None:
                continue
            d = _distance_km(longitude, latitude, lon, lat)
            if d > rayon_km:
                continue
            s["distance_km"] = round(d, 1)
            sorties.append(s)
        sorties.sort(key=lambda s: s["distance_km"])
        return sorties

    async def station(self, code: str) -> dict:
        rep = await self._obtenir("referentiel/stations",
                                  {"code_station": code, "format": "json"})
        donnees = rep.get("data", [])
        if not donnees:
            raise ErreurHubEau(f"station inconnue : {code}")
        return donnees[0]

    # -- Temps reel ---------------------------------------------------------

    async def observations(self, code: str, depuis: datetime,
                           ) -> dict[str, list[tuple[datetime, float]]]:
        """Mesures au pas fin depuis une date, hauteur et debit ensemble.

        Une seule requete pour les deux grandeurs : sans `grandeur_hydro`,
        l'API les renvoie melees, chaque ligne portant la sienne. Le tri
        descendant est celui que l'API sert le plus vite ; on remet l'ordre
        chronologique ici. Hauteurs en metres, debits en m3/s.
        """
        lignes = await self._pages("observations_tr", {
            "code_entite": code,
            "date_debut_obs": depuis.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "size": TAILLE_MAX, "sort": "desc",
            "fields": "grandeur_hydro,date_obs,resultat_obs",
        })
        sorties: dict[str, list[tuple[datetime, float]]] = {}
        for o in reversed(lignes):
            v = o.get("resultat_obs")
            if v is None:
                continue
            sorties.setdefault(o.get("grandeur_hydro"), []).append(
                (_en_datetime(o["date_obs"]), v / DIVISEUR))
        return sorties

    # -- Historique ---------------------------------------------------------

    async def serie_journaliere(
        self, code: str, grandeur_elab: str, debut: date, fin: date,
    ) -> tuple[list[tuple[date, float]], int]:
        """Valeurs journalieres entre deux dates, ecremees de ce qui est douteux.

        Une seule requete pour toute la periode : trente ans de valeurs
        journalieres tiennent sous le plafond de lignes d'une page. L'ancien
        decoupage en tranches de cinq ans multipliait les appels, et donc les
        occasions de tomber sur un 503, pour rien.

        Chaque valeur porte un statut et une qualification, que l'integration
        ignorait jusqu'a la version 0.4.0. Sur le Lez a Lavalette, cela faisait
        entrer dans les references 6,1 % de debits que le producteur qualifie
        lui-meme de douteux, dont le maximum de la chronique : 239 m3/s, quand
        le plus fort debit qualifie bon vaut 94 m3/s.
        """
        lignes = await self._pages("obs_elab", {
            "code_entite": code, "grandeur_hydro_elab": grandeur_elab,
            "date_debut_obs_elab": debut.isoformat(),
            "date_fin_obs_elab": fin.isoformat(),
            "size": TAILLE_MAX,
            "fields": "date_obs_elab,resultat_obs_elab,"
                      "code_statut,code_qualification",
        }, delai=DELAI_LONG)
        sorties: list[tuple[date, float]] = []
        ecartes = 0
        for o in lignes:
            v = o.get("resultat_obs_elab")
            if v is None:
                continue
            if not _donnee_retenue(o):
                ecartes += 1
                continue
            sorties.append((date.fromisoformat(o["date_obs_elab"]),
                            v / DIVISEUR))
        sorties.sort()

        if ecartes:
            _LOGGER.info(
                "%s %s : %d valeurs retenues, %d ecartees (statut ou "
                "qualification)", code, grandeur_elab, len(sorties), ecartes)
        return sorties, ecartes


# --- Utilitaires -------------------------------------------------------------

def _donnee_retenue(observation: dict) -> bool:
    """Vrai si la valeur est assez sure pour entrer dans une reference.

    Un code absent ne fait pas rejeter : toutes les stations ne renseignent pas
    ces champs, et les ecarter reviendrait a perdre des chroniques entieres.
    """
    statut = observation.get("code_statut")
    if statut is not None and statut not in STATUTS_RETENUS:
        return False
    qualification = observation.get("code_qualification")
    return qualification != QUALIFICATION_DOUTEUSE

def _en_datetime(texte: str) -> datetime:
    from homeassistant.util import dt as dt_util
    valeur = dt_util.parse_datetime(texte)
    if valeur is None:
        raise ErreurHubEau(f"horodatage illisible : {texte}")
    return dt_util.as_utc(valeur)


def _distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distance orthodromique, formule de haversine."""
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))

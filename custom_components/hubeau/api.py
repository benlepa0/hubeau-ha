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
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientResponseError, ClientTimeout

from .const import DIVISEUR, URL_BASE

_LOGGER = logging.getLogger(__name__)

AGENT = "home-assistant-hubeau"
DELAI = ClientTimeout(total=60)

# L'API renvoie un 503 quand on l'interroge trop vite. Les reprises sont donc
# la regle et non l'exception, en particulier lors du chargement initial des
# trente ans d'historique.
ESSAIS = 4
ATTENTE_INITIALE = 3.0


class ErreurHubEau(Exception):
    """Echec d'appel a l'API."""


class ApiHubEau:
    """Acces asynchrone a l'API, sur la session partagee de Home Assistant."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _obtenir(self, chemin: str, params: dict[str, Any]) -> dict:
        url = f"{URL_BASE}/{chemin}"
        derniere: Exception | None = None
        for essai in range(ESSAIS):
            try:
                async with self._session.get(
                    url, params=params, timeout=DELAI,
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
        raise ErreurHubEau(f"{chemin} : {derniere}") from derniere

    async def _pages(self, chemin: str, params: dict[str, Any],
                     maxi: int = 50) -> list[dict]:
        """Suit la pagination par curseur jusqu'a epuisement."""
        lignes: list[dict] = []
        rep = await self._obtenir(chemin, params)
        lignes.extend(rep.get("data", []))
        suivant = rep.get("next")
        pages = 1
        while suivant and pages < maxi:
            async with self._session.get(
                suivant, timeout=DELAI, headers={"User-Agent": AGENT}
            ) as r:
                r.raise_for_status()
                rep = await r.json()
            lignes.extend(rep.get("data", []))
            suivant = rep.get("next")
            pages += 1
            await asyncio.sleep(1.0)
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

    async def derniere_mesure(self, code: str, grandeur: str) -> dict | None:
        """Mesure la plus recente, convertie en m3/s ou en metres."""
        rep = await self._obtenir("observations_tr", {
            "code_entite": code, "grandeur_hydro": grandeur,
            "size": 1, "sort": "desc",
            "fields": "date_obs,resultat_obs",
        })
        donnees = rep.get("data", [])
        if not donnees or donnees[0].get("resultat_obs") is None:
            return None
        o = donnees[0]
        return {
            "valeur": o["resultat_obs"] / DIVISEUR,
            "date": _en_datetime(o["date_obs"]),
        }

    async def serie_recente(self, code: str, grandeur: str,
                            heures: int = 24) -> list[tuple[datetime, float]]:
        """Serie au pas fin sur les dernieres heures, du plus ancien au plus
        recent. Sert a detecter une station figee et a mesurer une tendance."""
        depuis = (datetime.utcnow() - timedelta(hours=heures)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        lignes = await self._pages("observations_tr", {
            "code_entite": code, "grandeur_hydro": grandeur,
            "date_debut_obs": depuis, "size": 2000, "sort": "asc",
            "fields": "date_obs,resultat_obs",
        }, maxi=6)
        return [(_en_datetime(o["date_obs"]), o["resultat_obs"] / DIVISEUR)
                for o in lignes if o.get("resultat_obs") is not None]

    # -- Historique ---------------------------------------------------------

    async def serie_journaliere(self, code: str, grandeur_elab: str,
                                debut: date, fin: date) -> list[tuple[date, float]]:
        """Valeurs journalieres entre deux dates.

        Decoupee en tranches de cinq ans : l'API plafonne le nombre de lignes
        par reponse, et la decoupe evite d'enchainer trop de pages.
        """
        sorties: list[tuple[date, float]] = []
        an = debut.year
        while an <= fin.year:
            borne = min(an + 4, fin.year)
            rep = await self._obtenir("obs_elab", {
                "code_entite": code, "grandeur_hydro_elab": grandeur_elab,
                "date_debut_obs_elab": f"{an}-01-01",
                "date_fin_obs_elab": f"{borne}-12-31",
                "size": 5000, "sort": "asc",
                "fields": "date_obs_elab,resultat_obs_elab",
            })
            for o in rep.get("data", []):
                v = o.get("resultat_obs_elab")
                if v is not None:
                    sorties.append((date.fromisoformat(o["date_obs_elab"]),
                                    v / DIVISEUR))
            an = borne + 1
            await asyncio.sleep(2.0)     # menagement du service public
        return sorties


# --- Utilitaires -------------------------------------------------------------

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

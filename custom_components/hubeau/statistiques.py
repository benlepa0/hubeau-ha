"""Statistiques de reference d'une station, et lecture d'une mesure.

C'est ce que cette integration apporte de particulier. Savoir que le Lez est
a 0,27 m ne dit rien a personne ; savoir que cette hauteur est **sous le
percentile 5 de trente ans** dit tout de suite qu'on est en etiage marque. Un
seuil absolu, lui, n'aurait aucun sens d'une riviere a l'autre : 1 m est une
crue sur un ruisseau cevenol et un etiage sur la Loire.

Les statistiques sont donc calculees par station, a partir de sa propre
chronique journaliere, et rafraichies une fois par mois -- trente ans de
donnees ne bougent pas d'une semaine sur l'autre.
"""

from __future__ import annotations

import bisect
import logging
from dataclasses import dataclass, asdict
from datetime import date

from .const import NIVEAUX

_LOGGER = logging.getLogger(__name__)

# En deca, la chronique est trop courte pour que les percentiles hauts aient
# un sens : le percentile 99 sur deux ans ne represente que sept jours.
JOURS_MINIMUM = 1095      # trois ans


@dataclass
class Statistiques:
    """Distribution d'une grandeur sur la chronique d'une station."""

    jours: int
    annees: float
    debut: str
    fin: str
    percentiles: dict[str, float]     # "5", "25", ... -> valeur
    maximum: float
    maximum_date: str
    minimum: float

    def vers_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def depuis_dict(cls, d: dict) -> "Statistiques":
        return cls(**d)

    # -- lecture d'une mesure ----------------------------------------------

    def rang(self, valeur: float) -> float:
        """Percentile approche d'une valeur, par interpolation entre bornes.

        Le maximum de la chronique sert de derniere borne. Sans lui, tout ce
        qui depasse le percentile 99,9 serait ecrase a 100 % : sur le Lez,
        trois metres et cinq metres auraient eu le meme rang, alors que le
        premier s'est produit sept fois en trente ans et le second jamais.
        """
        bornes = sorted((float(p), v) for p, v in self.percentiles.items())
        # Le maximum observe vaut, par construction, le percentile 100.
        if self.maximum > bornes[-1][1]:
            bornes.append((100.0, self.maximum))
        if valeur <= bornes[0][1]:
            return bornes[0][0]
        for (p1, v1), (p2, v2) in zip(bornes, bornes[1:]):
            if valeur <= v2:
                if v2 == v1:
                    return p2
                return p1 + (p2 - p1) * (valeur - v1) / (v2 - v1)
        return 100.0

    def au_dela_de_la_chronique(self, valeur: float) -> bool:
        """Vrai si la valeur depasse tout ce qui a ete enregistre."""
        return valeur > self.maximum

    def commentaire(self, valeur: float) -> str:
        """Une phrase qui situe la mesure, destinee a etre lue telle quelle."""
        if self.au_dela_de_la_chronique(valeur):
            return (f"au-dela du maximum connu ({self.maximum:g}, "
                    f"le {self.maximum_date})")
        r = self.rang(valeur)
        if r >= 99.99:
            return f"egale le maximum de {self.annees:g} ans"
        f = self.frequence_depassement_jours(valeur)
        if f is None:
            if r <= 5.0:
                return f"parmi les 5 % les plus bas de {self.annees:g} ans"
            if r <= 25.0:
                return "dans le quart le plus bas"
            return "sous la mediane"
        if f < 3:
            return "au-dessus de la mediane"
        return f"depasse environ un jour sur {f:.0f}"

    def niveau(self, valeur: float) -> str:
        """Regime hydrologique correspondant, en termes de percentile."""
        r = self.rang(valeur)
        # Borne incluse : le percentile 90 est la limite *haute* du regime
        # soutenu, pas le debut du regime fort. Avec une comparaison stricte,
        # une valeur tombant pile sur une borne basculait d'un cran de trop.
        for nom, borne in NIVEAUX:
            if r <= borne:
                return nom
        return NIVEAUX[-1][0]

    def frequence_depassement_jours(self, valeur: float) -> float | None:
        """Un jour sur combien depasse cette valeur ? None si sans objet.

        Ce n'est pas une periode de retour au sens hydrologique -- qui se
        calcule sur les maxima annuels avec un ajustement statistique -- mais
        une frequence empirique de depassement, qui se lit directement et ne
        pretend a rien de plus.

        Sans objet sous la mediane : dire d'un etiage qu'il est « depasse un
        jour sur deux » n'apprend rien, et le presenter comme une frequence de
        depassement preterait a confusion avec une mesure de severite.
        """
        r = self.rang(valeur)
        if r < 50.0 or r >= 100.0:
            return None
        part = (100.0 - r) / 100.0
        return None if part <= 0 else 1.0 / part


def calculer(serie: list[tuple[date, float]]) -> Statistiques | None:
    """Percentiles d'une chronique journaliere. None si elle est trop courte."""
    if len(serie) < JOURS_MINIMUM:
        _LOGGER.warning(
            "chronique trop courte pour des statistiques fiables : "
            "%d jours, il en faut %d", len(serie), JOURS_MINIMUM)
        return None

    valeurs = sorted(v for _, v in serie)
    n = len(valeurs)

    def pct(p: float) -> float:
        i = min(n - 1, max(0, int(round(n * p / 100.0)) - 1))
        return round(valeurs[i], 3)

    plus_haut = max(serie, key=lambda kv: kv[1])
    return Statistiques(
        jours=n,
        annees=round(n / 365.25, 1),
        debut=min(serie)[0].isoformat(),
        fin=max(serie)[0].isoformat(),
        percentiles={str(p): pct(p) for p in
                     (1, 5, 10, 25, 50, 75, 90, 95, 99, 99.5, 99.9)},
        maximum=round(plus_haut[1], 3),
        maximum_date=plus_haut[0].isoformat(),
        minimum=round(valeurs[0], 3),
    )


def tendance(serie: list[tuple]) -> float | None:
    """Vitesse de variation recente, par unite et par heure.

    Regression lineaire sur les mesures, plutot qu'un simple ecart entre la
    premiere et la derniere : une mesure isolee aberrante -- il y en a -- ne
    doit pas dicter la tendance affichee.
    """
    if len(serie) < 4:
        return None
    t0 = serie[0][0]
    xs = [(t - t0).total_seconds() / 3600.0 for t, _ in serie]
    ys = [v for _, v in serie]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


def est_figee(serie: list[tuple], minimum_points: int = 24,
              valeurs_distinctes_max: int = 3) -> bool:
    """Vrai si la station renvoie une valeur immobile.

    Un capteur hydrometrique peut rester joignable tout en ayant cesse de
    mesurer. Le cas d'ecole est le Lirou au Triadou : il annonce 2,65 m3/s
    depuis des semaines, et le producteur qualifie lui-meme ces valeurs de
    douteuses. Surveiller la seule disponibilite ne le verrait pas.

    Le critere retenu est le nombre de valeurs *distinctes*, et non l'etendue
    relative essayee d'abord. Sur douze heures, ce Lirou ne prend que deux
    valeurs sur cent quarante-deux mesures, mais l'ecart entre elles suffisait
    a passer sous un seuil d'etendue. Une station vivante, elle, en prend une
    demi-douzaine au moins : la quantification du capteur lui laisse toujours
    un peu de jeu.

    Une etendue rigoureusement nulle reste evidemment un cas figé, meme avec
    peu de points.
    """
    if len(serie) < 4:
        return False
    valeurs = [v for _, v in serie]
    if max(valeurs) == min(valeurs):
        return True
    if len(serie) < minimum_points:
        return False
    return len(set(valeurs)) <= valeurs_distinctes_max


def hauteur_incoherente(hauteur: float | None, debit: float | None) -> bool:
    """Vrai si un debit notable est annonce alors que la hauteur est nulle.

    Le debit n'est pas mesure : il se deduit de la hauteur par une courbe de
    tarage. Une hauteur nulle ou negative accompagnee d'un debit franc signale
    donc une station hors d'eau ou dereglee -- exactement ce que montre le
    Lirou, qui affiche 2,65 m3/s pour une hauteur de zero.
    """
    if hauteur is None or debit is None:
        return False
    return hauteur <= 0.0 and debit > 0.05

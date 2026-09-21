"""Constantes de l'integration Hub'Eau."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAINE: Final = "hubeau"
DOMAIN: Final = DOMAINE          # attendu par Home Assistant

FABRICANT: Final = "Eaufrance"
URL_BASE: Final = "https://hubeau.eaufrance.fr/api/v2/hydrometrie"

# L'API publie les mesures avec dix a vingt minutes de retard et un pas de
# cinq a dix minutes selon les stations. Interroger plus souvent ne rapporte
# rien et sollicite un service public pour rien.
INTERVALLE: Final = timedelta(minutes=5)

# Les statistiques de reference ne bougent pratiquement pas d'un mois sur
# l'autre : elles portent sur trente ans. On les recalcule rarement.
INTERVALLE_STATISTIQUES: Final = timedelta(days=30)

# Profondeur de la chronique utilisee pour situer la mesure du moment.
ANNEES_REFERENCE: Final = 30

CONF_STATION: Final = "station"
CONF_LIBELLE: Final = "libelle"
CONF_COURS_EAU: Final = "cours_eau"
CONF_RAYON_KM: Final = "rayon_km"

RAYON_DEFAUT_KM: Final = 30.0

# Grandeurs hydrometriques de Hub'Eau.
GRANDEUR_DEBIT: Final = "Q"
GRANDEUR_HAUTEUR: Final = "H"

# Grandeurs elaborees, pour l'historique. Hub'Eau ne conserve le pas fin
# qu'un mois glissant ; au-dela seules ces valeurs journalieres existent.
ELAB_DEBIT_MOYEN: Final = "QmnJ"      # debit moyen journalier
ELAB_HAUTEUR_MAX: Final = "HIXnJ"     # hauteur maximale journaliere

# Hub'Eau exprime debits et hauteurs en unites entieres : litres par seconde
# et millimetres. Tout le reste de l'integration travaille en m3/s et en m.
DIVISEUR: Final = 1000.0

# Seuils de lecture, exprimes en percentiles de la chronique de la station et
# non en valeurs absolues : une meme hauteur ne veut pas dire la meme chose
# sur le Lez et sur la Loire. Les bornes sont celles qu'emploie l'hydrologie
# de terrain pour decrire un regime.
NIVEAUX: Final = (
    ("etiage_severe", 5.0),
    ("etiage", 25.0),
    ("normal", 75.0),
    ("soutenu", 90.0),
    ("fort", 99.0),
    ("crue", 99.9),
    ("crue_majeure", 100.0),
)

# Au-dela de ce delai sans mesure nouvelle, la station est consideree muette.
MINUTES_AVANT_OBSOLESCENCE: Final = 120

# Une station peut rester en ligne tout en etant figee : c'est le cas du
# Lirou au Triadou, qui renvoie la meme valeur a la troisieme decimale pres
# depuis des semaines. On detecte l'immobilite plutot que l'absence.
HEURES_DETECTION_FIGE: Final = 12

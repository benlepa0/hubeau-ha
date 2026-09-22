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

# Profondeur du tampon des mesures au pas fin, tenu en memoire et sur disque :
# il nourrit le resume sur sept jours, la tendance et la detection d'un capteur
# fige, sans reinterroger l'API a chaque cycle.
JOURS_TAMPON: Final = 7

# Chaque cycle redemande la derniere heure deja connue : certaines stations
# sont publiees par lots, et un lot peut completer une heure deja servie.
RECOUVREMENT: Final = timedelta(hours=1)

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
#
# La reference de debit est la **pointe** journaliere et non la moyenne : c'est
# une mesure instantanee qu'on vient y classer. Mesure du 2026-09-22 sur le Lez
# a Lavalette : une pointe au percentile 99 des pointes ressortait au percentile
# 99,6 des moyennes, et l'alerte de crue se declenchait 6,5 jours par an au lieu
# des 3,7 annonces. Toutes les stations ne publient pas QIXnJ, d'ou le repli.
ELAB_DEBIT_POINTE: Final = "QIXnJ"    # debit instantane maximal journalier
ELAB_DEBIT_MOYEN: Final = "QmnJ"      # debit moyen journalier, en repli
ELAB_HAUTEUR_MAX: Final = "HIXnJ"     # hauteur instantanee maximale journaliere

# Qualite des donnees elaborees, nomenclatures Sandre 510 (statut) et 508
# (qualification). HydroPortail restreint ses analyses publiques aux donnees
# « pre-validees et validees » ; on fait de meme, et on ecarte en plus ce que
# le producteur qualifie de douteux. Un code absent ne fait pas rejeter la
# valeur : toutes les stations ne renseignent pas ces champs.
STATUTS_RETENUS: Final = (12, 16)     # pre-validee, validee
QUALIFICATION_DOUTEUSE: Final = 12    # « incertaine » chez Sandre

# Un percentile n'a de sens que s'il s'appuie sur assez de jours au-dessus de
# lui. En deca, la classe existe sans rien derriere.
JOURS_DE_SOUTIEN: Final = 10

# Hub'Eau exprime debits et hauteurs en unites entieres : litres par seconde
# et millimetres. Tout le reste de l'integration travaille en m3/s et en m.
DIVISEUR: Final = 1000.0

# Seuils de lecture, exprimes en percentiles de la chronique de la station et
# non en valeurs absolues : une meme hauteur ne veut pas dire la meme chose
# sur le Lez et sur la Loire.
#
# Ces bornes sont une **convention de ce projet**, verifiee le 2026-09-22 : la
# demarche, classer une mesure dans la distribution journaliere de sa propre
# station, est celle de la courbe des debits classes, mais les indices
# reglementaires francais sont d'une autre nature. Les basses eaux se decrivent
# par le QMNA5 et les VCNx, les hautes eaux par des periodes de retour ajustees
# sur des maximums annuels. Voir docs/HYPOTHESES.md.
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
# Ses entites gardent leur derniere valeur, horodatee ; c'est le capteur
# binaire « donnees obsoletes » qui signale le silence.
MINUTES_AVANT_OBSOLESCENCE: Final = 120

# Une station peut rester en ligne tout en etant figee : c'est le cas du
# Lirou au Triadou, qui renvoie la meme valeur a la troisieme decimale pres
# depuis des semaines. On detecte l'immobilite plutot que l'absence.
HEURES_DETECTION_FIGE: Final = 12

# La carte Lovelace voyage avec l'integration, dans le meme paquet : c'est
# l'integration qui la sert et qui la charge dans le frontend. L'utilisateur
# n'a donc ni second depot a installer, ni ressource a declarer a la main dans
# le tableau de bord.
FICHIER_CARTE: Final = "frontend/hubeau-card.js"
URL_CARTE: Final = "/hubeau/hubeau-card.js"
CLE_CARTE: Final = "hubeau_carte_servie"

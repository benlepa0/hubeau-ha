#!/usr/bin/env python3
"""Fabrique l'icone de marque de l'integration.

Home Assistant demande un PNG carre, 256 pixels et 512 pixels pour les
affichages a haute densite, et interdit d'emprunter sa propre identite
visuelle a une integration personnalisee. Le dessin est donc le motif de la
carte, reduit a l'essentiel : deux vagues sur un fond d'eau profonde.

Le script est ici pour que l'icone soit reproductible, et non un binaire
tombe du ciel.

    python3 outils/icone.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

DOSSIER = Path(__file__).resolve().parent.parent / "custom_components/hubeau/brand"

# Bleus de la carte : le fond descend vers l'eau profonde, les vagues
# remontent vers le clair.
HAUT = (33, 150, 243, 255)
BAS = (13, 71, 161, 255)
EAU = (129, 212, 250, 245)
CRETE = (255, 255, 255, 235)
REMOUS = (255, 255, 255, 110)

SURECHANTILLONNAGE = 4


def dessiner(taille: int) -> Image.Image:
    s = taille * SURECHANTILLONNAGE

    fond = Image.new("RGBA", (s, s))
    trait = ImageDraw.Draw(fond)
    for y in range(s):
        t = y / (s - 1)
        trait.line(
            [(0, y), (s, y)],
            fill=tuple(round(a + (b - a) * t) for a, b in zip(HAUT, BAS)),
        )

    coins = Image.new("L", (s, s), 0)
    ImageDraw.Draw(coins).rounded_rectangle(
        [0, 0, s - 1, s - 1], radius=round(0.22 * s), fill=255
    )

    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    image.paste(fond, (0, 0), coins)

    vagues = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pinceau = ImageDraw.Draw(vagues)

    def onde(niveau: float, amplitude: float, phase: float) -> list[tuple[float, float]]:
        return [
            (x, niveau * s + amplitude * s * math.sin(2 * math.pi * 1.5 * x / s + phase))
            for x in range(s + 1)
        ]

    # Le corps de l'eau, puis sa crete : un trait, et non un aplat, sans quoi
    # le blanc mange le bas de l'icone et l'eau ressemble a de la neige.
    surface = onde(0.56, 0.045, 0.0)
    pinceau.polygon([*surface, (s, s), (0, s)], fill=EAU)
    pinceau.line(surface, fill=CRETE, width=round(0.030 * s), joint="curve")

    # Une seconde onde, plus basse et a contresens, donne la profondeur.
    pinceau.line(
        onde(0.76, 0.030, math.pi), fill=REMOUS, width=round(0.022 * s), joint="curve"
    )

    image.alpha_composite(vagues)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), coins))

    return image.resize((taille, taille), Image.LANCZOS)


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    for taille, nom in ((256, "icon.png"), (512, "icon@2x.png")):
        chemin = DOSSIER / nom
        dessiner(taille).save(chemin, "PNG", optimize=True)
        print(f"{chemin.relative_to(DOSSIER.parent.parent.parent)} : {taille}x{taille}")


if __name__ == "__main__":
    main()

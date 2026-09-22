#!/usr/bin/env python3
"""Controles de la carte avant deploiement.

Deux defauts se sont produits, et tous deux rendaient la carte muette ou
absurde sans qu'aucun outil ne les signale.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def bloc_de_style(source: str) -> str:
    debut = source.index("innerHTML = `")
    return source[debut + 13:source.index("`;", debut)]


def verifier(chemin: Path) -> list[str]:
    s = chemin.read_text(encoding="utf-8")
    fautes: list[str] = []

    # 1. Un accent grave dans le bloc de style romprait le litteral de gabarit
    #    qui le porte, et la carte ne se chargerait plus du tout. C'est arrive
    #    deux fois, a chaque fois en citant un nom de classe dans un
    #    commentaire.
    n = bloc_de_style(s).count("`")
    if n:
        fautes.append(f"{n} accent(s) grave(s) dans le bloc de style : "
                      "le gabarit serait rompu")

    # 2. Une classe porteuse d'animation ne doit pas etre partagee avec des
    #    elements qui n'ont rien a voir. La classe « v » designait a la fois
    #    les vagues et les valeurs chiffrees du pied : les nombres heritaient
    #    du glissement et defilaient vers la gauche en boucle.
    animees = set(re.findall(r"\.([\w-]+)\s*\{[^{}]*animation:", s))
    for classe in sorted(animees):
        porteurs = re.findall(r'class="([^"]*)"', s)
        familles = {p.split()[0] for p in porteurs
                    if classe in p.split()}
        familles |= {m for m in re.findall(
            r'className = "([\w-]+)"', s) if m == classe}
        if len(familles) > 1:
            fautes.append(f"la classe animee « {classe} » est partagee par "
                          f"plusieurs familles d'elements : {sorted(familles)}")

    return fautes


if __name__ == "__main__":
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else "custom_components/hubeau/frontend/hubeau-card.js")
    fautes = verifier(chemin)
    for f in fautes:
        print(f"   {f}")
    if fautes:
        sys.exit(1)
    print("   bloc de style et classes animees : rien a signaler")

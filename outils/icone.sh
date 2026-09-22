#!/usr/bin/env bash
# Rend l'icone de marque a partir de sa source vectorielle.
#
# Home Assistant demande un PNG carre, 256 pixels et 512 pixels pour les
# affichages a haute densite, et interdit d'emprunter sa propre identite
# visuelle a une integration personnalisee.
#
# Le rendu passe par Chromium plutot que par une bibliotheque d'images : les
# courbes de la goutte et les degrades sortent nets, et chaque taille est
# rendue a sa dimension propre au lieu d'etre reduite.
set -euo pipefail
ICI="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ICI/outils/icone.svg"
CIBLE="$ICI/custom_components/hubeau/brand"
TEMPORAIRE="$(mktemp -d)"
trap 'rm -rf "$TEMPORAIRE"' EXIT

mkdir -p "$CIBLE"
cat > "$TEMPORAIRE/icone.html" <<HTML
<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;padding:0;background:transparent}svg{display:block;width:100vw;height:100vh}</style>
$(cat "$SOURCE")
HTML

rendre() {
  chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --default-background-color=00000000 --window-size="$1,$1" \
    --screenshot="$CIBLE/$2" "file://$TEMPORAIRE/icone.html" 2>/dev/null
}
rendre 256 icon.png
rendre 512 "icon@2x.png"

# Chromium n'optimise pas ce qu'il ecrit.
python3 - "$CIBLE" <<'PY'
import sys
from pathlib import Path
from PIL import Image

for nom in ("icon.png", "icon@2x.png"):
    chemin = Path(sys.argv[1]) / nom
    image = Image.open(chemin)
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    image.save(chemin, "PNG", optimize=True)
    print(f"{nom} : {image.width}x{image.height}, {chemin.stat().st_size // 1024} Kio")
PY

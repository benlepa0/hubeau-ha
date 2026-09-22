#!/usr/bin/env bash
# Refait les captures du README a partir de la page de demonstration.
#
# La carte est rendue dans un Chromium sans interface, sur un serveur local
# temporaire : un module ES ne se charge pas depuis file://. Le parametre
# ?capture retire le bouton de bascule du theme.
set -euo pipefail
ICI="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8777}"

python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ICI" >/dev/null 2>&1 &
SERVEUR=$!
trap 'kill $SERVEUR 2>/dev/null || true' EXIT
sleep 1

for theme in sombre clair; do
  [ "$theme" = clair ] && q="?capture&theme=clair" || q="?capture"
  chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --virtual-time-budget=4000 --window-size=1900,520 \
    --screenshot="$ICI/docs/captures/carte-$theme.png" \
    "http://127.0.0.1:$PORT/outils/demo.html$q" 2>/dev/null
done

# Chromium remplit toute la fenetre ; on retire le fond inutile sous les cartes.
python3 - "$ICI/docs/captures" <<'PY'
import sys
from pathlib import Path
from PIL import Image

for chemin in sorted(Path(sys.argv[1]).glob("carte-*.png")):
    image = Image.open(chemin).convert("RGB")
    fond = image.getpixel((5, image.height - 5))
    bas = image.height
    for y in range(image.height - 1, 0, -1):
        ligne = (image.getpixel((x, y)) for x in range(0, image.width, 17))
        if any(sum(abs(a - b) for a, b in zip(p, fond)) > 12 for p in ligne):
            bas = min(image.height, y + 20)
            break
    image.crop((0, 0, image.width, bas)).save(chemin, optimize=True)
    print(f"{chemin.name} : {Image.open(chemin).size[0]}x{Image.open(chemin).size[1]}")

# Les cinq etats tiennent sur 1900 pixels, que GitHub reduit de moitie : les
# chiffres y deviennent illisibles. L'image de tete n'en garde donc que trois,
# choisis pour l'ecart qu'ils montrent : etiage, regime fort, crue majeure.
MARGE, LARGEUR, ECART = 28, 340, 24
source = Image.open(Path(sys.argv[1]) / "carte-sombre.png")
colonnes = [0, 2, 3]
tete = Image.new(
    "RGB",
    (2 * MARGE + len(colonnes) * LARGEUR + (len(colonnes) - 1) * ECART, source.height),
    source.getpixel((5, source.height - 5)),
)
for place, colonne in enumerate(colonnes):
    gauche = MARGE + colonne * (LARGEUR + ECART)
    tete.paste(
        source.crop((gauche, 0, gauche + LARGEUR, source.height)),
        (MARGE + place * (LARGEUR + ECART), 0),
    )
tete.save(Path(sys.argv[1]) / "carte.png", optimize=True)
print(f"carte.png : {tete.width}x{tete.height}")
PY

#!/usr/bin/env bash
# Deploie l'integration et la carte vers Home Assistant.
#
# Ecrit apres s'etre fait prendre : la carte avait ete copiee une premiere
# fois, puis corrigee deux fois dans le depot sans jamais etre redeployee.
# L'utilisateur regardait donc une version ou les vagues etaient masquees et
# les filets de courant invisibles, et concluait, a juste titre, qu'il n'y
# avait pas d'animation.
#
# Le numero de version de la carte est repris dans l'URL de la ressource
# Lovelace : sans cela, le navigateur et surtout l'application Companion
# servent indefiniment le fichier qu'ils ont en cache.
set -euo pipefail
ICI="$(cd "$(dirname "$0")/.." && pwd)"
CONTENEUR="${CONTENEUR:-homeassistant}"

VERSION=$(grep -oP '(?<=const VERSION = ")[^"]+' "$ICI/carte/hubeau-card.js")
echo "carte version $VERSION"

echo "-- integration"
find "$ICI/custom_components/hubeau" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
docker exec "$CONTENEUR" rm -rf /config/custom_components/hubeau
docker cp "$ICI/custom_components/hubeau" "$CONTENEUR:/config/custom_components/" >/dev/null

echo "-- controles de la carte"
node --check "$ICI/carte/hubeau-card.js"
python3 "$ICI/outils/verifier_carte.py" "$ICI/carte/hubeau-card.js"

echo "-- carte"
docker exec "$CONTENEUR" mkdir -p /config/www/community/hubeau-card
docker cp "$ICI/carte/hubeau-card.js" \
  "$CONTENEUR:/config/www/community/hubeau-card/hubeau-card.js" >/dev/null

echo "-- verification"
a=$(md5sum "$ICI/carte/hubeau-card.js" | cut -d' ' -f1)
b=$(docker exec "$CONTENEUR" md5sum /config/www/community/hubeau-card/hubeau-card.js | cut -d' ' -f1)
[ "$a" = "$b" ] && echo "   carte identique a la source ($a)" || { echo "   ECART entre source et deploiement"; exit 1; }
echo
echo "Reste a faire :"
echo "  - mettre l'URL de la ressource Lovelace a ?v=$VERSION"
echo "  - redemarrer Home Assistant si l'integration a change"

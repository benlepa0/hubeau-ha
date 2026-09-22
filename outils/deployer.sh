#!/usr/bin/env bash
# Deploie l'integration vers un Home Assistant en conteneur, pour la mise au
# point. Une installation normale passe par HACS.
#
# Depuis la version 0.3.0 la carte voyage dans le paquet : il n'y a plus qu'un
# seul dossier a copier, et plus de fichier a deposer dans www/. C'est ce
# doublon qui avait derive -- la carte corrigee deux fois dans le depot, jamais
# redeployee, et l'utilisateur regardait une version sans animation.
set -euo pipefail
ICI="$(cd "$(dirname "$0")/.." && pwd)"
CONTENEUR="${CONTENEUR:-homeassistant}"
CARTE="$ICI/custom_components/hubeau/frontend/hubeau-card.js"

VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' \
  "$ICI/custom_components/hubeau/manifest.json")
echo "paquet version $VERSION"

echo "-- controles"
node --check "$CARTE"
python3 "$ICI/outils/verifier_carte.py" "$CARTE"
python3 -m compileall -q "$ICI/custom_components/hubeau"

echo "-- copie"
find "$ICI/custom_components/hubeau" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
docker exec "$CONTENEUR" rm -rf /config/custom_components/hubeau
docker cp "$ICI/custom_components/hubeau" "$CONTENEUR:/config/custom_components/" >/dev/null

echo "-- verification"
a=$(md5sum "$CARTE" | cut -d' ' -f1)
b=$(docker exec "$CONTENEUR" md5sum \
     /config/custom_components/hubeau/frontend/hubeau-card.js | cut -d' ' -f1)
[ "$a" = "$b" ] && echo "   carte identique a la source ($a)" \
  || { echo "   ECART entre source et deploiement"; exit 1; }

echo
echo "Reste a faire : redemarrer Home Assistant."
echo "La carte sera servie sur /hubeau/hubeau-card.js?v=<empreinte du fichier> ;"
echo "la console du navigateur doit afficher HUBEAU-CARD au chargement."

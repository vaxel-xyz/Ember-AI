#!/bin/sh
set -eu
CONF=/etc/nginx/conf.d/default.conf
if [ -z "${EMBER_API_KEY:-}" ]; then echo "[ember-dashboard] EMBER_API_KEY not set; /api calls will 401" >&2; fi
ESCAPED=$(printf '%s\n' "${EMBER_API_KEY:-}" | sed 's/[&/\]/\\&/g')
sed -i "s|Bearer \${EMBER_API_KEY}|Bearer ${ESCAPED}|g" "$CONF"
exec nginx -g 'daemon off;'

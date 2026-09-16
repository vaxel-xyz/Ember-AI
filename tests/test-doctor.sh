#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tests/.tmp
python3 - <<'EOF' &
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = {"status":"healthy","engine_pool":{"loaded_count":1}} if self.path=="/health" else {"status":"connected"}
        if self.path.startswith("/api/health"): body={"status":"ok"}
        self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(body).encode())
    def do_POST(self):
        body = {"data":[{"embedding":[0.1,0.2]}]} if "embeddings" in self.path else {"choices":[{"message":{"content":"pong"}}]}
        self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(body).encode())
    def log_message(self,*a): pass
HTTPServer(("127.0.0.1", 18999), H).serve_forever()
EOF
srv=$!; trap 'kill $srv' EXIT; sleep 1
cat > tests/.tmp/doctor.env <<EOF
OMLX_BASE_URL=http://127.0.0.1:18999
OMLX_API_KEY=x
LITELLM_MASTER_KEY=x
EMBER_API_KEY=x
OMLX_CHAT_MODEL=m
OMLX_EMBED_MODEL=e
EOF
EMBER_ENV_FILE=tests/.tmp/doctor.env EMBER_LITELLM_URL=http://127.0.0.1:18999 EMBER_API_URL=http://127.0.0.1:18999 EMBER_SKIP_COMPOSE=1 bin/ember doctor
echo "doctor OK"

# Mac mini probe scripts (run ON jons-mac-mini, stdlib only)
All read the oMLX bearer key from `~/.omlx/settings.json` (`.auth.api_key`) locally; nothing leaves the host.
- `tts-blind-test.py` — blind A/B TTS benchmark via oMLX `/v1/audio/speech` (shuffled labels, sealed mapping, `--reveal`). Used 2026-09-14: Kokoro-82M-bf16 vs Qwen3-TTS-0.6B → Kokoro (ADR 0007).
- `embed-probe.py` — `/v1/embeddings` dims/latency/memory probe (bge-m3-mlx-8bit → 1024 dims).
- `rerank-probe.py` — `/v1/rerank` probe (bge-reranker-v2-m3 → 2.4 s cold / 0.04 s warm, 2.38 GB resident).
Copy with `scp tools/mini/<script>.py vaxel-mini:~/` and run with `python3`.

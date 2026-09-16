#!/usr/bin/env python3
"""Blind A/B TTS benchmark through oMLX /v1/audio/speech.

Runs ON the mini (stdlib only). Reads the oMLX API key from ~/.omlx/settings.json so
it never leaves the host. For each sentence it synthesises with every candidate model,
records latency + oMLX memory delta, then writes the WAVs under randomised labels
(A/B) per sentence. The label->model mapping is written to a sealed JSON that the
listener must not open until scoring is done.

Usage:
  python3 tts-blind-test.py --out ~/tts-blind --models mlx-community/Kokoro-82M-bf16 \
      mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16 \
      --voice mlx-community/Kokoro-82M-bf16=af_heart \
      --voice mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16=Vivian
  python3 tts-blind-test.py --reveal ~/tts-blind
"""
import argparse, json, os, random, sys, time, urllib.request, urllib.error, pathlib

SENTENCES = [
    "Good morning. The kitchen lights are on and the coffee machine finished two minutes ago.",
    "Your next meeting starts at fourteen thirty. Traffic on the M25 is heavier than usual.",
    "I couldn't reach the garage door sensor. Do you want me to try again, or leave it?",
    "Reminder: the dishwasher cycle ends in ten minutes, and the bins go out tonight.",
    "It's 7 degrees outside with light rain expected around 6pm. Take a coat.",
    "The Mac mini is at 82 percent memory. I've paused the background indexer for now.",
]

def load_key():
    s = json.load(open(pathlib.Path.home() / ".omlx" / "settings.json"))
    for path in (("server", "api_key"), ("api_key",), ("auth", "api_key")):
        d = s
        try:
            for k in path:
                d = d[k]
            if d:
                return d
        except (KeyError, TypeError):
            pass
    sys.exit("no api_key in ~/.omlx/settings.json")

def http(base, path, key=None, data=None, timeout=300):
    req = urllib.request.Request(base + path, data=data, method="POST" if data else "GET")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(), dict(r.headers)

def health(base):
    st, body, _ = http(base, "/health")
    return json.loads(body)

def unload(base, key, model):
    try:
        http(base, f"/v1/models/{model}/unload", key, data=b"{}")
    except urllib.error.HTTPError as e:
        print(f"  (unload {model}: HTTP {e.code} — ignored)")

def synth(base, key, model, voice, text, fmt):
    payload = {"model": model, "input": text, "response_format": fmt}
    if voice:
        payload["voice"] = voice
    t0 = time.perf_counter()
    st, body, hdr = http(base, "/v1/audio/speech", key, data=json.dumps(payload).encode())
    return time.perf_counter() - t0, body, hdr.get("Content-Type", "")

def run(args):
    base, key = args.base, load_key()
    out = pathlib.Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    voices = dict(v.split("=", 1) for v in args.voice)
    results = []
    mapping = {}
    labels = "ABCDEFGH"[: len(args.models)]

    for mi, model in enumerate(args.models):
        print(f"\n== {model}")
        for other in args.models:
            if other != model:
                unload(base, key, other)
        h0 = health(base)
        # warm-up (model load) — timed separately
        t_load, _, _ = synth(base, key, model, voices.get(model), "Warm up.", args.format)
        h1 = health(base)
        mem = h1["engine_pool"]["current_model_memory"] - h0["engine_pool"]["current_model_memory"]
        print(f"  load+first synth: {t_load:.2f}s  model mem delta: {mem/1e9:.2f} GB  loaded_count={h1['engine_pool']['loaded_count']}")
        for si, text in enumerate(SENTENCES):
            lat, audio, ctype = synth(base, key, model, voices.get(model), text, args.format)
            fn = out / f"raw_m{mi}_s{si}.{args.format}"
            fn.write_bytes(audio)
            results.append({"model": model, "sentence": si, "latency_s": round(lat, 3), "bytes": len(audio), "chars": len(text), "content_type": ctype})
            print(f"  s{si}: {lat:.2f}s  {len(audio)/1024:.0f} KB  ({len(text)/lat:.0f} chars/s)")
        unload(base, key, model)

    # blind relabel: per sentence, shuffle which model is A/B
    rng = random.SystemRandom()
    for si in range(len(SENTENCES)):
        order = list(range(len(args.models)))
        rng.shuffle(order)
        for label, mi in zip(labels, order):
            src = out / f"raw_m{mi}_s{si}.{args.format}"
            dst = out / f"s{si}_{label}.{args.format}"
            src.rename(dst)
            mapping[dst.name] = args.models[mi]
    (out / "SEALED_mapping.json").write_text(json.dumps(mapping, indent=2))
    (out / "metrics.json").write_text(json.dumps({"results": results, "sentences": SENTENCES, "voices": voices}, indent=2))
    (out / "scoresheet.md").write_text(
        "# TTS blind test — score each clip 1-5 (naturalness, clarity, prosody). Do NOT open SEALED_mapping.json.\n\n"
        + "\n".join(f"- s{si}: A ___  B ___   — \"{t}\"" for si, t in enumerate(SENTENCES)) + "\n")
    print(f"\nClips + scoresheet.md in {out}. Mapping sealed. Run --reveal after scoring.")

def reveal(path):
    out = pathlib.Path(path).expanduser()
    mapping = json.loads((out / "SEALED_mapping.json").read_text())
    metrics = json.loads((out / "metrics.json").read_text())
    print("clip -> model"); [print(f"  {k}: {v}") for k, v in sorted(mapping.items())]
    print("\nmedian latency per model:")
    import statistics
    for m in {r["model"] for r in metrics["results"]}:
        ls = [r["latency_s"] for r in metrics["results"] if r["model"] == m]
        print(f"  {m}: {statistics.median(ls):.2f}s (n={len(ls)})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="~/tts-blind")
    ap.add_argument("--models", nargs="+")
    ap.add_argument("--voice", action="append", default=[], help="model=voice")
    ap.add_argument("--format", default="wav")
    ap.add_argument("--reveal", metavar="DIR")
    a = ap.parse_args()
    reveal(a.reveal) if a.reveal else run(a)

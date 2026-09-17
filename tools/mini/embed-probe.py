import json, time, urllib.request, urllib.error

key = json.load(open("/Users/jtotham/.omlx/settings.json"))["auth"]["api_key"]
B = "http://127.0.0.1:8000"


def call(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(B + path, data=body, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        return {"err": e.code, "body": e.read()[:300].decode(errors="ignore")}


def mem():
    return json.load(urllib.request.urlopen(B + "/health"))["engine_pool"]


m0 = mem()
t = time.perf_counter()
r = call("/v1/embeddings", {"model": "bge-m3-mlx-8bit", "input": ["The dishwasher cycle ends in ten minutes.", "Bins go out tonight."]})
t1 = time.perf_counter() - t
if "data" in r:
    print("embeddings OK: n=%d dims=%d first-call(load) %.2fs usage=%s" % (len(r["data"]), len(r["data"][0]["embedding"]), t1, r.get("usage")))
else:
    print("embeddings ERR:", r)
t = time.perf_counter()
r = call("/v1/embeddings", {"model": "bge-m3-mlx-8bit", "input": ["warm call number %d about the homelab" % i for i in range(8)]})
print("8-text warm call %.2fs" % (time.perf_counter() - t), "ok" if "data" in r else r)
m1 = mem()
print("mem delta %.2f GB loaded_count=%d" % ((m1["current_model_memory"] - m0["current_model_memory"]) / 1e9, m1["loaded_count"]))
t = time.perf_counter()
r = call("/v1/rerank", {"model": "bge-m3-mlx-8bit", "query": "when do bins go out", "documents": ["Bins go out tonight.", "Coffee is ready.", "Meeting at 14:30."], "top_n": 2})
print("rerank via bge-m3 (expect unsupported): %s  %.2fs" % (json.dumps(r)[:220], time.perf_counter() - t))

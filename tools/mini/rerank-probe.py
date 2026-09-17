import json, time, urllib.request, urllib.error
key = json.load(open("/Users/jtotham/.omlx/settings.json"))["auth"]["api_key"]
B = "http://127.0.0.1:8000"
def call(path, payload=None, timeout=300):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(B + path, data=body, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"err": e.code, "body": e.read()[:400].decode(errors="ignore")}
models = [m["id"] for m in call("/v1/models")["data"]]
print("models:", models)
mid = next((m for m in models if "reranker" in m.lower()), None)
print("reranker id:", mid)
if mid:
    m0 = json.load(urllib.request.urlopen(B + "/health"))["engine_pool"]["current_model_memory"]
    t = time.perf_counter()
    r = call("/v1/rerank", {"model": mid, "query": "when do the bins go out", "documents": ["Bins go out tonight.", "The coffee machine finished.", "Meeting at 14:30.", "Recycling is collected on Thursdays."], "top_n": 2})
    print("rerank first call %.2fs:" % (time.perf_counter() - t), json.dumps(r)[:500])
    t = time.perf_counter()
    r2 = call("/v1/rerank", {"model": mid, "query": "coffee", "documents": ["Bins go out tonight.", "The coffee machine finished."], "top_n": 1})
    print("rerank warm %.2fs:" % (time.perf_counter() - t), json.dumps(r2)[:300])
    m1 = json.load(urllib.request.urlopen(B + "/health"))["engine_pool"]
    print("mem delta %.2f GB, loaded_count=%d" % ((m1["current_model_memory"] - m0) / 1e9, m1["loaded_count"]))

#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
E1 = ROOT / "api-study" / "exploratory"
BUNDLE = "AU-E1-S2-b021f4b9caf73dad"
BLINDED = E1 / "e1" / "stage2" / "generated" / BUNDLE / "blinded"
INDEX = BLINDED / "STAGE2_PACKET_INDEX.json"
PARTITIONS = E1 / "e1" / "stage2" / "partitions" / BUNDLE / "P1D3" / "PARTITIONS.jsonl"
PASSAGES = ROOT / "api-study" / "passages.json"
PROTOCOL = E1 / "E1_BLIND_BUNDLE_FINALIZATION_F1.md"
OUT = E1 / "e1" / "blind_bundle" / "AU-E1-BLIND-v1"
ATTEMPTS = OUT / "CLUSTER_LABEL_ATTEMPTS.jsonl"
LABELS = OUT / "CLUSTER_LABELS.jsonl"
ANCHORS = OUT / "FOCAL_ANCHORS.json"
RECORD = OUT / "BLIND_SEMANTIC_BUNDLE_RECORD.json"
INFLIGHT = OUT / "INFLIGHT_CLUSTER_LABEL.json"

PARTITION_FREEZE = "fb54cd0c37841e880372694e056d985ac3272b40"
EXPECTED_SHA = "605d95f063d01349e95ebb126aa512796cb4f1fc9b12fae7862bacb8073e2aea"
MODEL = "gpt-5.6-sol"
MAX_ATTEMPTS = 3
MAX_OUTPUT = 12000
COST_GUARD = 10.0

SYSTEM = """Name already-fixed semantic clusters in a blinded research dataset.
For every cluster, write one concise descriptive name for its shared informational
answer-space, preferably 12 words or fewer. Return names in the exact cluster
order supplied. Do not merge, split, repair, reorder, or adjudicate clusters.
Base names only on the supplied canonical targets. Do not infer or mention
experimental condition, original model/provider, multiplicity, topic metadata,
hypotheses, or results. Singleton clusters still receive a concise name."""

def now(): return datetime.now(timezone.utc).isoformat()

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1048576), b""): h.update(b)
    return h.hexdigest()

def cj(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":"))

def load(path): return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def append(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a",encoding="utf-8",newline="\n") as f:
        f.write(cj(x)+"\n"); f.flush(); os.fsync(f.fileno())

def write(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")

def git(*a): return subprocess.run(["git",*a],cwd=ROOT,capture_output=True,text=True,check=False)

def verify(commit):
    if git("verify-commit",commit).returncode: raise ValueError("Implementation commit signature failed")
    if git("merge-base","--is-ancestor",PARTITION_FREEZE,commit).returncode: raise ValueError("Partition freeze not ancestor")
    for p in (Path(__file__).resolve(), PROTOCOL):
        rel=p.relative_to(ROOT).as_posix()
        r=git("show",f"{commit}:{rel}")
        if r.returncode: raise ValueError(f"{rel} absent from signed commit")
        if p.read_text(encoding="utf-8").replace("\r\n","\n") != r.stdout.replace("\r\n","\n"):
            raise ValueError(f"Working copy differs from signed commit: {rel}")

def env():
    for p in (ROOT/".env", ROOT/"api-study"/".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                s=line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k,v=s.split("=",1); os.environ.setdefault(k.strip(),v.strip().strip("'\""))

def source():
    if sha(PARTITIONS)!=EXPECTED_SHA: raise ValueError("P1D3 partition SHA mismatch")
    ps=rows(PARTITIONS)
    if len(ps)!=72: raise ValueError(f"Expected 72 partitions, got {len(ps)}")
    idx=load(INDEX); packets={}
    for item in idx["packets"]:
        p=ROOT/item["path"]
        if sha(p)!=item["sha256"]: raise ValueError(f"Packet hash mismatch: {item['packet_id']}")
        obj=load(p); packets[obj["packet_id"]]=obj
    if len(packets)!=24: raise ValueError("Expected 24 packets")
    return ps,packets

def payload(row,packet):
    tm={t["target_id"]:t["canonical_target"] for t in packet["targets"]}
    cls=[]
    for c in row["partition"]["clusters"]:
        cls.append({"cluster_id":c["cluster_id"],"canonical_targets":[tm[t] for t in c["target_ids"]]})
    return {"packet_id":row["packet_id"],"partition_replicate":row["partition_replicate"],"clusters":cls}

def schema(n):
    return {"type":"object","properties":{
        "packet_id":{"type":"string"},
        "partition_replicate":{"type":"string"},
        "names":{"type":"array","items":{"type":"string"},"minItems":n,"maxItems":n}},
        "required":["packet_id","partition_replicate","names"],"additionalProperties":False}

def validate(text,p):
    x=json.loads(text.strip())
    if set(x)!={"packet_id","partition_replicate","names"}: raise ValueError("Unexpected root fields")
    if x["packet_id"]!=p["packet_id"] or x["partition_replicate"]!=p["partition_replicate"]: raise ValueError("Identity mismatch")
    if not isinstance(x["names"],list) or len(x["names"])!=len(p["clusters"]): raise ValueError("Name count mismatch")
    if any(not isinstance(n,str) or not n.strip() for n in x["names"]): raise ValueError("Empty/nonstring name")
    return x

def state():
    done={}; counts={}; cost=0.0
    for r in rows(ATTEMPTS):
        t=r["task_id"]; counts[t]=counts.get(t,0)+1
        c=r.get("usage",{}).get("conservative_cost_usd")
        if isinstance(c,(int,float)): cost+=c
        if r["status"]=="valid":
            if t in done: raise ValueError(f"Multiple valid label outputs: {t}")
            done[t]=r["parsed"]
    return done,counts,cost

def write_labels(ps,done):
    LABELS.parent.mkdir(parents=True,exist_ok=True)
    with LABELS.open("w",encoding="utf-8",newline="\n") as f:
        for r in sorted(ps,key=lambda x:x["task_id"]):
            if r["task_id"] not in done: continue
            names=done[r["task_id"]]["names"]
            out={"schema_version":"au-e1-cluster-labels-v1","task_id":r["task_id"],
                 "packet_id":r["packet_id"],"partition_replicate":r["partition_replicate"],
                 "clusters":[{"cluster_id":c["cluster_id"],"descriptive_name":n.strip(),
                              "member_count":len(c["target_ids"])}
                             for c,n in zip(r["partition"]["clusters"],names)]}
            f.write(cj(out)+"\n")

def final_sentence(s):
    parts=[x.strip() for x in re.split(r"(?<=[.!?])\s+",s.strip()) if x.strip()]
    return parts[-1]

def write_anchors():
    x=load(PASSAGES); aa=[]
    for t in x["topics"]:
        p=t["variants"]["explicit_gap"]
        aa.append({"topic_id":t["topic_id"],"source_variant":"explicit_gap",
                   "focal_unknown_anchor":final_sentence(p),"source_passage":p,
                   "extraction_rule":"verbatim final sentence of explicit_gap passage"})
    if len(aa)!=12: raise ValueError("Expected 12 anchors")
    write(ANCHORS,{"schema_version":"au-e1-focal-anchors-v1","anchor_count":12,
                   "metadata_joined_to_semantic_outputs":False,"anchors":aa})

def preflight(commit=None):
    ps,packets=source()
    if commit: verify(commit)
    for r in ps: payload(r,packets[r["packet_id"]])
    done,counts,cost=state()
    ks=[len(r["partition"]["clusters"]) for r in ps]
    return {"status":"blind_bundle_preflight_complete_no_api_calls","partitions":72,
            "fixed_clusters":sum(ks),"cluster_count_range":[min(ks),max(ks)],
            "completed_label_tasks_existing":len(done),"attempt_records_existing":sum(counts.values()),
            "cost_usd_existing":round(cost,6),"inflight_exists":INFLIGHT.exists(),
            "focal_anchor_topics":len(load(PASSAGES)["topics"]),
            "original_model_gap_metadata_joined":False}

def run(commit):
    verify(commit); env(); ps,packets=source()
    key=os.environ.get("OPENAI_API_KEY")
    if not key: raise SystemExit("Missing OPENAI_API_KEY")
    if INFLIGHT.exists(): raise SystemExit(f"Ambiguous inflight marker exists: {INFLIGHT}")
    from openai import OpenAI
    client=OpenAI(api_key=key,max_retries=0,timeout=600.0)
    order=sorted(ps,key=lambda r:(-len(r["partition"]["clusters"]),r["task_id"]))
    for r in order:
        done,counts,cost=state(); tid=r["task_id"]
        if tid in done: continue
        if counts.get(tid,0)>=MAX_ATTEMPTS: raise SystemExit(f"Exhausted: {tid}")
        if cost>=COST_GUARD: raise SystemExit(f"Cost guard reached: ${cost:.4f}")
        p=payload(r,packets[r["packet_id"]])
        attempt=counts.get(tid,0)+1
        while attempt<=MAX_ATTEMPTS:
            marker={"task_id":tid,"attempt_index":attempt,"started_at":now()}
            write(INFLIGHT,marker); start=time.monotonic()
            base={"schema_version":"au-e1-cluster-label-attempt-v1","task_id":tid,
                  "packet_id":r["packet_id"],"partition_replicate":r["partition_replicate"],
                  "attempt_index":attempt,"model":MODEL,"reasoning_effort":"low",
                  "started_at":marker["started_at"]}
            try:
                resp=client.responses.create(model=MODEL,instructions=SYSTEM,input=cj(p),
                    max_output_tokens=MAX_OUTPUT,reasoning={"effort":"low"},
                    text={"format":{"type":"json_schema","name":"e1_cluster_names",
                                    "strict":True,"schema":schema(len(p["clusters"]))}})
                raw=resp.model_dump(mode="json"); u=raw.get("usage") or {}
                it=u.get("input_tokens"); ot=u.get("output_tokens")
                cc=(it/1e6*4+ot/1e6*20) if isinstance(it,(int,float)) and isinstance(ot,(int,float)) else None
                try:
                    parsed=validate(resp.output_text,p); status="valid"; err=None
                except Exception as e:
                    parsed=None; status="invalid_output"; err=f"{type(e).__name__}: {e}"
                rec={**base,"status":status,"finished_at":now(),
                     "elapsed_seconds":round(time.monotonic()-start,6),"raw_text":resp.output_text,
                     "parsed":parsed,"parse_error":err,
                     "usage":{"input_tokens":it,"output_tokens":ot,"conservative_cost_usd":cc},
                     "raw_provider_response":raw}
            except Exception as e:
                rec={**base,"status":"api_error","finished_at":now(),
                     "elapsed_seconds":round(time.monotonic()-start,6),
                     "error_type":type(e).__name__,"error":str(e),
                     "usage":{"input_tokens":None,"output_tokens":None,"conservative_cost_usd":None}}
            append(ATTEMPTS,rec)
            try: INFLIGHT.unlink()
            except FileNotFoundError: pass
            done,_,_=state(); write_labels(ps,done)
            if tid in done: break
            if attempt>=MAX_ATTEMPTS: raise SystemExit(f"Exhausted: {tid}")
            time.sleep(5); attempt+=1
    write_anchors()
    return finalize(commit)

def finalize(commit):
    verify(commit); ps,_=source(); done,_,cost=state()
    write_labels(ps,done); write_anchors()
    if len(done)!=72 or INFLIGHT.exists(): raise SystemExit("Blind bundle incomplete")
    lr=rows(LABELS); fixed=sum(len(r["partition"]["clusters"]) for r in ps)
    named=sum(len(r["clusters"]) for r in lr)
    if len(lr)!=72 or named!=fixed: raise ValueError("Label coverage mismatch")
    if load(ANCHORS)["anchor_count"]!=12: raise ValueError("Anchor coverage mismatch")
    rec={"schema_version":"au-e1-blind-semantic-bundle-record-v1",
         "status":"complete_pre_metadata_join","created_at":now(),
         "partition_freeze_commit":PARTITION_FREEZE,"f1_implementation_commit":commit,
         "original_model_gap_metadata_joined":False,"private_e1_keys_read_by_f1":False,
         "partitions":72,"fixed_clusters":fixed,"named_clusters":named,"focal_anchors":12,
         "naming_model":MODEL,"naming_cost_usd":round(cost,6),
         "hashes":{"p1d3_partitions_sha256":sha(PARTITIONS),
                   "stage2_packet_index_sha256":sha(INDEX),"passages_sha256":sha(PASSAGES),
                   "cluster_label_attempts_sha256":sha(ATTEMPTS),"cluster_labels_sha256":sha(LABELS),
                   "focal_anchors_sha256":sha(ANCHORS),"protocol_sha256":sha(PROTOCOL),
                   "runner_sha256":sha(Path(__file__).resolve())}}
    write(RECORD,rec); return rec

def status():
    done,counts,cost=state()
    print(json.dumps({"status":"complete" if len(done)==72 else "incomplete",
      "completed_label_tasks":len(done),"remaining_label_tasks":72-len(done),
      "attempt_records":sum(counts.values()),"cost_usd":round(cost,6),
      "inflight_exists":INFLIGHT.exists(),"record_exists":RECORD.exists()},indent=2,sort_keys=True))

def main():
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("preflight"); p.add_argument("--implementation-commit")
    p=sp.add_parser("run"); p.add_argument("--implementation-commit",required=True)
    p=sp.add_parser("finalize"); p.add_argument("--implementation-commit",required=True)
    sp.add_parser("status"); a=ap.parse_args()
    if a.cmd=="preflight": print(json.dumps(preflight(a.implementation_commit),indent=2,sort_keys=True))
    elif a.cmd=="run": print(json.dumps(run(a.implementation_commit),indent=2,sort_keys=True))
    elif a.cmd=="finalize": print(json.dumps(finalize(a.implementation_commit),indent=2,sort_keys=True))
    else: status()

if __name__=="__main__": main()

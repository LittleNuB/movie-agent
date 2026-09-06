"""Export local evidence summaries without credentials, signed URLs, prompts, or media bytes."""
import argparse
import json
from datetime import datetime
from pathlib import Path

from movie_agent.store import Store, now


def summarize(store, pid):
    project = store.project(pid)
    jobs = store.records(pid, "jobs")
    runs = store.records(pid, "runs")
    artifacts = store.records(pid, "artifacts")
    def elapsed(start, end):
        return round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds(), 3) if start and end else None
    return {
        "project_id": pid, "title": project["title"], "mode": project["mode"], "created": project["created"],
        "exported": now(), "status": project["status"], "adopted": project["adopted"],
        "observed_wall_seconds": elapsed(project["created"], now()),
        "wall_note": "Includes development interruptions and review waits; not a clean generation benchmark.",
        "jobs": [{"id": j["id"], "title": j["title"], "purpose": j["purpose"], "status": j["status"],
                  "model": (j.get("binding") or {}).get("model"), "unit_id": j.get("unit_id") or j.get("args", {}).get("unit_id"),
                  "external_id": j.get("external_id"), "artifact_ids": j.get("artifact_ids", []),
                  "generation_resolution": j.get("args", {}).get("parameters", {}).get("resolution"),
                  "failure_code": j.get("failure_code"),
                  "usage": j.get("usage", {}), "cost": j.get("cost"), "started": j.get("started"), "finished": j.get("finished"),
                  "elapsed_seconds": elapsed(j.get("started"), j.get("finished")), "error_type": j.get("error_type"),
                  "candidate_only": j.get("candidate_only", False), "reference_count": len(j.get("args", {}).get("references", []))}
                 for j in jobs],
        "runs": [{k: r.get(k) for k in ("id", "role", "status", "input_tokens", "output_tokens", "error_type")} for r in runs],
        "recorded_llm_tokens": {k: sum(r.get(k, 0) for r in runs) for k in ("input_tokens", "output_tokens")},
        "token_note": "Earlier vision probes did not record tokens; provider usage and recorded LLM tokens are incomplete billing evidence.",
        "reviews": [{k: r.get(k) for k in ("id", "artifact_id", "kind", "status", "authority", "created", "evidence_message_id")}
                    for r in store.records(pid, "reviews")],
        "artifacts": [{"id": a["id"], "kind": a["kind"], "title": a["title"], "has_file": bool(a.get("path")),
                       "duration": a.get("meta", {}).get("media", {}).get("duration"),
                       "streams": a.get("meta", {}).get("media", {}).get("streams", []),
                       "output_resolution": a.get("meta", {}).get("output_resolution"),
                       "source_conversions": a.get("meta", {}).get("source_conversions", []),
                       "source_job": a.get("meta", {}).get("job_id"), "basis": a.get("meta", {}).get("basis", {}),
                       "picture_master_id": a.get("meta", {}).get("picture_master_id"), "edit": a.get("meta", {}).get("edit")}
                      for a in artifacts],
        "billing_status": "unreconciled" if any(j.get("cost") is None and j["purpose"] != "compose" for j in jobs) else "recorded",
        "human_review": "pending",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("local-data"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summarize(Store(args.data), args.project), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {args.project}; billing and human review remain separately tracked.")

"""Dry-run-first orchestration of the pinned vLLM CLI; no engine reimplementation."""

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_config(experiment, cache_mode=None, kv_gib=None):
    experiments = read_json(ROOT / "configs/experiments.json")
    if experiment not in experiments:
        raise ValueError(f"Unknown experiment: {experiment}")
    cfg = copy.deepcopy(experiments[experiment])
    if cache_mode is not None:
        cfg["prefix_cache"] = cache_mode == "on"
        cfg["cache_state"] = "not_controlled_pilot" if cfg["prefix_cache"] else "prefix_reuse_disabled"
    if kv_gib is not None:
        if kv_gib not in (1, 2, 4, 8):
            raise ValueError("KV GiB must be one of 1, 2, 4, 8")
        cfg["kv_bytes"] = kv_gib * 1024**3
    length = cfg.get("input_tokens", cfg.get("prefix_tokens", 0) + cfg.get("suffix_tokens", 0))
    if length + cfg["output_tokens"] > cfg["max_model_len"]:
        raise ValueError("Input + output exceeds max_model_len")
    for key in ("kv_bytes", "num_requests", "concurrency", "batch_tokens", "max_num_seqs"):
        if cfg[key] <= 0:
            raise ValueError(f"{key} must be positive")
    return cfg


def command_for(args, cfg, model_id, model_dir, output):
    cli = str(ROOT / ".venv/bin/vllm")
    if args.action == "server":
        cmd = [cli, "serve", model_dir, "--served-model-name", model_id,
               "--host", "127.0.0.1", "--port", str(args.port),
               "--dtype", "bfloat16", "--kv-cache-dtype", "auto",
               "--tensor-parallel-size", "1", "--max-model-len", str(cfg["max_model_len"]),
               "--max-num-seqs", str(cfg["max_num_seqs"]),
               "--max-num-batched-tokens", str(cfg["batch_tokens"]),
               "--enable-chunked-prefill", "--generation-config", "vllm",
               "--kv-cache-memory-bytes", str(cfg["kv_bytes"]),
               "--enable-prefix-caching" if cfg["prefix_cache"] else "--no-enable-prefix-caching"]
        if args.experiment == "E0":
            cmd.append("--enforce-eager")
        return cmd
    if args.action == "collect":
        return None
    cmd = [cli, "bench", "serve", "--backend", "vllm", "--base-url", args.base_url,
           "--endpoint", "/v1/completions", "--model", model_id,
           "--tokenizer", model_dir, "--dataset-name", cfg["dataset"],
           "--num-prompts", str(cfg["num_requests"]), "--max-concurrency", str(cfg["concurrency"]),
           "--request-rate", str(cfg["request_rate"]), "--seed", str(cfg["seed"]),
           "--ignore-eos", "--num-warmups", "0", "--save-result", "--save-detailed",
           "--metric-percentiles", "50,95,99", "--result-dir", str(output),
           "--result-filename", "benchmark.json"]
    if cfg["dataset"] == "random":
        cmd += ["--random-input-len", str(cfg["input_tokens"]),
                "--random-output-len", str(cfg["output_tokens"]),
                "--random-prefix-len", "0", "--random-range-ratio", "0.0"]
    else:
        cmd += ["--prefix-repetition-prefix-len", str(cfg["prefix_tokens"]),
                "--prefix-repetition-suffix-len", str(cfg["suffix_tokens"]),
                "--prefix-repetition-num-prefixes", str(cfg["num_prefixes"]),
                "--prefix-repetition-output-len", str(cfg["output_tokens"])]
    return cmd


def git_value(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def validate_url(value):
    url = urllib.parse.urlparse(value)
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
        raise ValueError("base-url must be HTTP(S) without embedded credentials")
    if url.path not in ("", "/") or url.query or url.fragment:
        raise ValueError("base-url must be the server root, without path/query/fragment")


def validate_execution(args, cfg, model_id):
    if sys.platform != "linux":
        raise ValueError("Actual serving/benchmark execution requires Linux/WSL")
    if not args.approval_id or not args.run_id:
        raise ValueError("Execution requires --approval-id and unique --run-id")
    if not args.gpu_uuid or not re.fullmatch(r"GPU-[A-Za-z0-9-]+", args.gpu_uuid):
        raise ValueError("Provide the approved --gpu-uuid, not a guessed index")
    if args.action == "collect":
        return
    if not args.model_revision or not re.fullmatch(r"[a-fA-F0-9]{40}", args.model_revision):
        raise ValueError("Provide an immutable 40-hex --model-revision")
    if not args.model_dir or not Path(args.model_dir).is_dir():
        raise ValueError("Provide a previously downloaded local --model-dir snapshot")
    lock = read_json(ROOT / "configs/engine.json")
    engine = ROOT / "engines/vllm"
    if git_value(engine, "rev-parse", "HEAD") != lock["baseline_sha"]:
        raise ValueError("Engine HEAD differs from baseline lock; approve another protocol first")
    if git_value(engine, "status", "--porcelain"):
        raise ValueError("Baseline engine has uncommitted changes")
    py = ROOT / ".venv/bin/python"
    if not py.is_file() or not (ROOT / ".venv/bin/vllm").is_file():
        raise ValueError("Install and validate the pinned engine in .venv first")
    code = "import importlib.util; print(importlib.util.find_spec('vllm').origin)"
    origin = subprocess.check_output([str(py), "-c", code], text=True).strip()
    if not Path(origin).resolve().is_relative_to(engine.resolve()):
        raise ValueError("Installed vLLM is not this editable engine checkout")
    if args.action == "bench":
        if not args.server_manifest:
            raise ValueError("Benchmark requires your own --server-manifest")
        server = read_json(args.server_manifest)
        for key, expected in (("model_id", model_id), ("model_revision", args.model_revision),
                              ("gpu_uuid", args.gpu_uuid), ("approval_id", args.approval_id)):
            if server.get(key) != expected:
                raise ValueError(f"Server manifest mismatch: {key}")
        if server.get("action") != "server":
            raise ValueError("Not a server manifest")
        if server.get("base_url") != args.base_url:
            raise ValueError("Server URL differs; use the approved instance or matching SSH tunnel")
        for key in ("prefix_cache", "kv_bytes", "max_model_len", "max_num_seqs", "batch_tokens"):
            if server["config"][key] != cfg[key]:
                raise ValueError(f"Server config mismatch: {key}")


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def snapshot(base_url, destination):
    url = base_url.rstrip("/") + "/metrics"
    with urllib.request.urlopen(url, timeout=5) as response:
        destination.write_bytes(response.read())


def collect(args, output):
    deadline = time.monotonic() + args.duration
    with (output / "samples.jsonl").open("w", encoding="utf-8") as stream:
        while time.monotonic() < deadline:
            stamp = time.time_ns()
            record = {"utc": utc(), "monotonic": time.monotonic()}
            try:
                snapshot(args.base_url, output / f"metrics-{stamp}.txt")
            except (urllib.error.URLError, TimeoutError) as exc:
                record["metrics_error"] = str(exc)
            try:
                result = subprocess.run([
                    "nvidia-smi", "--id", args.gpu_uuid,
                    "--query-gpu=uuid,memory.used,memory.free,utilization.gpu,power.draw",
                    "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
                record["gpu_csv"] = result.stdout.strip()
                if result.returncode:
                    record["gpu_error"] = result.stderr.strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                record["gpu_error"] = str(exc)
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            time.sleep(min(args.interval, max(0, deadline - time.monotonic())))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("action", choices=["server", "bench", "collect"])
    result.add_argument("--experiment", choices=["E0", "E1", "E3"], default="E0")
    result.add_argument("--cache-mode", choices=["on", "off"])
    result.add_argument("--kv-gib", type=int, choices=[1, 2, 4, 8])
    result.add_argument("--execute", action="store_true")
    result.add_argument("--approval-id")
    result.add_argument("--run-id")
    result.add_argument("--gpu-uuid")
    result.add_argument("--model-dir")
    result.add_argument("--model-revision")
    result.add_argument("--server-manifest", type=Path)
    result.add_argument("--port", type=int, default=18000)
    result.add_argument("--base-url", default="http://127.0.0.1:18000")
    result.add_argument("--duration", type=float, default=60)
    result.add_argument("--interval", type=float, default=1)
    return result


def main(argv=None):
    arg_parser = parser()
    args = arg_parser.parse_args(argv)
    try:
        validate_url(args.base_url)
        if not 1 <= args.port <= 65535:
            raise ValueError("port out of range")
        if args.action == "server":
            args.base_url = f"http://127.0.0.1:{args.port}"
        if not 0 < args.interval <= args.duration <= 3600:
            raise ValueError("Require 0 < interval <= duration <= 3600")
        if args.run_id and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", args.run_id):
            raise ValueError("Unsafe run-id")
        cfg = load_config(args.experiment, args.cache_mode, args.kv_gib)
        model_id = read_json(ROOT / "configs/models.json")[cfg["model"]]["id"]
        model_dir = args.model_dir or "<LOCAL_IMMUTABLE_MODEL_SNAPSHOT>"
        output = ROOT / "results/raw" / (args.run_id or "<UNIQUE_RUN_ID>")
        cmd = command_for(args, cfg, model_id, model_dir, output)
        plan = {"action": args.action, "experiment": args.experiment, "config": cfg,
                "model_id": model_id, "model_revision": args.model_revision,
                "gpu_uuid": args.gpu_uuid, "approval_id": args.approval_id,
                "output_dir": str(output), "base_url": args.base_url,
                "command": cmd, "command_display": shlex.join(cmd) if cmd else None,
                "execute": args.execute, "state": "pilot_not_formal_baseline"}
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        if not args.execute:
            return 0
        validate_execution(args, cfg, model_id)
        output.mkdir(parents=True, exist_ok=False)
        plan.update({"utc_started": utc(), "main_sha": git_value(ROOT, "rev-parse", "HEAD"),
                     "main_dirty": bool(git_value(ROOT, "status", "--porcelain")),
                     "engine_sha": git_value(ROOT / "engines/vllm", "rev-parse", "HEAD"),
                     "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()})
        manifest = output / "manifest.json"
        manifest.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            if args.action == "collect":
                collect(args, output)
                code = 0
            else:
                if args.action == "bench":
                    snapshot(args.base_url, output / "metrics_before.txt")
                env = os.environ.copy()
                env["CUDA_VISIBLE_DEVICES"] = args.gpu_uuid
                env["HF_HUB_OFFLINE"] = "1"
                env["TRANSFORMERS_OFFLINE"] = "1"
                with (output / f"{args.action}.log").open("w", encoding="utf-8") as log:
                    code = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
                if args.action == "bench":
                    snapshot(args.base_url, output / "metrics_after.txt")
        except KeyboardInterrupt:
            code = 130
            plan["execution_error"] = "Interrupted by operator"
        except (OSError, subprocess.SubprocessError, urllib.error.URLError) as exc:
            code = 2
            plan["execution_error"] = str(exc)
        plan.update({"utc_finished": utc(), "exit_code": code})
        manifest.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return code
    except (ValueError, OSError, subprocess.SubprocessError, urllib.error.URLError) as exc:
        arg_parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())

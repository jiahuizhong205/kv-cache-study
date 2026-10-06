# Experiment repository instructions

- This repository organizes inference experiments, not training.
- Preserve the pinned, unmodified baseline in `engines/vllm`; its own
  `AGENTS.md` and domain instructions apply to engine changes.
- Read `docs/BASELINE_PROTOCOL.md` and `docs/STATUS.md` before experiment changes.
- Never launch a model, download weights, install GPU dependencies, contact a
  remote server or terminate a process without explicit user authorization.
- Scripts default to dry-run. Do not remove approval or source-version guards.
- Distinguish local tests, GPU smoke tests and validated performance results.
- Never commit tokens, `.env`, internal addresses, model weights or raw results.
- Preserve the original local `vllm/` copy until the replacement is verified;
  it is ignored by the experiment repository.
- Keep engine changes separate from workload/analysis changes; record both SHAs.
- Test orchestration with the project's isolated `.venv-checks` or `.venv`.
  Actual engine development follows upstream's `uv` environment instructions.
- Do not auto-update the submodule or use a floating `latest` experiment version.

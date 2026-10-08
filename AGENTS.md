# Experiment repository instructions

- This repository organizes inference experiments, not training.
- `engines/vllm` is ordinary source tracked by this monorepo, not a submodule.
  Preserve the pinned baseline identity in `configs/engine.json`; its own
  `AGENTS.md` and domain instructions apply to engine changes.
- Read `docs/BASELINE_PROTOCOL.md` and `docs/STATUS.md` before experiment changes.
- Never launch a model, download weights, install GPU dependencies, contact a
  remote server or terminate a process without explicit user authorization.
- Scripts default to dry-run. Do not remove approval or source-version guards.
- Distinguish local tests, GPU smoke tests and validated performance results.
- Never commit tokens, `.env`, internal addresses, model weights or raw results.
- Cleanup backups in `.cleanup-backups/` are private local material; never publish them.
- Keep engine changes separate from workload/analysis changes when possible;
  record the monorepo commit SHA, engine tree SHA and upstream baseline SHA.
- Test orchestration with the project's isolated `.venv-checks` or `.venv`.
  Actual engine development follows upstream's `uv` environment instructions.
- Do not auto-update vendored source or use a floating `latest` experiment version.
- Mechanism development belongs on a feature branch. Do not bypass baseline
  source-tree guards to run modified code under the vanilla baseline label.

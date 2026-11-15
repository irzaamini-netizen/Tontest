# TON Security Engine — Benchmark & Quality Evaluation

Independent evaluation suite. Does not modify core analysis rules or parsers.

## Dataset

- `datasets/real_projects.json`  
  Curated list of public TON repositories (wallets, jettons, NFTs, DEX, staking, governance) for baseline static analysis.

## Preparing the local baseline

```bash
# from the repository root (or adjust paths)
python tonsec_v020/benchmark/tools/prepare_dataset.py \
  --dataset tonsec_v020/benchmark/datasets/real_projects.json \
  --outdir ~/tonsec-baseline-projects
```

Optional:

```bash
# only first N projects
python tonsec_v020/benchmark/tools/prepare_dataset.py \
  --dataset tonsec_v020/benchmark/datasets/real_projects.json \
  --outdir ~/tonsec-baseline-projects \
  --limit 5
```

The script performs shallow clones and writes `manifest.json` with commit SHAs and source-file counts.

## Running baseline scan (read-only)

After the dataset is prepared:

```bash
tonsec run ~/tonsec-baseline-projects --out ~/tonsec-baseline-report-$(date +%Y%m%d)
```

or per-project with `tonsec batch` / `tonsec scan`.

## Evaluation principles

1. Run the engine **without code changes** on the prepared set (baseline).
2. Record coverage, partial files, findings, parse errors and runtime.
3. Manually or semi-automatically classify True/False Positives and Negatives on a sample.
4. Only then prioritise parser or rule improvements based on measured gaps.

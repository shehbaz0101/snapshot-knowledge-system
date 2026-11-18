#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
python3 harness/run_eval.py --submission submission --eval eval/public_eval.jsonl --out results/public
python3 harness/run_eval.py --submission submission --eval eval_extra/questions.jsonl --out results/extra
python3 harness/run_eval.py --submission submission --eval harness/selftest/eval.jsonl --snapshots harness/selftest/snapshots --conflicts-gold harness/selftest/conflicts_gold.json --out results/selftest

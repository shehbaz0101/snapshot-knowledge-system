# Snapshot knowledge system

An offline, deterministic Python system for the interface.ai assignment. It answers from the supplied Dupaco crawls, keeps historical versions and cites the evidence behind each answer. It requires no API keys or third-party packages.

## Setup and run

Use Python 3.11 or newer. From a fresh clone, place the kit's `snapshots_zip/` directory in the repository root, beside `harness/`, `eval/` and `submission/`. The harness extracts missing snapshots automatically. Existing extracted snapshots are reused. The supplied crawl data is excluded from version control and should not be redistributed.

```sh
python3 harness/run_eval.py --submission submission --eval eval/public_eval.jsonl --out results/public
./scripts/run_all_evals.sh
python3 scripts/ask.py "What APR applies to a 2014 motorcycle over 48 months?"
python3 scripts/ask.py "What is the 17-month certificate APY?" --as-of 2026-06-30
python3 -m unittest discover -s tests -v
```

The combined script runs unit tests, the public evaluation, 35 extra questions and the harness self-test with its conflict gold file. Reports and answers go to `results/public/`, `results/extra/` and `results/selftest/`. The question CLI prints answer text, sources, confidence and conflict notes as JSON. `.env.example` contains commented placeholders only; the implementation does not use keys or environment-dependent model paths.

## Architecture

`submission/solution.py` is the contract-compatible entry point. Its `build()` returns an object implementing `ingest(snapshot)`, `answer(question, as_of=None)` and `conflicts()`.

| Module under `submission/ks/` | Responsibility |
| --- | --- |
| `store.py` | Complete versioned snapshots, table and passage indexes |
| `tables.py` | Markdown table extraction, inclusive model-year and dollar-range parsing |
| `query.py` | Date interpretation, product families and rate intent |
| `retrieval.py` | Binary-term BM25, generic synonyms, answer-shape scoring and extracted links |
| `answer.py` | Tier filtering, metric selection, concise evidence composition and abstention |
| `authority.py` | Page authority rules |
| `conflicts.py` | Contradictions between matching structured facts and their resolutions |
| `text.py` | Shared text cleanup and number-word normalization |

The solution never loads evaluation questions or expected answers. Product vocabulary maps cars and vehicles to auto loans, separates home equity lines from credit cards, and distinguishes boat/RV loans from ATV/snowmobile/jet-ski tables. Prose retrieval uses lexical coverage, phrases, page titles, named entities, publication dates and answer shapes such as numbers, dates, addresses and times. All returned URLs are extracted from selected-crawl links; there is no answer URL lookup table.

## Design decisions

- Offline and deterministic. Standard library only, no model calls, no randomness. This keeps answers repeatable (the consistency pillar) and fast (p95 well under 2 seconds), and it means the submission runs in a clean Python 3.11 environment with nothing to install.
- Keep history, not just the latest copy. Every snapshot is stored whole with its rows and passages, so `as_of` questions are answered from the website as it stood on that date.
- Structured facts first, prose second. Rate questions go to parsed markdown table rows (product, term, tier, metric). Everything else goes to BM25 passage retrieval with authority and answer-shape scoring.
- One value per fact. The scorer zeroes any answer that also repeats a stale or other-tier number, so the system states a single value instead of hedging.
- No answers keyed to the practice questions. The code never reads the eval files, and URLs in answers are taken from links in the selected crawl.

## What "current" means

Without `as_of`, current means the newest supplied crawl. A historical date selects the latest crawl on or before that date. Dates before the first crawl select the first snapshot. Month-name dates inside the question ("as of May 2026") are also understood. Normal retrieval excludes pages absent from the selected snapshot. One general fallback for an exact non-rate fee match can return last-observed evidence from a page that has disappeared; it keeps the older citation and labels the evidence as last observed.

Structured rate selection filters product, term, model year, amount, business or personal scope and jumbo or standard status before composing an answer. Shortened and reversed year ranges ("2024-27", "2026-23"), older-than tiers ("2016 and older"), monetary ranges without a second dollar sign and open-ended amount tiers ("$40,000+") are parsed into numeric ranges and matched against the year or amount in the question. APY, dividend rate and APR are separate metrics. Payment examples ("If you borrow $7,500 at 8.34% APR...") are illustrations and are never used as a rate answer.

## How conflicts are resolved

`conflicts()` compares facts that share the same identity (product, term, balance or amount tier, model-year band and metric) across snapshots and across mirrored tables on different pages. Presentation differences such as "$1,000" vs "$1,000.00" are normalized first, so they are not reported. Distinct tiers and APR vs APY are separate facts, not conflicts. The winner is chosen by these rules, in order:

1. Page authority: the central rates pages (`/rates`, `/business-rates`) beat product pages, which beat calculators, blog posts, newsroom articles, PDFs and legacy `info.dupaco.com` pages.
2. Recency: the observation from the newest snapshot that still contains the fact wins over older snapshots.
3. A fact that has disappeared from the newest snapshot cannot win a current conflict.
4. For counts stated in dated articles (for example the number of branches), the most recently published statement wins over older boilerplate.

Each `Conflict` lists the competing values, a `Source` for each value and snapshot, the resolution and a short reason. The current corpus produces 62 conflict records (certificate specials, auto loan bands, mortgage rates, checking and savings tiers, branch count). `Answer.conflict_note` carries a short note on which rule picked the value (authoritative rate table, selected snapshot, or last-observed evidence). It does not yet name the specific rejected values; linking each answer to its conflict record is a possible next step.

## Citation format

Every answer and conflict cites `Source(url=..., snapshot_id=..., quote=...)`:

- `url`: the page the value came from, as it appears in the crawl manifest.
- `snapshot_id`: the crawl the evidence was read from, for example `05_2026-09-28_latest`.
- `quote`: the supporting table row or passage, trimmed to 500 characters.

Rate answers may add a second source when the matched table links to a product details page.

## Abstention

If no table row matches the requested product and term, or no passage is relevant enough, or a named entity (such as a branch) does not exist in the selected crawl, the system returns `confident=False` with the text "I don't know; this information isn't listed. Please contact Dupaco." The refusal deliberately contains no digits (not even a phone number), because the scorer treats any new number in a refusal as a guess.

## Limitations

- This is lexical retrieval plus structured extraction, with limited language understanding. Unusual phrasing, irregular tables, mixed product mentions and ambiguous questions can still miss.
- Synonyms are a small hand-written vocabulary map, so a new word for a product may not be recognized.
- Article publication dates are parsed heuristically, so "last year" style questions can pick the wrong report year (one public miss).
- Last-observed fee evidence from a removed page does not prove the fee is still current.
- No conflict gold list is supplied for the full site, so conflict precision is not measured here.
- An optional LLM rerank path is not included. If one is added later it should stay behind an environment variable (see `.env.example`) and fall back to this offline path.

## Evaluation results

Measured offline with the unmodified harness:

| Evaluation | Questions | QA score | Final score | Stale trap hits | Consistency | p95 answer time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Public | 40 | 0.9070 | 0.9070 | 0 | 1.0000 | 0.53 s |
| Extra | 35 | 1.0000 | 1.0000 | 0 | 1.0000 | 0.03 s |
| Harness self-test | 5 | 1.0000 | 1.0000 | 0 | 1.0000 | below 0.01 s |

All five unit tests pass. They cover range parsing, historical selection, authority precedence, one-value output and rejection of payment-example rates. Full-site ingest takes about nine seconds. The self-test conflict F1 and resolution accuracy are both 1.0000 on one gold conflict. Public and extra scores have no conflict pillar because no full-site gold is supplied. These results do not establish hidden-set performance.

Known public misses include an empty required-answer list that receives zero correctness, prose retrieval misses and a volunteer question whose expected count is from an older reporting year than the retrieved article. The implementation retains newer snapshot evidence rather than inserting the practice answer.

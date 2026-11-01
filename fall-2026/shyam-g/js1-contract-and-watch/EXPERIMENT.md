# Prompt experiment (Chapter 2)

**Status: PARTIAL (2026-10-31, deadline).** The baseline prompt ran on all 20 postings, and all 20 outputs were valid. **Hand labels were not completed, so no pass rates exist, and no revision was chosen or run.** Choosing the revision would have needed the dev-set misses against hand labels; making a change without them would not have been a real experiment.

## Labeling rule (write this BEFORE labeling)
**Not written before the deadline.**

## Sets
`labels/hand_labels.csv`: 20 real Formlabs postings from the 2026-10-31 live response. `study.py pick`
chose them: all 6 postings whose title matched a target title, plus 14 random others, with seed 7375.
They were then split into 10 `dev` and 10 `heldout`. Do not open the held-out results until the
revision is frozen.

## Prompts
- Baseline: `prompts/baseline.txt` (states the CONTRACT rule; JSON-only output contract)
- Revision: **not written** (it needs the dev misses against hand labels).

## Commands
```
python study.py experiment --raw state/raw/2026-10-31T223703-formlabs-live.json --prompt prompts/baseline.txt --split dev
python study.py experiment --raw state/raw/2026-10-31T223703-formlabs-live.json --prompt prompts/revision.txt --split dev
# only after the revision is frozen:
python study.py experiment --raw state/raw/2026-10-31T223703-formlabs-live.json --prompt prompts/baseline.txt --split heldout
python study.py experiment --raw state/raw/2026-10-31T223703-formlabs-live.json --prompt prompts/revision.txt --split heldout
```

## Results (pass = Claude verdict equals hand label; an invalid output counts as a fail)
| | dev (10) | held-out (10) |
|---|---|---|
| baseline | not scored (no labels) | not scored (no labels) |
| revision | not run | not run |
| rule (for reference) | not scored | not scored |

What was measured instead: **agreement of the baseline prompt with the rule**: dev 10/10, held-out
10/10 (`results/experiment-baseline-*.json`). This is not a pass rate. The prompt states the rule, so
high agreement mostly shows that Claude followed the stated rule and produced valid output, not that
either one is right. Only 1 of the 20 postings is rule-relevant (8311099), so this set barely tests the
`relevant` side at all.

Note on order: the held-out baseline was run at the same time as dev, before any labeling, and its
results were not used to choose anything. No revision exists, so nothing was tuned on held-out.

## How little ten cases show
A change from 7/10 to 8/10 is one posting. On a ten-case set that is within what re-sampling the same
prompt can produce on its own: in `SAMPLING.md` one posting flipped verdict in 1 of 4 identical runs. Even with labels, 10 dev and 10 held-out cases, of which only 1 is rule-relevant, could not separate two prompts unless they differed by several postings.

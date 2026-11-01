# Prompt experiment (Chapter 2)

**Status: PARTIAL (2026-10-31, deadline).** The baseline prompt ran on all 20 postings, and all 20 outputs were valid. Hand labels were added at 23:49 and scored at 23:50. The revision was run 23:53 (dev), frozen, then run 23:54 (held-out).

## Labeling rule (write this BEFORE labeling)
Relevant if it's a supply chain, procurement, planning or ops analyst role, entry to mid level (5 years or less), in Boston or remote.

Written: 2026-10-31 23:43 (file timestamp), before labeling. (Wording adapted from Claude's example; the choice is mine.)

## Sets
`labels/hand_labels.csv`: 20 real Formlabs postings from the 2026-10-31 live response. `study.py pick`
chose them: all 6 postings whose title matched a target title, plus 14 random others, with seed 7375.
They were then split into 10 `dev` and 10 `heldout`. Do not open the held-out results until the
revision is frozen.

## Prompts
- Baseline: `prompts/baseline.txt` (states the CONTRACT rule; JSON-only output contract)
- Revision: `prompts/revision.txt`. **One change:** the sentence restating the contract rule is replaced by
  my labeling rule; everything else is byte-identical apart from Windows line endings. Chosen because
  every baseline miss was a posting I labeled `relevant` that the contract rule rejected. Claude
  proposed the change in the report; I asked for it to be run.

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
| baseline | **6/10** | **7/10** |
| revision | **5/10** | **7/10** |
| rule (for reference) | 6/10 | 7/10 |

Every miss is the same kind: I labeled a posting `relevant` and both Claude and the contract rule said
`not_relevant`. The dev misses are 7684675, 8327414, 8241540 and 8167038; the held-out misses are
8281689, 8335610 and 8333766. Claude never disagreed with the rule. The baseline prompt restates the
rule, so it inherits the rule's misses. **The revision did not help:** dev went from 6/10 to 5/10, and held-out stayed at 7/10. On dev, Claude still
rejected the same 4 postings, and it flipped 8161780 (Global Sourcing Intern) to `relevant`, a
posting I had labeled `not_relevant` with the note "internship, but sourcing = procurement". So
the one changed verdict moved the wrong way. One posting is within the noise seen in `SAMPLING.md`
(that same posting flipped 1 of 4 times under the baseline), so I can't say the revision is worse.
I can only say it is not shown to be better. Several of my labels (an engineering technician, a materials scientist, a
support role in Milwaukee, an ops leader in Ohio) do not obviously follow my own written rule either,
and that is unresolved.

Also measured: **agreement of the baseline prompt with the rule**: dev 10/10, held-out
10/10 (`results/experiment-baseline-*.json`). This is not a pass rate. The prompt states the rule, so
high agreement mostly shows that Claude followed the stated rule and produced valid output, not that
either one is right. Only 1 of the 20 postings is rule-relevant (8311099), so this set barely tests the
`relevant` side at all.

Note on order: the held-out baseline was run at the same time as dev, before any labeling, and its
results were not used to choose anything. No revision exists, so nothing was tuned on held-out.

## How little ten cases show
A change from 7/10 to 8/10 is one posting. On a ten-case set that is within what re-sampling the same
prompt can produce on its own: in `SAMPLING.md` one posting flipped verdict in 1 of 4 identical runs. Even with labels, 10 dev and 10 held-out cases, of which only 1 is rule-relevant, could not separate two prompts unless they differed by several postings.

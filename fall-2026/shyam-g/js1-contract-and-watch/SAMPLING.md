# Sampling report (Chapter 1)

**Status: Claude runs collected 2026-10-31 (22:48–23:07). NOT SCORED against hand labels: labels were
not completed before the deadline.** This report covers repeatability only. Correctness is not
measured.

## Setup
- 5 postings from the live Formlabs response, picked before any labels or Claude results existed to
  cover a clear fit, borderline cases and clear misses.
- Each was asked 4 times, every time in a fresh `claude -p` conversation with no tools, under
  `prompts/baseline.txt` and the CLI's default model (not pinned).
- Command:
  `python study.py sample --raw state/raw/2026-10-31T223703-formlabs-live.json --ids 8311099,8161780,8335610,8281689,7684675 --n 4`
- Raw outputs, including every reply: `results/sampling.json`. All 20 outputs passed the validator.

## Results
| posting_id | title | Claude verdicts (4 fresh runs) | rule (record) | Claude = rule | my hand label |
|---|---|---|---|---|---|
| 8311099 | Strategy & Operations Analyst | relevant ×4 | relevant | 4/4 | _not labeled_ |
| 8161780 | Global Sourcing Intern (Winter/Spring 2027) | not_relevant ×3, **relevant ×1** | not_relevant | 3/4 | _not labeled_ |
| 8335610 | Mechanical Project Manager | not_relevant ×4 | not_relevant | 4/4 | _not labeled_ |
| 8281689 | Product Manager, Software | not_relevant ×4 | not_relevant | 4/4 | _not labeled_ |
| 7684675 | Manufacturing Ops Leader | not_relevant ×4 | not_relevant | 4/4 | _not labeled_ |

## What this can and cannot show
- **Can:** the same prompt on the same posting doesn't always return the same verdict. 8161780 flipped
  once in 4 runs. A single Claude call on that posting is not a stable answer, which is why the agent
  keeps the rule as the record and labels Claude's answer as a judgment.
- **Can:** 4 of the 5 postings repeated 4/4. Repeating proves **repeatability, not correctness**.
- **Cannot:** whether any of these verdicts is *right*. That needs the hand-label column, which is
  empty. Agreement with the rule (19/20) is not correctness either, because the prompt restates the
  rule, so agreement is partly built in.
- **Cannot:** anything about the size of the variation in general. With 4 samples, one flip is
  consistent with a true flip rate anywhere from a few percent to over half.
- The posting that flipped is the borderline one: "sourcing" is close to `procurement`, but it's an
  internship. Variation showing up where the rule is least clear is what you'd expect. On five postings
  that is an observation, not a finding.

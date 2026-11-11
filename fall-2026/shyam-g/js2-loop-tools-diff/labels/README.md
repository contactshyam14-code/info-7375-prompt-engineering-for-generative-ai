# Hand labels: fill these in BEFORE any run you report and before any Claude call

`check.py` refuses to run while `hand_labels.csv` has no rows. A board with no label is reported
UNCHECKED, which is not a pass.

For each board in `config/boards.json`:

1. Open the public board page in a browser. Don't use the agent.
   - Greenhouse: `https://job-boards.greenhouse.io/<board>`
   - Lever: `https://jobs.lever.co/<board>`
2. Count the postings yourself, or read the total the page shows. Write down how you counted.
3. Write the time (ET) you counted. Postings change, so set `tolerance` to the drift you'll accept
   between your count and a run a few minutes later, and say why in `notes`.
4. For the deliberate-failure board, put `N/A` in `hand_count`.

Columns: `board,ats,checked_at_et,hand_count,tolerance,how_counted,notes`

Commit this file on its own, before the run you submit, so the commit history shows the order.

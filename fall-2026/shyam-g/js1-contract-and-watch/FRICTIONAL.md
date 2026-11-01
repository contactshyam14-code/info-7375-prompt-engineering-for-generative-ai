# FRICTIONAL

Things that went wrong or caused friction, in order, with what was done about each.

1. **2026-10-30: contract left two blanks.** The board token and the HTML-stripping decision were
   still placeholders when implementation started. The code had to choose (strip HTML), and the
   contract was amended afterwards (section 8, 2026-10-31). The rule in section 4 is unchanged; only
   the part left undecided was filled in.
2. **2026-10-31: 3 of 7 guessed board tokens returned 404** (`wayfair`, `draftkings`, `anduril`). Their
   careers pages are not on Greenhouse under those names, so a token must be verified, not assumed.
3. **Two of the boards that did return JSON had zero rule-relevant postings** (`flyzipline`, `toast`).
   A board can be technically valid and still useless for this persona.
4. **2026-10-31: `--state` crashed the seeded run** (`ValueError: ... is not in the subpath of ...`).
   A relative path was compared with an absolute root. The crash came *after* `seen_ids.json` was
   written, so rerunning would have treated run 2 as a non-baseline run with the wrong history. The
   partial `state-seeded/` folder was deleted and both runs redone. The root fix: `agent.py` now writes
   the report first and marks ids seen last.
5. **PowerShell `Set-Content -Encoding utf8` added a byte-order mark** to `agent.py`. It was removed
   with `sed`. Python tolerates the mark, but it is an invisible diff.
6. **The Read tool isn't limited to one file.** Way 2 of the action-surface comparison was meant to be
   "read this one file", but the tool can open any file the user can. That is why the agent sends
   Claude pasted text and does not give it a file.
7. **A misnamed zip.** `JayaramanGopalakrishnan_ShyamSundar_INFO7375_JS1.zip` in the parent folder
   holds the earlier Mode Build submission, not this assignment. It must not be uploaded for JS1.
8. **2026-10-31 ~23:15: two label sets in play.** `Downloads/labels_to_fill.txt` (another session,
   different posting ids, still unfilled) was confused with this project's `labels/hand_labels.csv`.
   Neither was labeled before the deadline. The Claude runs were collected anyway, saved without being
   printed, so they could be scored later without having anchored the labels.
9. **Sampling surprise:** posting 8161780 (Global Sourcing Intern) got `relevant` in 1 of 4 identical
   fresh runs. It is the borderline posting: sourcing is near procurement, but it's an internship.

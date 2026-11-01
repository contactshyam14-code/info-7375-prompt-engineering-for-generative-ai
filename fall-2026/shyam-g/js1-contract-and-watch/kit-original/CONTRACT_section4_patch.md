## 4. The rule (rule_verdict)  -- REPLACE your section 4 with this

Matching: case-insensitive, WHOLE-WORD/PHRASE. A term matches only if the
characters before and after it are not letters or digits (regex
`(?<!\w)term(?!\w)`, term escaped). So "sql" does not match "sqlite",
"excel" does not match "excellent", and "supplier" would not match
"suppliers". Input text is the posting's plain text (state in README
whether HTML tags in `content` are stripped first; test it).

A posting is `relevant` only if ALL hold:
1. TITLE: `title` matches at least one `resume.target_titles` entry.
2. LOCATION: `location.name` matches an entry in `resume.locations`, or
   matches "remote".
3. SKILLS: `content` matches at least 2 DISTINCT `resume.skills` entries.
4. EXCLUSIONS: neither `title` nor `content` matches any
   `resume.exclude_keywords` entry.
Otherwise `not_relevant`.

Decision: "ma" is NOT a location term (it matched "Germany"). Consequence:
"Worcester, MA" is `not_relevant` unless "massachusetts" appears. I accept
this limitation; fixture 1009 pins it.

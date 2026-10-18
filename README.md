# Enki Sumerian

**Measuring the oldest writing as pure geometry, to see whether it is organised like a coordinate system.**

This is an open exploration, not a claim. No translations are used, and nothing here says what any sign means. Every result is a measurement, a test against chance, or an open question. Where something does not fit, it is listed.

Project page: https://enkisystems.com/sumerian · By Brad Harris, Enki Systems

---

## The question

Enki Systems gives every piece of information a permanent base-60 address, and its collapse engine folds many signals into one governed node. The people who wrote cuneiform counted in 60s. So we asked a narrow question:

> If you ignore what the signs are said to mean and only measure their shapes, are they built and used like addresses?

## What was measured

- **541 signs**, every wedge confirmed by hand: 5,712 wedges in 3,717 groups. Together these signs make up 94.1% of the writing on the tablets below.
- **79,660 Ur III tablets** (about 2100–2000 BCE), 938,258 undamaged lines, for the text tests.

Each wedge is four numbers: where its head is, which way it points (compass angle, 0° = up), how long its tail runs, and how big its head is (stage 1–4). Distances are in *bits*: one bit is the width of a standard wedge head.

## What we have seen so far

| Observation | Status |
|---|---|
| **Signs are built like counters.** 252 of 541 signs are one small unit repeated a set number of times ("ladders"): down wedges 1–9, across wedges 1–9, hooks 1–10, a 4-wedge diamond 2–9. | Seen |
| **On the tablets, hooks stop at 5 before units.** A hook sign directly followed by down wedges has 1–5 hooks 58,383 times and 6–9 hooks 11 times; the 6–9 hook signs are used 1,422 times elsewhere. Down wedges after hooks run 1–9. Ten units and six steps of tens make a 60 cycle, found without assuming any base. | Seen |
| **Lines repeat like stored records.** 78.9% of complete lines recur symbol for symbol on other tablets; one 15-symbol, five-field layout appears 4,395 times on 584 tablets. | Seen |
| **Looking alike does not mean being used alike.** Shape difference says nothing about text context (rank correlation −0.001 over 64,261 pairs), but signs on the same ladder share context 2.6× more than unrelated signs. Most ladders are counting signs, so this may only mean numbers behave like numbers. | Open |

### What counts against the idea

- Symbol use is very uneven: 970 symbols, the top 100 make up 83.2% of the text.
- 7 pairs of signs are identical by our measure; 84 signs are one wedge from another. A misread wedge would change the value.
- Slanted wedges cluster at 45° and 135°, not at multiples of 30°: the circle is split in eighths, not sixths.
- Predicting missing signs mostly failed: 4 of 64 predicted gaps were filled, all weakly.

### What we do not know

- **Font or clay?** Signs were measured from a modern font's standard drawings, not yet from real tablets.
- **Editor influence.** Which sign stands where comes from modern editions.
- **The place above the hooks** is not pinned; the sums test cannot tell 60 from other values.
- **The 10-hook sign** does not fit the 1–5 ladder.
- **Libraries outside numbers** have not been tested yet.
- **Curved marks** in three signs are held out until checked on clay.

## How it was validated

1. **Sources pinned and hashed.** Every downloaded file has a SHA-256 fingerprint; the files these results rest on were re-verified on 18 October 2026.
2. **Only signs on the clay.** Signs editors marked as restored or supplied are dropped; damaged lines are left out of the line tests.
3. **Every wedge confirmed by eye.** A detector proposes wedges; a person corrects each sign on a grid.
4. **Every pattern tested against chance.** Results are compared with the same data shuffled.
5. **Rerunnable.** Rebuilding the scripts from scratch reproduced every number exactly.

## Repository layout

```
data/
  validated_wedges.json   hand-confirmed wedge measurements (the base dataset)
  sign_meta.json          per sign: grid size, crop offset, rank and share of the text
  wedges.json             every sign with its wedges and groups (built by scripts/group_wedges.py)
  signclass.json          each sign as down-only (V), hook-only (K), across-only (H) or mixed, with its count
  context_vectors.json    for each sign, the signs directly left and right of it in the text
  detector_shapes.json    unvalidated detector shapes for all 1,234 font signs (positions and angles only)
  summary.json            the numbers the project page draws from
scripts/                  every test; see "Reproduce" below
outputs/                  the printed results of each test
```

## Reproduce

Requires Python 3.10+, standard library only.

The sign-set tests run straight from `data/`:

```
python scripts/group_wedges.py      # validated_wedges.json + sign_meta.json -> wedges.json
python scripts/b60.py               # base-60 tests on the sign set
python scripts/b60b.py              # down-wedge / hook count table
python scripts/b4_signs.py          # ladders and nearest-sign distances
python scripts/b5_library.py        # missing signs, building rules, context vs shape
python scripts/site_summary.py data/summary.json
```

The tablet tests need the public corpus and sign list. Download them into `data/raw/` (not included here):

1. The Ur III corpus JSON: https://oracc.museum.upenn.edu/json/epsd2-admin-ur3.zip
2. The Oracc Global Sign List: `git clone https://github.com/oracc/osl data/raw/osl`

Then:

```
python scripts/osl_parse.py data/raw/osl/00lib/osl.asl data/raw            # -> data/raw/signs.tsv
OSL_ASL=data/raw/osl/00lib/osl.asl python scripts/ingest.py data/raw/epsd2-admin-ur3.zip data/raw/ur3 --resolve
python scripts/b3_base.py      # hooks and units on the tablets, and the sums test
python scripts/b4_text.py      # record-like structure of lines
python scripts/b4_more.py
python scripts/b5_context.py   # rebuilds data/context_vectors.json
```

`ingest.py` resolves each written sign to a sign ID using the sign list. It reads the edition's transliteration in memory to do that, but writes out only sign IDs and positions: no readings, values or meanings.

## Sources

| Source | Used for | Licence |
|---|---|---|
| [ePSD2/CDLI Ur III Corpus](https://oracc.museum.upenn.edu/epsd2/admin/ur3/), Oracc JSON build of 7 Dec 2022 (Oracc with the Cuneiform Digital Library Initiative) | Which sign stands where in each line | CC0, as stated in the download's metadata |
| [Oracc Global Sign List](https://github.com/oracc/osl), commit 6231cc4 | Linking sign IDs to Unicode code points | No licence stated; used as a lookup, not redistributed |
| CuneiformClassic font, © 2011–2012 Steve Tinney and Michael Everson | The standard drawing of each sign, measured to find its wedges | All rights reserved. **Not included.** No image of it appears in this repository; only our measurements |
| [Unicode Cuneiform charts](https://www.unicode.org/charts/PDF/U12000.pdf) | Code points (e.g. U+12423) as neutral sign labels | Unicode terms of use |
| [HeiCuBeDa Hilprecht 3D scans](https://doi.org/10.11588/DATA/IE8CCN), Heidelberg University | Downloaded for the next step (clay check); not used in these results | CC BY-SA 4.0 |

## Licence

Code (`scripts/`): MIT. Data, outputs and text (`data/`, `outputs/`, this README): CC BY 4.0. Third-party sources keep their own licences, above.

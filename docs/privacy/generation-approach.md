---
document_version: 1.1.0
status: Submitted for privacy review - pending sign-off
---

# Synthetic persona generation approach: privacy review packet

This packet describes how the Fuzzy Chain Saw synthetic persona engine
generates its sample data, what each value is drawn from, the safeguards
around generation, and how that is monitored and verified. It is written for
the privacy officer evaluating PHI-free prototyping: approving this approach
is the decision that lets analytics, application development and testing
teams use synthetic member data instead of requesting de-identified
production extracts.

Every generated persona carries exactly six attributes: first name, last
name, age, gender, geography and income. Nothing else is produced, so
nothing else can leak.

## Generation method

A dataset is produced by `PersonaGenerator.generate_dataset(config, count,
seed)` in the `persona-engine` package. The seed is required: the generator
builds a dedicated seeded `random.Random(seed)` instance and draws every
attribute of every persona from that one source, so the same seed and the
same generation configuration rebuild the exact dataset, byte for byte,
within a Python runtime.

Attributes are consumed in a fixed order — `first_name`, `last_name`, `age`,
`gender`, `geography`, `income` — so the seed's value stream maps
deterministically onto named fields. Names come from `rng.choice` over
committed pools; `age` and `income` come from `rng.randint` over validated
ranges; `gender` and `geography` come from `rng.choice` over the configured
category labels. Reproducibility is a property of the seed, the fixed
consumption order and the immutable configuration together: adding or
reordering an attribute changes every dataset and is announced with a
`manifest_version` bump.

## Attribute sources

Every attribute value is drawn from one of the following named sources. No
attribute has any other source.

| Attribute | Source |
| --- | --- |
| name (first/last) | Fixed synthetic name pools committed in `src/persona_engine/name_pools.py` |
| age | An integer drawn by `rng.randint` from the configured `age_range` |
| income | An integer drawn by `rng.randint` from the configured `income_range` |
| gender | `rng.choice` over the configured gender label list |
| geography | `rng.choice` over the configured geography label list |

Details:

- **name** — the first and last name values come only from two fixed lists
  ("pools") committed with the engine: 54 first names and 48 last names.
  The pools are synthetic by construction: they are deliberately chosen
  common names spanning diverse cultural origins, and no value identifies
  any specific person. The pool file carries the repository's
  `pacca: allow-phi` recorded-reason marker explaining exactly this.
  Nothing outside these lists can ever appear in a generated name, because
  the generator is the only producer and it draws only from the pools.
- **age and income** — integers drawn inside the configured positive ranges
  (`default`: age 18–85, income 20,000–150,000). A range is validated at
  configuration time: it must be ascending and its lower bound must be
  positive. There is no path by which a generated age or income is derived
  from anything but the seeded generator and the configured bounds.
- **gender and geography** — plain label strings chosen from the configured
  category lists (`default` genders: Female, Male, Non-Binary; `default`
  geographies: Region North, Region South, Region East, Region West).
  These are intentionally non-identifying labels; the default geographies
  do not resolve below region level, consistent with Safe Harbor's
  coarsest-geography expectation. The lists themselves, however, are caller
  content: whoever authors the generation configuration chooses the label
  strings, and the engine checks only that each list is non-empty and free
  of duplicates — it does not constrain what the labels say. See the
  never-contains criteria below for what that configuration channel can
  and cannot carry.

## Safeguards

The generation approach is defended by the following controls, each
implemented in code rather than promised in prose:

- **Immutable configuration recorded as provenance.** The generation
  configuration (ranges and label lists) is a frozen dataclass: once built
  it cannot change. It is serialised verbatim into every dataset manifest,
  so the manifest is self-recording: the exact configuration that produced
  the rows travels with them and any later reading of the dataset knows it
  was the producer. A mutable configuration could silently stop being the
  one that produced the data; this one cannot.
- **Validated ranges and categories.** An `age_range` or `income_range`
  that is not an ascending, positively-bounded pair, or a gender/geography
  list that is empty or contains duplicates, is rejected with an exception
  at construction. Invalid configurations never reach generation.
- **API bounds refuse loudly.** The save endpoint bounds a `seed` to a
  whole number 0 to 2^31-1, a `count` to 0 through 10,000, a name to 255
  characters, and a team path to 64 characters. A request beyond any bound
  is refused with an explained `422` before anything is written; a
  duplicate configuration name for the same team is refused with `409`.
  A refused save never resembles a partially successful one.
- **CI gates.** Every pull request runs the backend and engine suites
  under an 80% coverage floor, pyflakes, frontend `tsc`, the frontend
  vitest suite — reproducibility, refusal and export behaviour included —
  before merge. A regression in the safeguards above fails CI.
- **No prompts, no model, no credentials.** Generation involves no machine
  learning model at all, so no content is ever sent to an external model
  provider: PHI does not travel in prompts because there are no prompts.
  Credentials resolve from the service's own environment and never appear
  in payloads or logs.

## Monitoring controls

Confidence in this approach is grounded in verification that runs today,
not in assurance claimed for a system under construction:

- **Manifest provenance.** Every dataset is stored as a canonical JSON
  manifest embedding the `seed`, the record `count`, the `manifest_version`
  of the writing engine, the `python_version` of the run, and the full
  configuration. Any stored dataset therefore carries the evidence needed
  to interrogate exactly how it was produced.
- **Replay verification.** Reproducing a saved dataset regenerates it from
  its recorded seed and configuration and then verifies the regenerated
  rows against the rows the manifest itself recorded. Any divergence — a
  different Python runtime, a stale name pool, a tampered artifact — is an
  exception naming both runtimes and the first divergent row, never a
  silently different dataset. This replay check is itself covered by
  regression tests in the engine suite.
- **Manifest-version refusal.** A manifest whose `manifest_version` the
  current engine does not support is refused outright: changing the
  attribute consumption order or the persona schema is a deliberate,
  announced event, and an old manifest between two such versions cannot
  be replayed into something quietly different from what it says.
- **CI enforcement.** The GitHub Actions pipeline runs the backend and
  engine suites, the reproducibility and refusal tests, and enforces the
  80% coverage floor on every pull request and merge to main, with a
  post-deploy smoke check against staging.
- **Production monitoring is deferred — future work, not an existing
  control.** There is today no production auditing, alerting or runtime
  anomaly monitoring over generated datasets; what exists is the
  provenance, replay verification and CI described above, which run at
  build and reproduction time, not continuously against a live
  deployment. Residual risk is bounded as follows: name and numeric
  values are structurally safe (their sources are fully enumerated and
  engine-controlled), verified by the replay check; the content of the
  caller-configured gender and geography labels, by contrast, is not
  gated by anything described in this section — it is disclosed and
  weighed in the never-contains criteria below. Establishing production
  monitoring is explicitly deferred and would be a new,
  separately-reviewed work item.

## What generated output must never contain

The generated output of this system is a persona record with exactly the
following permitted fields, and nothing beyond them:

```
first_name
last_name
age
gender
geography
income
```

Never-contains criteria. Each statement is worded at the strength the
enforcing control actually supports: structural guarantees are scoped to
the sources the engine fully controls, and caller-fed channels are
disclosed as exactly that.

1. **Name values come only from synthetic pools.** Generated first and
   last names are always drawn from the two committed synthetic name
   pools and from nothing else. No name value is ever sourced from a
   production member extract, a de-identified extract, customer records,
   or any other dataset of real individuals — the generator is the only
   producer of names and it draws only from the pools.
2. **Numeric values come only from the seeded generator over validated
   bounds.** A generated `age` or `income` is an integer drawn by
   `rng.randint` between the configured, positively-validated bounds.
   There is no path by which a generated number is derived from anything
   but the seeded generator and those bounds.
3. **Generated values never reference a real member identity.** No
   generated record is, or is derived from, an actual customer. (Names
   can coincidentally match a real person's name, exactly as a name
   drawn from a phone book could; the guarantee is that the value came
   from a synthetic pool, not that collisions are impossible.)
4. **No field beyond the six permitted fields is ever produced**: no
   dates of birth (only an age), no contact details of any kind, no
   account, plan or record numbers. The persona record has no free-text
   field for a generator value to land in.
5. **Gender and geography labels are caller content and are not
   content-checked by the engine — this is the one channel through which
   real member data could enter generated output.** A generated gender
   or geography value is a label string from the configuration, carried
   verbatim into every row and every CSV/JSON export. The engine
   validates only that each list is non-empty and free of duplicates; it
   does not constrain what the labels say. A configuration author who
   pastes identifying text — a real city, a postal code, a member name,
   or any value copied from production data — into `genders` or
   `geographies` puts that text into the generated dataset. The default
   configuration's label lists carry no such content. Keeping them
   identifying-free is a governance obligation on configuration authors,
   not an engine-enforced guarantee, and reviewers should weigh it
   exactly as they weigh any allowance the engine itself does not
   check.
6. **Geography granularity is a caller decision, not an engine
   property.** With the default configuration, generated geographies
   resolve no finer than region level — no state, city, street or
   postal code is present in the default lists. Nothing in the engine
   prevents a caller from configuring finer or more specific labels;
   the granularity a dataset has is exactly the granularity its
   authoring configuration chose, and the manifest records that
   configuration verbatim so it can be audited per dataset.

## Revision history

| Version | Date | Change |
| --- | --- | --- |
| 1.0.0 | 2026-11-16 | Initial packet submitted for privacy review. |
| 1.0.1 | 2026-11-16 | Corrected the committed name-pool counts to 54 first names and 48 last names. |
| 1.1.0 | 2026-11-16 | Never-contains criteria rewritten per privacy-review finding: structural guarantees scoped to name pools and validated numeric ranges; the caller-configured gender/geography label channel disclosed as the one path real member data could take into generated output; the 'structurally empty ingest side' and region-fineness absolutes replaced with accurate descriptions; the monitoring section's residual-risk statement corrected to match. |

## Approval record

The table is completed at sign-off. The rationale column is the recorded
reason a later reader weighs, mirroring the repository's
`pacca: allow-phi` recorded-reason precedent.

| Approver | Role | Decision | Rationale | Date |
| --- | --- | --- | --- | --- |
| pending sign-off | Privacy officer | Pending review | Recorded at sign-off | — |

A future revision of this document — for example a seventh Persona field,
which the documentation tests refuse silently against the code — is
regenerated, bumped in `document_version`, appended as a revision-history
row and returned for re-review with a fresh approval row.

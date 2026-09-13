# Internal audit tooling -- provenance and release verification

> **These scripts are NOT part of normal reproduction.**
> They are the authors' internal release gates and provenance tools. They depend on
> restricted artefacts, internal checksum files and historical Git tags that this
> repository does not ship, so they **cannot** run in a clean clone. They are retained
> because they document how the release was checked, not as instructions to a user.

## What lives here, and what does not

The scripts themselves are **kept in their original locations**
(`src/reporting/`, `src/validation/`) rather than moved, so that a reader of the internal
working tree finds them where they were and so that the published file list stays stable.
Their module docstrings say what they are, `README.md` labels them, and this file explains
why they are not runnable here.

| script | why it cannot run in a clean clone |
|---|---|
| `src/validation/publication_lock.py` | reads `data/*.csv`, `outputs/tables/*.xlsx` and `PUBLICATION_RELEASE_MANIFEST.json`; also opens a **read-only eICU database connection** to recover the patient count, which requires authorised access |
| `src/reporting/final_release_check.py` | reads the restricted analysis dataset and predictions, the internal `PUBLICATION_ARTIFACT_CHECKSUMS.txt`, and a historical analytical Git tag |
| `src/reporting/release_verification.py` | reads `PUBLICATION_ARTIFACT_CHECKSUMS.txt`, an internal artefact-checksum file that is not shipped |
| `src/manuscript_qa/*.py` | audit the manuscript files, which are not part of a code release |

## What the public reader should use instead

```bash
python verify_public_release.py       # 20 checks, no data, no database, no Git
python pipeline_path_audit.py         # pipeline path and stage hand-off audit
```

`verify_public_release.py` covers everything that can be checked from the repository
contents alone: file checksums, required and forbidden paths, compilation, the absence of
restricted data, documentation references, the release manifest, the pipeline structure,
and the citation metadata.

## The internal scripts, adapted for v1.1.0

They were **not** left describing the removed hierarchical model. Where they referenced it,
they were adapted to the final state:

* `src/reporting/final_release_check.py` previously **required** a `hierarchical_calibration`
  sheet carrying alpha/beta/tau, and a `random_intercepts` sheet, to be present in Table 4.
  Those checks are now **inverted**: the gate fails if either sheet ever reappears. The
  check is therefore stronger than it was, not weaker.
* `src/validation/publication_lock.py` read the removed `hierarchical_calibration` sheet and
  wrote an alpha/beta/tau sentence into the lock document. It now reads the retained
  `primary_N20` sheet and states that no hierarchical model is reported, so no
  calibration-heterogeneity conclusion is available.
* `src/reporting/tables_and_figures.py` described Figure 5 as "hospital observed vs
  predicted + hierarchical calibration". Figure 5 panel B has been the per-hospital
  observed-to-expected ratio since the model was removed.

## Version strings -- a deliberate mismatch

| what | version |
|---|---|
| the frozen primary-analysis configuration (`config/final_analysis_config.py`) | **`FINAL_v1.0.0`** |
| this publication / code release | **`v1.1.0`** |

The primary model and its configuration were **not changed**, so the configuration version
string was deliberately left alone: editing it would change the frozen configuration hash
and invalidate every output stamped with it. v1.1.0's only analytical change is a
**removal** — the unreliable hierarchical calibration analysis. See `CHANGELOG.md`.

## Historical Git tags

The internal gates reference tags such as `PROJECT1_FINAL_MANUSCRIPT_v1.0.0`. Those tags
exist in the authors' private Git history. This release archive ships no `.git` directory,
so the tag checks cannot resolve here and are reported as failures by design. No public
check depends on any tag.

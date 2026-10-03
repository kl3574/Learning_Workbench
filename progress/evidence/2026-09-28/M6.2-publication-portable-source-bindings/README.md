# Portable bindings for three original source snapshots

This supplement proves source-byte portability. It neither reruns product tests nor changes the original tested commit identities, original evidence packages, failures, or conclusions.

The original fixed commits can be unavailable in a clone containing only the public main history. The verifier therefore reads just two public-history commits:

- Default source: `ce42bf8cae734e49166a1472184fd9c3fa875bc7`.
- Source for the explicit override paths: `62118f823b03da6bc4c34ba335f736e20ea31df6`.

Every engineering Git path is included, except the `progress/` subtree. For each target, the default tree plus its listed override paths must equal the complete original tree in path membership, Git mode, blob SHA-1, byte length, and SHA-256. This does not require whole Git tree IDs or commit IDs to match: the public commit contains other work and progress records.

| Original fixed source | Override paths | Complete engineering files | Original final input manifests checked |
| --- | ---: | ---: | --- |
| Service `dec1d937523f4596da4c39bcc27750d9132c752c` | 16 service paths | 1021 | Stages 16–19, before and after: 8 manifests, each 1021 inputs |
| HTTP `833f0a84168638ba5ce421c70cd2f20a71e45e48` | 16 service + 8 HTTP paths | 1023 | `http-final`, `review-http`, `spec`, `ruff`, `web-types-final`, before and after: 10 manifests, each 1023 inputs |
| Observer `8b6629205a72593ab835e2c61a20b6e1eac7061e` | 9 observer paths | 1015 | Stages 06–10, before and after: 10 manifests, each the original 827 explicit inputs |

The 1015-file observer comparison is new source-only evidence. It does not expand any original execution to 1015 inputs. Observer stage 05 had only 825 of its 827 inputs equal to the final candidate; this supplement does not upgrade that run. Stage 08 remains a failed native-types run, despite its 827 matching source inputs. The original `GIT_SOURCE_BINDINGS.json` is retained byte for byte with all original stage outcomes.

For HTTP, the 100 contract tests and 204-source mypy result remain bound to the earlier `966b6c6cf616df816d6c114675c920621ba84573` gate. The final `833f0a8` gate comprises the original 14 publication HTTP tests, 30 Review HTTP tests, Ruff, spec, and strict TypeScript. The fixture-only assertion correction between those commits is not a rerun of the earlier gate. Original absent-route RED, fixture failures, and Node toolchain failure remain in the original public package. All service failures and limitations likewise remain there.

Run from this package with Python 3.10 or newer and Git:

```sh
python verify.py --git-repo /path/to/public-main-clone
```

A normal or bare repository is accepted. It must contain the full relevant main history, including both pinned public commits. The verifier performs local reads only; it fetches nothing, checks out nothing, imports no application code, and never asks Git for one of the three original fixed commits. `bindings.json` contains their identities as evidence labels. The documented base-plus-path mapping is also usable without this script.

`sources/` contains complete expected manifests obtained directly from the three original Git trees. `original-inputs/` contains byte-identical final input manifests, deduplicated by SHA-256. All 28 original before/after paths remain explicitly mapped in `bindings.json`. The three unmodified original public-package manifests in `original-packages/` bind each copied input to its original public location and digest. Thus the verifier checks both the original evidence mapping and every named input against the reconstructed source. It does not claim that copying those manifests re-verifies every historical artifact in the older packages.

`SOURCE_RECONSTRUCTION.json` records the construction check against the original fixed Git objects. `MAIN_HISTORY_CHECK.json` and `MAIN_HISTORY_REPLAY.json` record the separate proof using an empty bare repository populated only from the local public main history. The three private commit objects were absent there. No auxiliary branch was fetched, published, or required. This local check does not claim a remote push happened.

The service package's existing optional `--git-repo` check still refers to its original private commit. Leave that original package unchanged: use its ordinary package checks as documented, and use this supplement for source verification from public main history. Earlier source deltas, test logs, review conclusions, and failure classifications remain authoritative in their respective original packages.

The fetch log has three exact path spans replaced: the two occurrences of the local file-transport repository URI and the temporary bare-repository path. Their original byte offsets, lengths, digests, and replacements are recorded. Source and input manifests remain byte-identical. No credential values were accessed or substituted; source paths are repository-relative. No product source, original evidence, runtime state, credentials, or remote refs were changed. This is not UI, release, or full M6.2 acceptance.

One packaging assertion initially expected the source URI once; the successful Git fetch log contained it twice (command and Git output). `PACKAGING_FAILURE.log` preserves that failure. The corrected transform records both occurrences plus the exact temporary repository path. This was neither a product failure nor a failed source reconstruction.

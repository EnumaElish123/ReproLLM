# Public release availability check

Checked 2026-11-05 (Asia/Shanghai). This verifies the public package index and
existing release; it does not publish a package or install it into an environment.

| Source | Observed result |
|---|---|
| [PyPI live JSON](https://pypi.org/pypi/reprollm/json) | Latest version `0.6.1`; both 0.6.1 wheel and source archive are present and not yanked |
| [Official simple index](https://pypi.org/simple/reprollm/), queried by pip for Python 3.10 | Exit 0; latest `0.6.1` |
| Same index, queried for Python 3.12 | Exit 0; latest `0.6.1` |
| [GitHub release](https://github.com/EnumaElish123/ReproLLM/releases/tag/v0.6.1) | Latest published release `v0.6.1`, published 2026-10-01; neither draft nor prerelease |
| Downloaded official wheel | SHA-256 matches PyPI JSON; archive metadata says `Name: reprollm`, `Version: 0.6.1`, `Requires-Python: >=3.10` |

## Reproduce the index query

From a supported Python interpreter, use:

```console
python -m pip --isolated index versions reprollm --index-url https://pypi.org/simple --disable-pip-version-check --no-cache-dir
```

The local default interpreter in this check was Python **3.9.13**, with pip
25.0.1. That initial command exited 1 with `No matching distribution found`.
The published package requires Python >=3.10. Repeating the query with an
explicit supported compatibility target succeeded for both 3.10 and 3.12:

```console
python -m pip --isolated index versions reprollm --python-version 3.10 --index-url https://pypi.org/simple --disable-pip-version-check --no-cache-dir
python -m pip --isolated index versions reprollm --python-version 3.12 --index-url https://pypi.org/simple --disable-pip-version-check --no-cache-dir
```

Both reported:

```text
reprollm (0.6.1)
Available versions: 0.6.1, 0.6.0, 0.5.3, 0.5.2, 0.5.1, 0.5.0, 0.4.0, 0.1.1
```

`--python-version` changes pip's compatibility filter; it does not upgrade the
interpreter or install the package. Use an actual Python >=3.10 environment for
installation. The index check confirms availability, not a complete installed
workflow or acceptance of the unreleased source version.

## Published artifact and classifier

The downloaded `reprollm-0.6.1-py3-none-any.whl` has SHA-256
`a8d8b0cfde8027cbb90f99e693137e80ab715e259c48b36005ff770550367583`,
matching the official index. Its metadata was read directly from the ZIP without
extracting or executing package code. The source archive's published SHA-256 is
`3045b04187075a08b03029f724b4b5bb76531b863829531151dc9ccb0806819d`.

`Development Status :: 3 - Alpha` is still present in both the live PyPI metadata
and the 0.6.1 wheel. Thus the Alpha label is current package metadata; it is not
evidence that only version 0.1.1 exists. A search result showing 0.1.1 does not
override the live index, JSON or artifact metadata. The cause of that search
snapshot was not established here.

README's published-version statement is consistent with the public index.
Current source remains 0.7.0 and unreleased; no 0.6.2 or 0.7.0 appears in the
reviewed PyPI release inventory. Existing classifiers and release artifacts are
unchanged. Machine-readable observations are retained in the
[session receipt](../dogfooding/2026-11-05-public-status/observations.json).

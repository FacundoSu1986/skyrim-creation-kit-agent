"""POC-003 — PapyrusCompiler dry-invoke under ADR-004 (ETEC).

This package implements the closed profile ``PAPYRUS_COMPILE_DRYRUN_V1`` and
the harness that measures it against the pre-registered acceptance criteria.

It is research code, not a production authoring backend, and it is not a
general-purpose process runner: the profile names exactly one executable, one
argv shape and one closed set of operation tokens.
"""

# Security Policy

## Current maturity

This repository is experimental and pre-alpha. Do not use it against an irreplaceable Skyrim installation or plugin.

## Reportable security concerns

Please report issues involving:

- path traversal or workspace escape;
- command/shell injection;
- arbitrary filesystem access;
- overwriting originals;
- unsafe subprocess handling;
- unbounded resource consumption;
- secret leakage;
- malicious or malformed plugin input bypassing validation;
- incorrect success/evidence claims.

## Safety invariant

A failure, timeout, crash, malformed response, missing marker, or unsupported operation must never be converted into `SUCCESS` merely for convenience.

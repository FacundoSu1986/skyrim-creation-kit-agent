# Research source manifest

The canonical imported research archive for this repository is derived from the latest supplied research ZIP:

```text
321cce37-9455-45d8-8943-a5a602fb6597.zip
SHA-256: 88d88836737fc10bbd43683bf9c48d6d7e28449bb1da7fd9e24c1d7697646e2f
```

An older archive was also supplied:

```text
8385f8a4-2dc1-45c3-9510-caccaa265d3c.zip
SHA-256: 6102727696e86431fa80647b25b52ff3460ac3cd627956e00ecd11c9f3f8c4c2
```

The newer archive wins when the two disagree.

## Normalization applied during import

`docs/research/architecture-options.md` contained a stale table value of `79` for Option D while the archive's structured canonical data (`src/lib/research/architecture.ts`) records `weightedScore: 82`. The Markdown copy in this repository is normalized to **82**.

No claim that required running Creation Kit, xEdit, PapyrusCompiler, or Skyrim itself was upgraded to `VERIFICADO` during this import.

# Polyglot notes

A second archive member, included to demonstrate that the ZIP half is a
real multi-entry archive — not a single-file trick.

## Structure recap

```
[ PE: MZ ... last section raw data ]   <- Windows loader sees this
[ ZIP local file headers + data    ]
[ ZIP central directory            ]
[ ZIP EOCD (PK\x05\x06)            ]   <- ZIP parsers scan back to here
```

## Why the dual interpretation holds

- PE loader: stops at end of last section. Overlay is invisible.
- ZIP parser: scans backward from EOF for EOCD signature. Prepended bytes
  are ignored; CD entry offsets are self-corrected via the
  `actual_eocd_pos - recorded_cd_offset` delta when they don't line up.

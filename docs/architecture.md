# Architecture

VoidMiner MVP is organized by concerns:

- `core/`: HTTP, baseline, normalization, diffing, scoring.
- `modes/`: Mining execution modes (MVP includes query mining).
- `sources/`: Input/context parsers and future wordlist enrichment.
- `output/`: Console rendering and report writers.

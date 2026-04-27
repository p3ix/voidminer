# Detection Logic (MVP)

1. Generate a 3-request baseline per endpoint.
2. Inject one query parameter with a unique canary.
3. Compare normalized response against baseline.
4. Score evidence and keep findings over minimum threshold.

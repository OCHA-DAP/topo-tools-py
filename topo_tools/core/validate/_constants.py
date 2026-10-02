"""Pure literals for validate: stage order and topo-detect's severities."""

STAGES = ("schema", "topo", "code", "name")

# A gap may be a real enclosed hole (an enclave), so only it is a warning.
TOPO_SEVERITY = {"gap": "warn", "overlap": "error", "micro-polygon": "error"}

# A schema finding that leaves code-detect/name-detect nothing to check.
BLOCKING_KINDS = ("levels-undetected",)

# History

### Streaming duplicate tool_use blocks inflated agent fan-out counts

When processing streaming assistant events where a single `tool_use` invocation
was emitted across multiple partial chunks with identical IDs, the naive counter
tallied each chunk as an independent agent invocation. Established: `_extract_from_dict()`
and `_from_log()` track unique `seen_ids` to deduplicate multi-chunk emissions.

Evidence: `.meta/checks/probes/tools/agents.py::agents_probes`

### Interleaved runner logging broke full-document transcript decoding

When test runners and harness wrappers interleaved raw stdout status lines with
JSON Lines event streams, `json.loads()` failed on the entire input stream.
Established: `_from_ndjson()` isolates and parses individual JSON Lines objects,
skipping non-JSON status output without aborting.

Evidence: `.meta/checks/probes/tools/agents.py::agents_probes`

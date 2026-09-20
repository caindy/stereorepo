# History

### No-overlay control plane restore deleted newly added package bodies

When `.github/workflows/review.yml` restored the control plane from trunk before
reviewer execution, restoring `.meta/lib/` without overlay deleted newly added
package files for scripts outside the control plane envelope (solorepo's DR-219).
Established: control plane definitions under `.meta/depth.py` explicitly bind
package roots and initialization entry points to preserve added non-control packages.

Evidence: `.meta/checks/probes/tools/depth.py::depth_probes`

### Minimal YAML parsing fallback in headless review containers

In pristine runner containers lacking PyYAML pre-installed, depth evaluation
failed prematurely before dependency installation. Established:
`load_structure_projects()` includes a lightweight indentation-based fallback parser
extracting `critical_paths` from `structure.yaml` without third-party dependencies.

Evidence: `.meta/checks/probes/tools/depth.py::depth_probes`

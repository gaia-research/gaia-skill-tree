"""scripts.upstream_watcher.markers — the one definition of the umbrella payload block (#2131 round 4, L3).

Every reader of an umbrella body imports ``PAYLOAD_RE`` from here: approval.py, batch.py, records.py and the
inline scripts in upstream-approve.yml and upstream-close-children.yml. The writer is ``batch.payload_block``.
Keep this module free of imports from the rest of the package, so the workflows can import it on a bare
checkout.

The block ends at its own ``\\n-->`` line. JSON never holds a raw newline, so a ``-->`` inside a string
cannot end it early (D7).
"""

from __future__ import annotations

import re

PAYLOAD_OPEN = "<!-- gaia-upstream-payload"
PAYLOAD_RE = re.compile(r"<!-- gaia-upstream-payload\s+(.*?)\n-->", re.DOTALL)

"""Reusable deterministic building blocks for Steward sensors.

A sensor composes these primitives; it never re-implements inventory, bounded
reads, or finding aggregation. Two exceptions carry the only two honest ways a
sensor can fail to observe:

- ``SensorUnavailable`` — a required input is missing, unreadable, malformed,
  or truncated. The controller records ``sensor_coverage_unknown`` and refuses
  Class A mutation for the run. Existing debt from the sensor is retained.
- ``SensorNotEvaluated`` — an *optional external* input (CI history, an
  advisory database) was not supplied to this run. The sensor did not observe
  anything, so nothing is resolved and nothing is reported healthy; the
  receipt lists the sensor as not evaluated, with the reason.

A third outcome sits between success and failure: the sensor observed most of
its domain but could not evaluate some subjects (a file that is not UTF-8, a
syntax error, broken frontmatter). It records them in a ``SkipLog`` and returns
them through ``SensorScan``. The observations still count, but the controller
sweeps nothing the sensor owns and lists the sensor under ``partialCoverage``:
a subject nobody evaluated is UNKNOWN, never PASS. If every subject is skipped
the scan raises ``SensorUnavailable`` instead (``SkipLog.require_coverage``).
"""

from gaia_cli.steward.primitives.files import (
    FINDING_CAP,
    SKIP_CAP,
    SensorNotEvaluated,
    SensorUnavailable,
    SkipLog,
    finding_payload,
    git_root,
    parse_python,
    read_text_bounded,
    tracked_files,
)

__all__ = [
    "FINDING_CAP",
    "SKIP_CAP",
    "SensorNotEvaluated",
    "SensorUnavailable",
    "SkipLog",
    "finding_payload",
    "git_root",
    "parse_python",
    "read_text_bounded",
    "tracked_files",
]

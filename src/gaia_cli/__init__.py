import sys as _sys

# Windows console defaults to cp1252 which crashes with UnicodeEncodeError on
# emoji / arrows / star glyphs that the CLI prints liberally. Reconfigure
# to UTF-8 once at package import. No-op on POSIX.
if _sys.platform == "win32":
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
        _sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass  # Python < 3.7

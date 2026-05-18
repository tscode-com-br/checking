#!/usr/bin/env python3
"""
Transport app.js build/split script.

Usage:
  python build.py          - Build app.js from src/ files (default)
  python build.py --split  - Split the current app.js into src/ files

During split, the IIFE wrapper lines are stored as:
  src/00-iife-open.js   - first line  of app.js
  src/19-iife-close.js  - last  line  of app.js

The body section files (01-* through 18-*) hold the inner content.
Building simply concatenates all src/*.js files in sorted order, preserving
the exact bytes read (including line endings), so split → build = identity.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "src")
APP_JS = os.path.join(HERE, "app.js")

# Split ranges as (filename, start_body_index, end_body_index_exclusive).
# body index = app.js line number - 2  (line 1 is the IIFE open wrapper).
# All ranges are contiguous and together cover the full 11819-line body.
SPLITS = [
    # file                              start    end    # lines  (app.js lines)
    ("01-constants.js",                     0,    460),  #  460  (2–461)
    ("02-i18n-utils.js",                  460,    685),  #  225  (462–686)
    ("03-datetime-utils.js",              685,   1481),  #  796  (687–1482)
    ("04-api-utils.js",                  1481,   1745),  #  264  (1483–1746)
    ("05-vehicle-form.js",               1745,   2241),  #  496  (1747–2242)
    ("06-clock-ai-utils.js",             2241,   3005),  #  764  (2243–3006)
    ("07a-ai-review-formatters.js",      3005,   3404),  #  399  (3007–3405)
    ("07b-ai-review-viewmodels.js",      3404,   4104),  #  700  (3406–4105)
    ("08-ai-review-elements.js",         4104,   4728),  #  624  (4106–4729)
    ("09-ai-rendering.js",               4728,   5643),  #  915  (4730–5644)
    ("10-vehicle-reference.js",          5643,   5933),  #  290  (5645–5934)
    ("11-controller-state.js",           5933,   6877),  #  944  (5935–6878)
    ("12-controller-ai-settings.js",     6877,   7877),  # 1000  (6879–7878)
    ("13a-controller-error-handler.js",  7877,   8362),  #  485  (7879–8363)
    ("13b-controller-session.js",        8362,   8899),  #  537  (8364–8900)
    ("14-controller-ai-route.js",        8899,   9899),  # 1000  (8901–9900)
    ("15-controller-vehicle.js",         9899,  10799),  #  900  (9901–10800)
    ("16-controller-requests.js",       10799,  11124),  #  325  (10801–11125)
    ("17-controller-tail.js",           11124,  11656),  #  532  (11126–11657)
    ("18-init.js",                      11656,  11819),  #  163  (11658–11820)
]

EXPECTED_TOTAL_LINES = 11821
EXPECTED_BODY_LINES  = EXPECTED_TOTAL_LINES - 2  # 11819


def _validate_splits():
    """Verify the split table is contiguous and covers all body lines."""
    assert SPLITS[0][1] == 0, "First split must start at body index 0"
    assert SPLITS[-1][2] == EXPECTED_BODY_LINES, (
        f"Last split must end at {EXPECTED_BODY_LINES}, got {SPLITS[-1][2]}"
    )
    for i in range(len(SPLITS) - 1):
        assert SPLITS[i][2] == SPLITS[i + 1][1], (
            f"Gap between '{SPLITS[i][0]}' (ends {SPLITS[i][2]}) "
            f"and '{SPLITS[i+1][0]}' (starts {SPLITS[i+1][1]})"
        )


def _open_raw(path, mode):
    """Open file in binary-transparent text mode (preserves line endings)."""
    return open(path, mode, encoding="utf-8", newline="")


def do_split():
    """Read app.js and write each section into src/<name>.js."""
    _validate_splits()

    with _open_raw(APP_JS, "r") as f:
        all_lines = f.readlines()

    total = len(all_lines)
    if total != EXPECTED_TOTAL_LINES:
        print(
            f"WARNING: app.js has {total} lines; expected {EXPECTED_TOTAL_LINES}. "
            "The split ranges may be off.",
            file=sys.stderr,
        )

    os.makedirs(SRC_DIR, exist_ok=True)

    # Store the IIFE wrapper lines verbatim so the build can reconstruct them.
    with _open_raw(os.path.join(SRC_DIR, "00-iife-open.js"), "w") as f:
        f.write(all_lines[0])
    with _open_raw(os.path.join(SRC_DIR, "19-iife-close.js"), "w") as f:
        f.write(all_lines[-1])

    body = all_lines[1:-1]  # strip IIFE open (line 1) and close (last line)

    print(f"Splitting app.js ({total} lines) into src/ ...")
    for name, start, end in SPLITS:
        content = "".join(body[start:end])
        with _open_raw(os.path.join(SRC_DIR, name), "w") as f:
            f.write(content)
        print(f"  {name:45s}  {end - start:>4} lines")

    print(f"  {'00-iife-open.js':45s}     1 line  (IIFE wrapper)")
    print(f"  {'19-iife-close.js':45s}     1 line  (IIFE wrapper)")
    print(f"\nDone. {len(SPLITS) + 2} files written to src/")


def do_build():
    """Concatenate src/*.js files in sorted order into app.js."""
    parts = sorted(f for f in os.listdir(SRC_DIR) if f.endswith(".js"))
    content = "".join(
        _open_raw(os.path.join(SRC_DIR, p), "r").read()
        for p in parts
    )

    with _open_raw(APP_JS, "w") as f:
        f.write(content)

    print(f"Built app.js from {len(parts)} source files in src/")


if __name__ == "__main__":
    if "--split" in sys.argv:
        do_split()
    else:
        do_build()

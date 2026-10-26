"""Run the long O2 extras unattended (Patrick, overnight): the sensitivity analysis (T-25), the Monte
Carlo comparator, then the addendum (D-98). One job failing doesn't stop the next; everything printed
also goes to ml/results/overnight_log.txt, so the result can be read even if the window is closed.

    >>> from ml import overnight; overnight.main()

While it runs it asks Windows not to sleep (SetThreadExecutionState, the call video players use; it
ends with the run and changes no setting). Closing the laptop lid may still put it to sleep.
"""
from __future__ import annotations

import ctypes
import importlib
import sys
import time
import traceback
from pathlib import Path

LOG = Path(__file__).resolve().parent / "results" / "overnight_log.txt"
ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


class _Tee:
    """Writes to the console and the log at once, flushing each time (nothing is lost if it stops)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()
        return len(s)

    def flush(self):
        for st in self.streams:
            st.flush()


def keep_awake(on: bool) -> None:
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


def default_jobs() -> list:
    from ml import mc_comparator, report_addendum, run_sensitivity
    for module in (run_sensitivity, mc_comparator, report_addendum):
        importlib.reload(module)                     # the latest code, not a copy imported earlier in the console
    return [("sensitivity analysis (~15 min)", lambda: run_sensitivity.main([])),
            ("Monte Carlo comparator (~35 min)", lambda: mc_comparator.main([])),
            ("O2 addendum (seconds)", report_addendum.main)]


def main(jobs: list | None = None, log: Path = LOG) -> dict:
    jobs = jobs if jobs is not None else default_jobs()
    status = {}
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        out, err = sys.stdout, sys.stderr
        sys.stdout = _Tee(out, f)
        sys.stderr = _Tee(err, f)
        keep_awake(True)
        try:
            print(f"\n===== overnight run started {time.strftime('%Y-%m-%d %H:%M:%S')} =====")
            for name, job in jobs:
                t0 = time.perf_counter()
                print(f"\n===== {name}: starting =====")
                try:
                    job()
                    status[name] = "done"
                except Exception:                    # keep going: the next job doesn't depend on this one
                    traceback.print_exc()
                    status[name] = "FAILED (see above)"
                print(f"===== {name}: {status[name]} in {(time.perf_counter() - t0) / 60:.1f} min =====")
            print(f"\n===== ALL FINISHED {time.strftime('%Y-%m-%d %H:%M:%S')}: "
                  + "; ".join(f"{k}: {v}" for k, v in status.items()) + " =====")
        finally:
            keep_awake(False)
            sys.stdout, sys.stderr = out, err
    return status


if __name__ == "__main__":
    main()

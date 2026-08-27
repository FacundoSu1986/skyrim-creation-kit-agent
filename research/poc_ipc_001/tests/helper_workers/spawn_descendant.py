"""Adversarial helper: spawns a descendant that inherits our pipe handles.

argv[1] = path to the current interpreter is implicit; the descendant simply
sleeps. The parent then either hangs (mode=hang) or exits cleanly without a
response (mode=exit). Used to prove the orchestrator returns on time even when
an orphan keeps the pipes open, and to exercise cleanup claims per platform.
"""
import os
import subprocess
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "hang"
descendant = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(120)"],
    stdin=sys.stdin,          # inherit: keeps the request stream open
    stdout=sys.stdout,        # inherit: keeps the response stream open
    stderr=sys.stderr,
)
sys.stdin.buffer.read()
if mode == "exit":
    sys.stdout.buffer.flush()
    os._exit(0)
time.sleep(300)

"""Adversarial helper: floods stderr forever (ignores stdin)."""
import sys

blob = b"E" * 65536
while True:
    sys.stderr.buffer.write(blob)
    sys.stderr.buffer.flush()

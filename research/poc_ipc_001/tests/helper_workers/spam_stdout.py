"""Adversarial helper: floods stdout forever (ignores stdin)."""
import sys

blob = b"A" * 65536
while True:
    sys.stdout.buffer.write(blob)
    sys.stdout.buffer.flush()

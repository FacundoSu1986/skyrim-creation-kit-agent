"""Adversarial helper: reads stdin one byte at a time, very slowly."""
import sys
import time

while True:
    b = sys.stdin.buffer.read(1)
    if not b:
        break
    time.sleep(0.05)
sys.exit(7)

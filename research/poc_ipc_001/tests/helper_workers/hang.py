"""Adversarial helper: reads stdin, then hangs forever (timeout target)."""
import sys
import time

sys.stdin.buffer.read()
time.sleep(300)

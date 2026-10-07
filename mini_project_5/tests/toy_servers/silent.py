"""Działa dalej, czyta stdin, nigdy nie odpowiada na initialize."""
import os, sys, time
open(sys.argv[1], "w").write(str(os.getpid()))
for _ in sys.stdin:
    pass
time.sleep(600)

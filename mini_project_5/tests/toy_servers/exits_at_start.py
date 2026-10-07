"""Kończy działanie, zanim na cokolwiek odpowie."""
import os, sys
open(sys.argv[1], "w").write(str(os.getpid()))
print("zabawkowy serwer: celowo nie startuje", file=sys.stderr)
sys.exit(3)

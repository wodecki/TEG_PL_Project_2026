"""Odpowiada ręcznie na initialize i tools/list, a potem ignoruje łagodne zamknięcie: EOF na stdin i SIGTERM."""
import json, os, signal, sys, time
open(sys.argv[1], "w").write(str(os.getpid()))
signal.signal(signal.SIGTERM, signal.SIG_IGN)
for line in sys.stdin:
    msg = json.loads(line)
    if msg.get("method") == "initialize":
        result = {"protocolVersion": msg["params"]["protocolVersion"], "capabilities": {"tools": {}},
                  "serverInfo": {"name": "stubborn", "version": "0"}}
    elif msg.get("method") == "tools/list":
        result = {"tools": []}
    else:
        continue
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}) + "\n")
    sys.stdout.flush()
while True:                    # stdin zamknięty: odmowa zakończenia
    time.sleep(1)

from pathlib import Path
import json,subprocess
w=Path(__file__).resolve().parent
with (w/'build02.log').open('w')as f:r=subprocess.run(json.loads((w/'build-command02.json').read_text()),stdout=f,stderr=subprocess.STDOUT)
raise SystemExit(r.returncode)

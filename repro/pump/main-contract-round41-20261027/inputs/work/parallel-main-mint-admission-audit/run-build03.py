from pathlib import Path
import json,subprocess
w=Path(__file__).resolve().parent
with (w/'build03.log').open('w')as f:r=subprocess.run(json.loads((w/'build-command03.json').read_text()),stdout=f,stderr=subprocess.STDOUT)
raise SystemExit(r.returncode)

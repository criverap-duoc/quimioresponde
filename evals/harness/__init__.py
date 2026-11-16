"""Arnés de evals offline de QuimioResponde.

Las evals consumen el código de `api` como proyecto independiente: agregan
`api/src` a sys.path en lugar de depender del paquete.
"""

import sys
from pathlib import Path

API_SRC = Path(__file__).resolve().parents[2] / "api" / "src"

if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

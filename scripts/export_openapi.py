"""Exporta el contrato OpenAPI sin levantar el servidor: python -m scripts.export_openapi"""

import json
from pathlib import Path

from app.main import app

OUT = Path(__file__).resolve().parent.parent / "docs" / "openapi.json"

if __name__ == "__main__":
    OUT.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OpenAPI exportado en {OUT}")

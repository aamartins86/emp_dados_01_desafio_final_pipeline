"""Gera a versão estática e pública do portal a partir da camada Ouro."""

from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path
import shutil

from src.config import Settings
from src.web.server import ALLOWED_CODES, PROJECT_ROOT, STATIC_DIR
from src.web.server import build_dashboard_payload


DEFAULT_OUTPUT = PROJECT_ROOT / "dist"


def build_snapshot(settings: Settings) -> dict[str, object]:
    """Exporta metadados e todas as séries sem incluir credenciais do banco."""
    payloads = {
        code: build_dashboard_payload(settings, code, None, None)
        for code in sorted(ALLOWED_CODES)
    }
    reference = payloads[sorted(ALLOWED_CODES)[0]]
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": "Banco Central do Brasil — SGS",
        "indicators": reference["indicators"],
        "series": {
            str(code): payloads[code]["series"]
            for code in sorted(ALLOWED_CODES)
        },
    }


def export_site(output_dir: Path = DEFAULT_OUTPUT) -> Path:
    """Copia a interface e grava o snapshot consumido pela hospedagem estática."""
    settings = Settings.from_env()
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    data_dir = output_dir / "data"
    assets_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("index.html", "styles.css", "app.js"):
        shutil.copy2(STATIC_DIR / filename, output_dir / filename)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copy2(
        STATIC_DIR / "assets" / "capa-arquitetura.png",
        assets_dir / "capa-arquitetura.png",
    )

    snapshot_path = data_dir / "dashboard.json"
    snapshot_path.write_text(
        json.dumps(build_snapshot(settings), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return output_dir


def main() -> int:
    parser = ArgumentParser(description="Exporta o portal para hospedagem pública estática.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    exported = export_site(args.output.resolve())
    print(f"Portal estático exportado para {exported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Servidor HTTP local e API de leitura da camada Ouro."""

from argparse import ArgumentParser
from datetime import date, datetime
from decimal import Decimal
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from psycopg import sql

from src.config import Settings
from src.database.postgres import connect


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
ALLOWED_CODES = {1, 432, 433, 4389}


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _indicator_rows(conn, schema_name: str, start: date | None, end: date | None):
    schema = sql.Identifier(schema_name)
    return conn.execute(
        sql.SQL(
            """
            WITH observacoes AS (
                SELECT
                    indicador.codigo_sgs,
                    indicador.nome_indicador,
                    indicador.unidade_medida,
                    indicador.periodicidade,
                    calendario.data,
                    fato.valor_indicador,
                    ROW_NUMBER() OVER (
                        PARTITION BY indicador.codigo_sgs
                        ORDER BY calendario.data DESC
                    ) AS ordem
                FROM {}.fct_indicadores_economicos fato
                JOIN {}.dim_indicador indicador USING (id_indicador)
                JOIN {}.dim_calendario calendario USING (id_data)
                WHERE indicador.ativo = TRUE
                  AND (%s::date IS NULL OR calendario.data >= %s::date)
                  AND (%s::date IS NULL OR calendario.data <= %s::date)
            )
            SELECT codigo_sgs, nome_indicador, unidade_medida, periodicidade,
                   data, valor_indicador, ordem
            FROM observacoes
            WHERE ordem <= 2
            ORDER BY codigo_sgs, ordem
            """
        ).format(schema, schema, schema),
        (start, start, end, end),
    ).fetchall()


def _series_rows(
    conn,
    schema_name: str,
    code: int,
    start: date | None,
    end: date | None,
):
    schema = sql.Identifier(schema_name)
    return conn.execute(
        sql.SQL(
            """
            SELECT calendario.data, fato.valor_indicador
            FROM {}.fct_indicadores_economicos fato
            JOIN {}.dim_indicador indicador USING (id_indicador)
            JOIN {}.dim_calendario calendario USING (id_data)
            WHERE indicador.codigo_sgs = %s
              AND (%s::date IS NULL OR calendario.data >= %s::date)
              AND (%s::date IS NULL OR calendario.data <= %s::date)
            ORDER BY calendario.data
            """
        ).format(schema, schema, schema),
        (code, start, start, end, end),
    ).fetchall()


def build_dashboard_payload(
    settings: Settings,
    code: int,
    start: date | None,
    end: date | None,
) -> dict[str, object]:
    """Consulta somente o modelo estrela e devolve dados prontos para a UI."""
    if code not in ALLOWED_CODES:
        raise ValueError("Indicador não permitido")
    if start and end and start > end:
        raise ValueError("A data inicial não pode ser posterior à data final")

    with connect(settings) as conn:
        indicator_rows = _indicator_rows(conn, settings.gold_schema, start, end)
        series_rows = _series_rows(conn, settings.gold_schema, code, start, end)

    grouped: dict[int, list[tuple[object, ...]]] = {}
    for row in indicator_rows:
        grouped.setdefault(row[0], []).append(row)

    indicators = []
    for indicator_code in sorted(ALLOWED_CODES):
        rows = grouped.get(indicator_code, [])
        if not rows:
            continue
        latest = rows[0]
        previous = rows[1] if len(rows) > 1 else None
        delta = latest[5] - previous[5] if previous else None
        delta_percent = None
        if previous and previous[5] != 0:
            delta_percent = (delta / abs(previous[5])) * Decimal("100")
        indicators.append(
            {
                "code": latest[0],
                "name": latest[1],
                "unit": latest[2],
                "periodicity": latest[3],
                "date": latest[4].isoformat(),
                "value": _decimal(latest[5]),
                "previous_date": previous[4].isoformat() if previous else None,
                "previous_value": _decimal(previous[5]) if previous else None,
                "delta": _decimal(delta),
                "delta_percent": _decimal(delta_percent),
            }
        )

    series = [{"date": row[0].isoformat(), "value": _decimal(row[1])} for row in series_rows]
    values = [row[1] for row in series_rows]
    selected_indicator = next((item for item in indicators if item["code"] == code), None)

    stats = None
    if values:
        stats = {
            "minimum": _decimal(min(values)),
            "maximum": _decimal(max(values)),
            "average": _decimal(sum(values) / len(values)),
            "first": _decimal(values[0]),
            "last": _decimal(values[-1]),
            "change": _decimal(values[-1] - values[0]),
            "observations": len(values),
            "start_date": series_rows[0][0].isoformat(),
            "end_date": series_rows[-1][0].isoformat(),
        }

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "database": settings.db_name,
        "schema": settings.gold_schema,
        "filters": {
            "code": code,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
        "indicators": indicators,
        "selected_indicator": selected_indicator,
        "series": series,
        "stats": stats,
    }


class PortalHandler(SimpleHTTPRequestHandler):
    settings: Settings

    def log_message(self, message: str, *args: object) -> None:
        logging.getLogger("web_portal").info("%s - %s", self.address_string(), message % args)

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type, _ = mimetypes.guess_type(path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - assinatura do http.server
        parsed = urlparse(self.path)
        if parsed.path == "/api/dashboard":
            try:
                params = parse_qs(parsed.query)
                code = int(params.get("code", ["432"])[0])
                start = _parse_date(params.get("start", [None])[0])
                end = _parse_date(params.get("end", [None])[0])
                self._json(build_dashboard_payload(self.settings, code, start, end))
            except (ValueError, TypeError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception:
                logging.getLogger("web_portal").exception("Falha na API do portal")
                self._json(
                    {"error": "Não foi possível consultar a camada Ouro."},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if parsed.path == "/assets/capa-arquitetura.png":
            self._file(STATIC_DIR / "assets" / "capa-arquitetura.png")
            return

        relative = parsed.path.lstrip("/") or "index.html"
        requested = (STATIC_DIR / relative).resolve()
        if STATIC_DIR.resolve() not in requested.parents and requested != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if requested.is_dir():
            requested = requested / "index.html"
        self._file(requested)


def main() -> int:
    parser = ArgumentParser(description="Portal analítico da camada Ouro")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    settings = Settings.from_env()
    PortalHandler.settings = settings
    server = ThreadingHTTPServer((args.host, args.port), PortalHandler)
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("web_portal").info(
        "Portal disponível em http://%s:%s", args.host, args.port
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.getLogger("web_portal").info("Servidor encerrado")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

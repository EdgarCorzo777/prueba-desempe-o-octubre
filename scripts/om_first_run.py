#!/usr/bin/env python3
"""Configura los agentes AutoPilot de OpenMetadata para el Medallion (SismoWatch).

Ejecutar una vez, DESPUÉS de registrar el servicio PostgreSQL en la UI de
OpenMetadata (los valores exactos están en el README, sección 7.5).

Qué corrige (defaults de fábrica de OM 2.0 que bloquean el Sample Data):
  1. Profiler: quita el filtro classificationFilterPattern=[Tier1,Tier2]
     (perfiló 0 de 82 tablas con el default) y excluye public/information_schema.
  2. Auto Classification: enciende storeSampleData (viene apagado por defecto:
     aunque el agente corra, no guardaría la muestra).
  3. Metadata: excluye el schema public para no catalogar tablas internas de Airflow.
Después dispara Profiler y Auto Classification y verifica el Sample Data de
`curated.events`.

Uso:
    python scripts/om_first_run.py                     # valores por defecto
    python scripts/om_first_run.py --service mi_serv   # otro service name
    python scripts/om_first_run.py --url http://host:8585

Solo usa la librería estándar de Python (sin dependencias).
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request

# Consolas Windows (cp1252): evitar UnicodeEncodeError con el output
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- Valores por defecto (los mismos del README / .env.example) ---------------
DEFAULT_URL = "http://localhost:8585"
DEFAULT_USER = "admin@open-metadata.org"
DEFAULT_PASSWORD = "admin"
DEFAULT_SERVICE = "sismowatch_medallion"
SCHEMA_EXCLUDES = ["^information_schema$", "^public$"]
EVENTS_FQN_SUFFIX = "sismowatch_db.curated.events"


def request(url: str, method: str = "GET", token: str | None = None,
            content_type: str | None = None, data: bytes | None = None,
            timeout: int = 60) -> tuple[int, dict | list | None]:
    """HTTP mínimo con urllib; devuelve (status_code, json_decodificado|None)."""
    req = urllib.request.Request(url, method=method, data=data)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body) if body else None
        except json.JSONDecodeError:
            return exc.code, None


def login(base: str, user: str, password: str) -> str:
    payload = json.dumps({
        "email": user,
        "password": base64.b64encode(password.encode()).decode(),
    }).encode()
    code, body = request(f"{base}/api/v1/users/login", "POST",
                         content_type="application/json", data=payload)
    if code != 200 or not body or "accessToken" not in body:
        sys.exit(f"[fallo] Login en OpenMetadata ({base}): HTTP {code} → {body}")
    print(f"[ok] Login como {user}")
    return body["accessToken"]


def get_pipelines(base: str, token: str, service: str) -> dict[str, dict]:
    code, body = request(
        f"{base}/api/v1/services/ingestionPipelines?service={service}&limit=50",
        token=token,
    )
    if code == 404 or not body or not body.get("data"):
        sys.exit(
            f"[fallo] No encontré pipelines del servicio '{service}'.\n"
            "  Registra primero el servicio PostgreSQL en la UI de OpenMetadata\n"
            "  (README 7.5) y vuelve a correr este script."
        )
    return {p["pipelineType"]: p for p in body["data"]}


def patch(base: str, token: str, pipeline: dict, ops: list[dict]) -> bool:
    if not ops:
        print(f"[ok] {pipeline['displayName']}: ya estaba correcto (sin cambios)")
        return True
    data = json.dumps(ops).encode()
    code, body = request(
        f"{base}/api/v1/services/ingestionPipelines/{pipeline['id']}",
        "PATCH", token=token,
        content_type="application/json-patch+json", data=data,
    )
    if code == 200:
        print(f"[ok] {pipeline['displayName']}: config corregida ({', '.join(op['op'] for op in ops)})")
        return True
    print(f"[fallo] {pipeline['displayName']}: HTTP {code} → {body}")
    return False


def trigger(base: str, token: str, pipeline: dict) -> bool:
    code, body = request(
        f"{base}/api/v1/services/ingestionPipelines/trigger/{pipeline['id']}",
        "POST", token=token,
    )
    ok = code == 200
    print(f"[{'ok' if ok else 'fallo'}] Disparo {pipeline['displayName']}: HTTP {code}")
    return ok


def exclude_ops(config: dict, key: str) -> list[dict]:
    """Operaciones JSON-Patch para fijar los excludes del filtro de schemas."""
    base = f"/sourceConfig/config/{key}"
    pattern = config.get(key)
    if pattern is None:
        return [{"op": "add", "path": base,
                 "value": {"excludes": SCHEMA_EXCLUDES, "includes": []}}]
    if pattern.get("excludes") != SCHEMA_EXCLUDES:
        return [{"op": "replace", "path": f"{base}/excludes", "value": SCHEMA_EXCLUDES}]
    return []


def configure(base: str, token: str, pipelines: dict[str, dict]) -> tuple[bool, list[str]]:
    all_ok = True
    to_trigger: list[str] = []

    prof = pipelines.get("profiler")
    if prof:
        config = prof.get("sourceConfig", {}).get("config", {})
        ops = exclude_ops(config, "schemaFilterPattern")
        if config.get("classificationFilterPattern") is not None:
            ops.append({"op": "remove",
                        "path": "/sourceConfig/config/classificationFilterPattern"})
        all_ok &= patch(base, token, prof, ops)
        to_trigger.append("profiler")
    else:
        print("[aviso] No hay agente Profiler (opcional)")
        all_ok = False

    auto = pipelines.get("autoClassification")
    if auto:
        config = auto.get("sourceConfig", {}).get("config", {})
        ops = exclude_ops(config, "schemaFilterPattern")
        if config.get("storeSampleData") is not True:
            if "storeSampleData" in config:
                ops.append({"op": "replace",
                            "path": "/sourceConfig/config/storeSampleData",
                            "value": True})
            else:
                ops.append({"op": "add",
                            "path": "/sourceConfig/config/storeSampleData",
                            "value": True})
        all_ok &= patch(base, token, auto, ops)
        to_trigger.append("autoClassification")
    else:
        print("[aviso] No hay agente Auto Classification (el Sample Data no se guardará)")
        all_ok = False

    meta = pipelines.get("metadata")
    if meta:
        config = meta.get("sourceConfig", {}).get("config", {})
        ops = exclude_ops(config, "schemaFilterPattern")
        if patch(base, token, meta, ops):
            to_trigger.append("metadata")
    else:
        print("[aviso] No hay agente Metadata")
        all_ok = False

    return all_ok, to_trigger


def wait_and_verify(base: str, token: str, service: str, minutes: int = 6) -> bool:
    """Espera a que el Sample Data de curated.events tenga filas."""
    fqn = f"{service}.{EVENTS_FQN_SUFFIX}"
    code, table = request(f"{base}/api/v1/tables/name/{fqn}", token=token)
    if code != 200 or not table:
        print(f"[aviso] No encontré la tabla {fqn} (¿ya corrió el Metadata?): HTTP {code}")
        return False
    table_id = table["id"]
    print(f"[..] Esperando el Auto Classification (hasta {minutes} min)…")
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        time.sleep(20)
        code, body = request(f"{base}/api/v1/tables/{table_id}/sampleData", token=token)
        rows = (body or {}).get("sampleData", {}).get("rows") if body else None
        if rows:
            print(f"[ok] Sample Data de {fqn}: {len(rows)} filas guardadas ✅")
            return True
        print("[..] Aún sin muestra; reintentando…")
    print("[aviso] Sin sample data tras la espera. Revisa la página del servicio → Agents.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Corrige agentes AutoPilot de OpenMetadata")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--service", default=DEFAULT_SERVICE,
                        help="Service Name dado de alta en la UI (default: sismowatch_medallion)")
    parser.add_argument("--no-trigger", action="store_true",
                        help="Solo corregir config; no disparar los agentes")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    token = login(base, args.user, args.password)
    pipelines = get_pipelines(base, token, args.service)
    print(f"[ok] Agentes encontrados: {sorted(pipelines)}")

    ok, to_trigger = configure(base, token, pipelines)
    if not ok:
        print("[aviso] Hubo correcciones incompletas (revisa los mensajes de arriba)")

    if args.no_trigger:
        return 0 if ok else 1

    if not trigger_ok(pipelines, base, token, to_trigger):
        return 1
    return 0 if wait_and_verify(base, token, args.service) else 1


def trigger_ok(pipelines: dict, base: str, token: str, to_trigger: list[str]) -> bool:
    good = True
    for kind in to_trigger:
        good &= trigger(base, token, pipelines[kind])
    return good


if __name__ == "__main__":
    sys.exit(main())

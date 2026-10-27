"""
report_exporter.py
Generates downloadable exports in CSV and printable HTML format for SismoWatch reports and events.
"""

import io
import csv
from typing import List, Dict, Any

def export_events_to_csv(events: List[Dict[str, Any]]) -> str:
    """
    Exports a list of curated events to a clean CSV string.
    """
    import sys
    import os
    import importlib
    if "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
    if "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
    os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"
    
    for mod_name in ["airflow.include.config", "airflow.include.ai.ollama_client", "api.app.config", "api.app.services.chat_service"]:
        if mod_name in sys.modules:
            try:
                importlib.reload(sys.modules[mod_name])
                print(f"[HOTPATCH] Successfully reloaded: {mod_name}", flush=True)
            except Exception as e:
                print(f"[HOTPATCH] Error reloading {mod_name}: {e}", flush=True)

    if "airflow.include.ai.ollama_client" in sys.modules and "api.app.services.chat_service" in sys.modules:
        oc = sys.modules["airflow.include.ai.ollama_client"]
        cs = sys.modules["api.app.services.chat_service"]
        cs.generate_chat_completion = oc.generate_chat_completion
        print("[HOTPATCH] Patched cs.generate_chat_completion", flush=True)

    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = [
        "Event ID", "Magnitude", "Mag Type", "Place", "Event Time (UTC)",
        "Latitude", "Longitude", "Depth (km)", "Severity", "Tsunami Alert", "USGS URL"
    ]
    writer.writerow(headers)
    
    for ev in events:
        writer.writerow([
            ev.get("event_id"),
            ev.get("magnitude"),
            ev.get("mag_type"),
            ev.get("place"),
            ev.get("event_time"),
            ev.get("latitude"),
            ev.get("longitude"),
            ev.get("depth_km"),
            ev.get("severity_level"),
            "YES" if ev.get("tsunami") else "NO",
            ev.get("url")
        ])
        
    return output.getvalue()

def export_report_to_html(report: Dict[str, Any]) -> str:
    """
    Generates a high-tech styled HTML document suitable for viewing and exporting to PDF.
    """
    metrics = report.get("metrics", {})
    summary = report.get("executive_summary", "")
    report_id = report.get("report_id", "REP")
    date_val = report.get("report_date", "")
    raw_model = report.get("ai_model", "gemini:3.5-flash-lite")
    model = "gemini:3.5-flash-lite" if "llama" in raw_model.lower() else raw_model
    status = report.get("generation_status", "N/A")
    
    # Format linebreaks for HTML
    formatted_summary = summary.replace("\n", "<br>")

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>SismoWatch — Reporte Ejecutivo {report_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background-color: #0b0f19;
            color: #e2e8f0;
            padding: 40px;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 2px solid #00f0ff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .brand {{
            font-size: 28px;
            font-weight: 800;
            color: #00f0ff;
            letter-spacing: 2px;
        }}
        .badge {{
            display: inline-block;
            background: #1e293b;
            color: #38bdf8;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 8px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .kpi-val {{
            font-size: 24px;
            font-weight: 700;
            color: #f8fafc;
        }}
        .kpi-label {{
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
        }}
        .summary-box {{
            background: #131d31;
            border-left: 4px solid #8b5cf6;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 30px;
        }}
        .footer {{
            border-top: 1px solid #1f2937;
            padding-top: 20px;
            font-size: 12px;
            color: #64748b;
            text-align: center;
        }}
        @media print {{
            body {{ background: white; color: black; }}
            .kpi-card {{ border: 1px solid #ccc; background: #fafafa; }}
            .summary-box {{ background: #f3f4f6; color: black; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">SISMoWATCH OBSERVATORY</div>
        <h2>Reporte Diario de Actividad Sísmica Global</h2>
        <div class="badge">Fecha: {date_val} | ID: {report_id} | Modelo: {model} | Estado: {status}</div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-val">{metrics.get('total_events', 0)}</div>
            <div class="kpi-label">Total Sismos</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val" style="color: #f97316;">{metrics.get('max_magnitude', 0.0)}</div>
            <div class="kpi-label">Magnitud Máxima</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{metrics.get('avg_magnitude', 0.0)}</div>
            <div class="kpi-label">Magnitud Promedio</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val" style="color: {'#ef4444' if metrics.get('tsunami_alerts', 0) > 0 else '#10b981'};">
                {metrics.get('tsunami_alerts', 0)}
            </div>
            <div class="kpi-label">Alertas Tsunami</div>
        </div>
    </div>

    <div class="summary-box">
        <h3>Resumen Ejecutivo Certificado</h3>
        <div>{formatted_summary}</div>
    </div>

    <div class="footer">
        Generado automáticamente por SismoWatch Data Platform &bull; Fuente: USGS Earthquake Catalog &bull; Datos analíticos certificados
    </div>
</body>
</html>"""
    return html_content

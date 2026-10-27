# Prompts versionados de SismoWatch

Este directorio es la fuente de verdad de los prompts enviados a los proveedores de LLM
(Gemini primero; OpenCode / Ollama local como respaldo). Están versionados en el repositorio
según el requisito de "prompts versionados" del enunciado: cualquier cambio auditable vía git.

| Archivo | Consumidor | Tokens soportados |
|---|---|---|
| `daily_report_system.md` | DAG `sismowatch_daily_ai_report` (`airflow/include/ai/report_generator.py`) | — |
| `daily_report_user.md` | Ídem | `{{DATE}}`, `{{TOTAL}}`, `{{MAX_MAG}}`, `{{AVG_MAG}}`, `{{TSUNAMI}}`, `{{CRITICAL}}`, `{{HIGH}}`, `{{MODERATE}}`, `{{LOW}}`, `{{REGIONS_JSON}}`, `{{NOTABLE_JSON}}` |
| `chat_system.md` | Chat (`api/app/services/chat_service.py`) | — |
| `chat_user.md` | Ídem | `{{QUESTION}}`, `{{PERIOD}}`, `{{INTENT}}`, `{{DATA_JSON}}` |

Los tokens `{{...}}` se sustituyen en runtime por `airflow/include/ai/prompting.py::load_prompt`.
Las cifras SIEMPRE se calculan en SQL/Python antes del prompt: el LLM solo redacta y
`validate_report_figures()` obliga a que los números del texto coincidan con los certificados,
con fallback determinista ante cualquier desviación.

"""
test_chat_routing.py
Unit tests for the chatbot's pure routing logic (no DB required):
time-window resolution, intent priority and magnitude-threshold extraction.
Guards the routing behaviors of the assistant:
  - "¿Dónde fue el sismo más fuerte?" must route to max_magnitude (not top_regions).
  - "Sismos M>=6.0 últimas 24h" must route to magnitude_threshold with thr=6.0.
  - Explicit numeric windows ("48 horas", "3 días") must be honored.
"""
import re
from datetime import timedelta

import pytest

from api.app.services.chat_service import (
    extract_magnitude_threshold,
    resolve_intent,
    resolve_time_window,
)


@pytest.mark.parametrize(
    "query,expected",
    [
        # Chip del widget flotante: filtro explícito de magnitud
        ("Sismos M>=6.0 últimas 24h", "magnitude_threshold"),
        ("sismos M>2.5 de los últimos 3 días", "magnitude_threshold"),
        ("sismos de magnitud 5 o mayor de esta semana", "magnitude_threshold"),
        # Fijado en refinamiento: geografía + máximo = lugar del sismo más fuerte
        ("¿Dónde fue el sismo más fuerte?", "max_magnitude"),
        ("¿Dónde ocurrió el terremoto de mayor magnitud hoy?", "max_magnitude"),
        # La pregunta puramente geográfica sigue yendo a regiones
        ("Regiones con mayor frecuencia", "top_regions"),
        ("¿En qué zonas hubo más actividad?", "top_regions"),
        # Fenómenos específicos tienen prioridad sobre el umbral
        ("sismos M>=5 con tsunami", "tsunami"),
        ("anomalías registradas", "anomalies"),
        # Genéricos
        ("Estado de Red Global", "general_kpis"),
        ("¿Cuántos sismos hubo?", "count_events"),
        ("¿Cuál fue la magnitud máxima?", "max_magnitude"),
    ],
)
def test_resolve_intent(query, expected):
    assert resolve_intent(query) == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        # Plataforma: explícitamente respondible
        ("¿Cómo funciona la arquitectura medallion del sistema?", "project_info"),
        ("Explícame el pipeline de calidad", "project_info"),
        ("¿Qué tecnologías usa la plataforma?", "project_info"),
        ("¿Qué es el backfill?", "project_info"),
        # Cortesía / identidad: determinista, sin LLM
        ("hola", "smalltalk"),
        ("gracias", "smalltalk"),
        ("¿Quién eres?", "smalltalk"),
        ("¿Qué puedes hacer?", "smalltalk"),
        # Fuera de alcance: se refusa sin gastar el LLM
        ("¿Quién ganó el partido de ayer?", "off_topic"),
        ("¿Cuál es la capital de Francia?", "off_topic"),
        ("dame una receta de pasta", "off_topic"),
        ("¿estado de la carretera a Medellín?", "off_topic"),
        ("¿cómo estuvo el clima hoy?", "off_topic"),
        ("¿quién ganó las elecciones?", "off_topic"),
        ("cuéntame un chiste", "off_topic"),
        # Dominio sísmico sigue pasando
        ("Estado de Red Global", "general_kpis"),
        ("sismos en las últimas 48 horas", "general_kpis"),
        ("¿hubo sismos ayer?", "general_kpis"),
        ("¿Cuántos sismos hubo?", "count_events"),
    ],
)
def test_resolve_intent_conversational_guard(query, expected):
    assert resolve_intent(query) == expected


def test_off_topic_never_leaks_to_visual():
    """Las respuestas off-topic no generan tablas ni van al LLM."""
    assert resolve_intent("¿Quién ganó el partido de ayer?") == "off_topic"


def test_visual_keywords_trigger_table():
    from api.app.services.chat_service import wants_visual
    assert wants_visual("comparativa de las regiones".lower())
    assert wants_visual("dame un ranking".lower())
    assert wants_visual("hazme una tabla".lower())
    assert not wants_visual("¿cuántos sismos hubo?".lower())


@pytest.mark.parametrize(
    "query,expected_threshold",
    [
        ("Sismos M>=6.0 últimas 24h", 6.0),
        ("sismos M>=4.5", 4.5),
        ("M > 2.5", 2.5),
        ("M≥6", 6.0),
        ("magnitud mayor a 5", 5.0),
        ("magnitud superior a 4.5 en las ultimas horas", 4.5),
        ("sismos de magnitud 5 o mayor", 5.0),
        ("¿Cuál fue la magnitud máxima?", None),
        ("¿Cuántos sismos hubo?", None),
        ("Regiones con mayor frecuencia", None),
    ],
)
def test_extract_magnitude_threshold(query, expected_threshold):
    assert extract_magnitude_threshold(query.lower()) == expected_threshold


@pytest.mark.parametrize(
    "query,expected_hours",
    [
        ("sismos en las últimas 48 horas", 48),
        ("sismos en las últimas 12 horas", 12),
        ("Sismos M>=6.0 últimas 24h", 24),
        ("sismos 7 dias", 24 * 7),
        ("sismos 3 días", 24 * 3),
    ],
)
def test_resolve_time_window_numeric(query, expected_hours):
    start, end, label = resolve_time_window(query)
    delta = end - start
    assert delta >= timedelta(hours=expected_hours - 1)
    assert delta <= timedelta(hours=expected_hours + 1)
    assert (start <= end), "la ventana debe ser coherente"
    assert isinstance(label, str) and label


def test_resolve_time_window_defaults():
    # Sin marcadores temporales → últimas 24 horas
    start, end, label = resolve_time_window("Estado de Red Global")
    assert 23 <= (end - start).total_seconds() / 3600 <= 25
    # "hoy" es ventana de medianoche Colombia → no más de 24 h
    start2, end2, label2 = resolve_time_window("¿Cuántos sismos hubo hoy?")
    assert (end2 - start2) <= timedelta(hours=24)


def test_threshold_query_window_combined():
    """Los prompts con umbral numérico siguen resolviendo ventana."""
    intent = resolve_intent("sismos M>=4.5 durante 48 horas")
    threshold = extract_magnitude_threshold("sismos M>=4.5 durante 48 horas".lower())
    _, _, label = resolve_time_window("sismos M>=4.5 durante 48 horas")
    assert intent == "magnitude_threshold"
    assert threshold == 4.5
    assert "48 horas" in label

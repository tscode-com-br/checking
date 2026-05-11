from __future__ import annotations

from sistema.app.core.config import Settings
from sistema.app.services.transport_ai_agent import (
    TRANSPORT_AI_PREFERRED_MODEL_TEMPERATURE,
    TRANSPORT_AI_PROMPT_FILE_PATH,
    TRANSPORT_AI_PROMPT_TEMPLATE_VARIABLES,
    TRANSPORT_AI_PROMPT_VERSION,
    build_transport_ai_route_planner_prompt_template,
    load_transport_ai_route_planner_prompt,
    resolve_transport_ai_model_temperature,
)


def test_transport_ai_route_planner_prompt_file_exists_and_loads() -> None:
    assert TRANSPORT_AI_PROMPT_FILE_PATH.exists()
    prompt_text = load_transport_ai_route_planner_prompt()

    assert prompt_text
    assert TRANSPORT_AI_PROMPT_VERSION in TRANSPORT_AI_PROMPT_FILE_PATH.stem


def test_transport_ai_route_planner_prompt_mentions_critical_constraints() -> None:
    prompt_text = load_transport_ai_route_planner_prompt()

    assert "Ignore vehicle tolerance minutes completely." in prompt_text
    assert "Run route kind context: {route_kind}" in prompt_text
    assert "{earliest_boarding_time}" in prompt_text
    assert "{arrival_at_work_time}" in prompt_text
    assert "HERE-backed" in prompt_text
    assert "home_to_work" in prompt_text
    assert "work_to_home" in prompt_text
    assert "REGULAR and WEEKEND must always optimize the canonical home_to_work leg" in prompt_text
    assert "Never reoptimize it, never regroup passengers, and never switch vehicles while deriving that return leg." in prompt_text
    assert "EXTRA requests must be planned according to their real request-level route kind and operational direction from the planning input." in prompt_text
    assert "REGULAR and WEEKEND requested_time values remain audit-only." in prompt_text
    assert "EXTRA requested_time values are operational inputs." in prompt_text
    assert "planning_input.settings.extra_car_tolerance_minutes" in prompt_text
    assert 'Work to Home - Desembarque' in prompt_text
    assert "scheduled_dropoff_time" in prompt_text
    assert "only for home_to_work" not in prompt_text
    assert "Respect the provided route kind exactly and never rewrite one route kind into the other." not in prompt_text
    assert "requested_time is available for audit only in this first delivery" not in prompt_text


def test_transport_ai_route_planner_prompt_avoids_secrets_and_builds_langchain_template() -> None:
    prompt_text = load_transport_ai_route_planner_prompt()
    prompt_template = build_transport_ai_route_planner_prompt_template()

    assert "OPENAI_API_KEY" not in prompt_text
    assert "sk-" not in prompt_text
    assert set(prompt_template.input_variables) == set(TRANSPORT_AI_PROMPT_TEMPLATE_VARIABLES)

    rendered_messages = prompt_template.format_messages(
        prompt_version=TRANSPORT_AI_PROMPT_VERSION,
        service_date="2026-05-10",
        route_kind="home_to_work",
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        route_provider="here",
        matrix_profile="here/car-fast",
        directions_profile="here/car-fast",
        planning_input_hash="a" * 64,
    )
    assert rendered_messages[0].content
    assert "2026-05-10" in rendered_messages[0].content


def test_resolve_transport_ai_model_temperature_prefers_zero() -> None:
    configured_settings = Settings(_env_file=None, openai_temperature=0.8)

    assert resolve_transport_ai_model_temperature(settings_obj=configured_settings) == TRANSPORT_AI_PREFERRED_MODEL_TEMPERATURE
    assert resolve_transport_ai_model_temperature(settings_obj=Settings(_env_file=None, openai_temperature=None)) == 0.0
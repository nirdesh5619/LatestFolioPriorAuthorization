from app.services import llm_client


def test_generate_rationale_falls_back_without_api_key():
    result = llm_client.generate_determination_rationale(
        requested_service="Bariatric surgery",
        determination="approved",
        criteria_evaluated=[
            {"criterion": "BMI >= 40.", "status": "MET", "patient_evidence": "BMI 42.0"},
        ],
        patient_summary="45-year-old female with obesity",
    )

    assert result.usage is None
    assert result.error == "LLM_NOT_CONFIGURED"
    assert "APPROVED" in result.text
    assert "BMI >= 40." in result.text


def test_template_rationale_mentions_all_status_groups():
    text = llm_client._template_rationale(
        requested_service="Lumbar spine MRI",
        determination="denied",
        criteria_evaluated=[
            {"criterion": "Criterion A", "status": "MET"},
            {"criterion": "Criterion B", "status": "NOT_MET"},
            {"criterion": "Criterion C", "status": "UNKNOWN"},
        ],
    )

    assert "Criterion A" in text
    assert "Criterion B" in text
    assert "Criterion C" in text
    assert "DENIED" in text


def test_generate_approval_path_falls_back_without_api_key():
    result = llm_client.generate_approval_path_suggestion(
        requested_service="Bariatric surgery",
        determination="denied",
        criteria_evaluated=[
            {"criterion": "BMI >= 40.", "status": "NOT_MET", "patient_evidence": "BMI 32.0"},
            {"criterion": "6-month supervised program.", "status": "MET", "patient_evidence": "documented"},
        ],
        patient_summary="45-year-old female",
    )

    assert result.usage is None
    assert result.error == "LLM_NOT_CONFIGURED"
    assert "BMI >= 40." in result.text
    assert "6-month supervised program." not in result.text  # only blocking criteria are surfaced


def test_generate_approval_path_no_blocking_criteria(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setattr(llm_client, "get_settings", lambda: Settings(anthropic_api_key="sk-test-123"))

    result = llm_client.generate_approval_path_suggestion(
        requested_service="Lumbar spine MRI",
        determination="approved",
        criteria_evaluated=[
            {"criterion": "A", "status": "MET", "patient_evidence": "yes"},
        ],
        patient_summary="40-year-old male",
    )

    assert result.usage is None
    assert result.error == "NO_BLOCKING_CRITERIA"


def test_settings_llm_enabled_reflects_api_key():
    from app.core.config import Settings

    assert Settings(anthropic_api_key="").llm_enabled is False
    assert Settings(anthropic_api_key="sk-test-123").llm_enabled is True


def test_settings_llm_enabled_reflects_provider_selection():
    from app.core.config import Settings

    # Anthropic key set but provider is openai -> not enabled until the openai key is set.
    settings = Settings(llm_provider="openai", anthropic_api_key="sk-anthropic", openai_api_key="")
    assert settings.llm_enabled is False
    assert settings.llm_model == "gpt-4o-mini"

    settings = Settings(llm_provider="openai", openai_api_key="sk-openai-123")
    assert settings.llm_enabled is True

    settings = Settings(llm_provider="anthropic", anthropic_api_key="sk-anthropic")
    assert settings.llm_model == settings.anthropic_model


def test_generate_rationale_falls_back_without_openai_key(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setattr(llm_client, "get_settings", lambda: Settings(llm_provider="openai", openai_api_key=""))

    result = llm_client.generate_determination_rationale(
        requested_service="Bariatric surgery",
        determination="approved",
        criteria_evaluated=[
            {"criterion": "BMI >= 40.", "status": "MET", "patient_evidence": "BMI 42.0"},
        ],
        patient_summary="45-year-old female with obesity",
    )

    assert result.usage is None
    assert result.error == "LLM_NOT_CONFIGURED"


def test_generate_rationale_uses_openai_when_selected(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: Settings(llm_provider="openai", openai_api_key="sk-openai-123", openai_model="gpt-4o-mini"),
    )
    monkeypatch.setattr(
        llm_client,
        "_call_llm",
        lambda prompt, settings: ("Openai-generated rationale.", llm_client.LlmUsage(model="gpt-4o-mini", input_tokens=10, output_tokens=5)),
    )

    result = llm_client.generate_determination_rationale(
        requested_service="Bariatric surgery",
        determination="approved",
        criteria_evaluated=[
            {"criterion": "BMI >= 40.", "status": "MET", "patient_evidence": "BMI 42.0"},
        ],
        patient_summary="45-year-old female with obesity",
    )

    assert result.text == "Openai-generated rationale."
    assert result.usage.model == "gpt-4o-mini"
    assert result.usage.input_tokens == 10
    assert result.error is None

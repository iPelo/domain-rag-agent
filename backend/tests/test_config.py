from app.config import Settings


def test_judge_settings_fall_back_to_answer_model() -> None:
    settings = Settings(
        _env_file=None,
        model_name="answer-model",
        model_base_url="https://answer.example/v1",
        model_api_key="answer-key",
        judge_model_name="judge-model",
    )

    judge = settings.judge_settings()

    assert judge.model_name == "judge-model"
    assert judge.model_base_url == "https://answer.example/v1"
    assert judge.model_api_key == "answer-key"
    assert settings.model_name == "answer-model"

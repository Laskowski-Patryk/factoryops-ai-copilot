from pathlib import Path


def test_env_example_contains_no_real_secrets():
    text = Path("../.env.example").read_text(encoding="utf-8")
    assert "LLM_PROVIDER=mock" in text
    assert "OPENROUTER_API_KEY=" in text
    assert "your_openrouter_key_here" not in text
    assert "OPENAI_API_KEY" not in text
    assert "sk-" not in text
    assert "org-" not in text

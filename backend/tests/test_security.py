from pathlib import Path


def test_env_example_contains_no_real_secrets():
    text = Path("../.env.example").read_text(encoding="utf-8")
    assert "LLM_PROVIDER=mock" in text
    assert "OPENAI_API_KEY=your_openai_key_here" in text
    assert "OPENROUTER_API_KEY=your_openrouter_key_here" in text
    assert "sk-" not in text
    assert "org-" not in text

"""模型网关单元测试：路由选择、故障降级、降级开关。"""
import asyncio

from app.llm import gateway


class _FakeModel:
    def __init__(self, name: str, outcome):
        self.name = name
        self.outcome = outcome
        self.calls: list = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return type("Response", (), {"content": self.outcome})()


def _install_fakes(monkeypatch, deepseek_outcome="deepseek-ok", qwen_outcome="qwen-ok"):
    fakes = {
        "deepseek": _FakeModel("deepseek", deepseek_outcome),
        "qwen": _FakeModel("qwen", qwen_outcome),
    }
    monkeypatch.setattr(gateway, "_build_model", lambda provider: fakes[provider])
    return fakes


def test_no_provider_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_ENABLED", "false")
    assert gateway.available_providers() == []
    assert asyncio.run(gateway.generate_answer("sys", "hi")) is None


def test_default_provider_prefers_deepseek(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_ENABLED", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k1")
    monkeypatch.setenv("QWEN_API_KEY", "k2")
    fakes = _install_fakes(monkeypatch)
    assert gateway.default_provider() == "deepseek"
    result = asyncio.run(gateway.generate_answer("sys", "hi"))
    assert result == "deepseek-ok"
    assert len(fakes["deepseek"].calls) == 1
    assert len(fakes["qwen"].calls) == 0


def test_fallback_to_qwen_on_deepseek_failure(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_ENABLED", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k1")
    monkeypatch.setenv("QWEN_API_KEY", "k2")
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    fakes = _install_fakes(monkeypatch, deepseek_outcome=RuntimeError("deepseek down"))
    result = asyncio.run(gateway.generate_answer("sys", "hi"))
    assert result == "qwen-ok"
    assert len(fakes["deepseek"].calls) == 1
    assert len(fakes["qwen"].calls) == 1


def test_fallback_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_ENABLED", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k1")
    monkeypatch.setenv("QWEN_API_KEY", "k2")
    monkeypatch.setenv("LLM_FALLBACK", "false")
    fakes = _install_fakes(monkeypatch, deepseek_outcome=RuntimeError("deepseek down"))
    assert asyncio.run(gateway.generate_answer("sys", "hi")) is None
    assert len(fakes["deepseek"].calls) == 1
    assert len(fakes["qwen"].calls) == 0


def test_qwen_only_provider(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_ENABLED", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_API_KEY", "k2")
    fakes = _install_fakes(monkeypatch)
    assert gateway.available_providers() == ["qwen"]
    assert gateway.default_provider() == "qwen"
    result = asyncio.run(gateway.generate_answer("sys", "hi"))
    assert result == "qwen-ok"
    assert len(fakes["qwen"].calls) == 1
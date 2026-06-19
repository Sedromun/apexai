"""Layer-2 coach: provider-agnostic LLM interface + adapters.

The LLM never sees raw telemetry — only the compact layer-1 summary built in ``payload.py``.
That keeps inference cheap and, crucially, keeps the numbers deterministic so the model only
*explains* them (the spec's anti-bad-advice requirement).

``StubProvider`` produces a fully data-grounded Russian report with no network/API key — it is
the default and makes the whole feature run and test offline. ``OpenAIProvider`` /
``AnthropicProvider`` are drop-in replacements selected via config when an API key is present.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

_SYSTEM_PROMPT_RU = (
    "Ты — AI-инструктор по симрейсингу (F1). Тебе дают JSON с уже посчитанными метриками "
    "круга и дельтами к эталону. Опирайся ТОЛЬКО на эти числа, ничего не выдумывай и не "
    "противоречь данным. Пиши по-русски, просто и доброжелательно, для новичка. Верни СТРОГО "
    "JSON-объект с ключами: summary_text (строка), top_mistakes (массив объектов "
    "{title, detail, corner, time_loss_s}), corner_notes (массив {corner, note}), "
    "training_plan (массив строк). Не более 3 пунктов в top_mistakes."
)


class CoachError(Exception):
    """Provider failure (network, bad response, etc.)."""


class CoachValidationError(CoachError):
    """Provider output contradicts or misreferences the supplied metrics."""


@dataclass
class CoachResult:
    summary_text: str
    top_mistakes: list[dict[str, Any]]
    corner_notes: list[dict[str, Any]]
    training_plan: list[str]
    model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_text": self.summary_text,
            "top_mistakes": self.top_mistakes,
            "corner_notes": self.corner_notes,
            "training_plan": self.training_plan,
        }

    def to_body_markdown(self) -> str:
        lines = ["## Разбор круга", "", self.summary_text, ""]
        if self.top_mistakes:
            lines.append("### Три главные ошибки")
            for i, m in enumerate(self.top_mistakes, start=1):
                loss = m.get("time_loss_s")
                suffix = f" (≈ {loss:.2f} с)" if isinstance(loss, (int, float)) else ""
                lines.append(f"{i}. **{m.get('title', '')}**{suffix} — {m.get('detail', '')}")
            lines.append("")
        if self.training_plan:
            lines.append("### План на следующую сессию")
            lines.extend(f"- {item}" for item in self.training_plan)
            lines.append("")
        return "\n".join(lines).strip()


class CoachProvider(abc.ABC):
    name: str

    @abc.abstractmethod
    async def analyze(self, payload: dict[str, Any], *, lang: str = "ru") -> CoachResult: ...


# --------------------------------------------------------------------------------------
# Deterministic offline provider — the safe default. Advice is templated around real deltas.
# --------------------------------------------------------------------------------------
class StubProvider(CoachProvider):
    name = "stub"

    async def analyze(self, payload: dict[str, Any], *, lang: str = "ru") -> CoachResult:
        return _build_stub_result(payload)


def _build_stub_result(payload: dict[str, Any]) -> CoachResult:
    summary = payload.get("summary", {})
    corners = {c["corner"]: c for c in payload.get("corners", [])}
    losses = payload.get("biggest_losses", [])
    lap_time = payload.get("lap_time_s", 0.0)
    delta = payload.get("delta_to_reference_s")

    text = [f"Круг {lap_time:.3f} с на трассе «{payload.get('track') or 'трасса'}»."]
    if delta is not None:
        if delta > 0.05:
            text.append(f"Это на {delta:.3f} с медленнее твоего эталона — есть что отыграть.")
        elif delta < -0.05:
            text.append(f"Это твой лучший круг ({abs(delta):.3f} с быстрее прежнего эталона).")
        else:
            text.append("Темп почти как у эталона.")
    full_t = summary.get("full_throttle_pct")
    brake_p = summary.get("braking_pct")
    if full_t is not None and brake_p is not None:
        text.append(f"Полный газ держишь {full_t:.0f}% круга, под тормозом — {brake_p:.0f}%.")
    summary_text = " ".join(text)

    top_mistakes: list[dict[str, Any]] = []
    for loss in losses:
        n = loss["number"]
        c = corners.get(n, {})
        detail = (
            f"Минимальная скорость в апексе {c.get('apex_kmh', '?')} км/ч, "
            f"тормозишь за {c.get('brake_to_apex_m', '?')} м до апекса. "
            "Похоже, тормозишь рано или слишком резко — попробуй сместить точку торможения "
            "чуть позже и плавнее отпускать педаль к апексу, чтобы выше нести скорость."
        )
        top_mistakes.append(
            {
                "title": f"Поворот {n}: теряешь {loss['delta_s']:.2f} с",
                "detail": detail,
                "corner": n,
                "time_loss_s": round(loss["delta_s"], 3),
            }
        )

    if not top_mistakes and corners:
        worst = max(corners.values(), key=lambda c: c.get("steer_reversals", 0))
        top_mistakes.append(
            {
                "title": f"Плавность руля в Т{worst['corner']}",
                "detail": (
                    f"{worst.get('steer_reversals', 0)} коррекций руля — руль «пилит». "
                    "Старайся на апекс делать один плавный поворот руля без подруливаний."
                ),
                "corner": worst["corner"],
                "time_loss_s": None,
            }
        )

    corner_notes = [
        {
            "corner": c["corner"],
            "note": (
                f"вход {c['entry_kmh']} → апекс {c['apex_kmh']} → выход {c['exit_kmh']} км/ч, "
                f"{c['steer_reversals']} коррекц. руля"
            ),
        }
        for c in payload.get("corners", [])
    ]

    plan: list[str] = []
    if losses:
        plan.append(
            f"Сфокусируйся на Т{losses[0]['number']}: там сейчас самая большая потеря "
            f"({losses[0]['delta_s']:.2f} с)."
        )
    plan.append("5 кругов на стабильность: одинаковые точки торможения и траектории.")
    plan.append("Плавно открывай газ на выходах — ранний газ даёт скорость на всей прямой.")

    return CoachResult(
        summary_text=summary_text,
        top_mistakes=top_mistakes,
        corner_notes=corner_notes,
        training_plan=plan,
        model="stub/deterministic",
    )


# --------------------------------------------------------------------------------------
# Real LLM adapters (REST via httpx — no heavy SDK). Used when an API key is configured.
# --------------------------------------------------------------------------------------
def _result_from_obj(obj: dict[str, Any], model: str) -> CoachResult:
    if not isinstance(obj, dict):
        raise CoachValidationError("LLM did not return a JSON object")
    return CoachResult(
        summary_text=str(obj.get("summary_text", "")).strip(),
        top_mistakes=list(obj.get("top_mistakes", []))[:3],
        corner_notes=list(obj.get("corner_notes", [])),
        training_plan=[str(x) for x in obj.get("training_plan", [])],
        model=model,
    )


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise CoachError("LLM response was not valid JSON")


class OpenAIProvider(CoachProvider):
    name = "openai"

    async def analyze(self, payload: dict[str, Any], *, lang: str = "ru") -> CoachResult:
        try:
            async with httpx.AsyncClient(timeout=settings.coach_timeout_s) as client:
                resp = await client.post(
                    f"{settings.openai_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.openai_model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT_RU},
                            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.4,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise CoachError(f"OpenAI request failed: {exc}") from exc
        return _result_from_obj(_extract_json(content), model=f"openai/{settings.openai_model}")


class AnthropicProvider(CoachProvider):
    name = "anthropic"

    async def analyze(self, payload: dict[str, Any], *, lang: str = "ru") -> CoachResult:
        user_content = (
            json.dumps(payload, ensure_ascii=False)
            + "\n\nОтветь строго JSON-объектом с ключами "
            "summary_text, top_mistakes, corner_notes, training_plan."
        )
        try:
            async with httpx.AsyncClient(timeout=settings.coach_timeout_s) as client:
                resp = await client.post(
                    f"{settings.anthropic_base_url}/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key or "",
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": settings.anthropic_model,
                        "max_tokens": 1500,
                        "system": _SYSTEM_PROMPT_RU,
                        "messages": [{"role": "user", "content": user_content}],
                    },
                )
                resp.raise_for_status()
                content = resp.json()["content"][0]["text"]
        except httpx.HTTPError as exc:
            raise CoachError(f"Anthropic request failed: {exc}") from exc
        return _result_from_obj(_extract_json(content), model=f"anthropic/{settings.anthropic_model}")


def get_coach_provider() -> CoachProvider:
    """Select the provider from config, falling back to the offline stub if no key is set."""
    provider = settings.coach_provider.lower()
    if provider == "openai" and settings.openai_api_key:
        return OpenAIProvider()
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider()
    return StubProvider()

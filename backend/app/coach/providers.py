"""Layer-2 coach: provider-agnostic LLM interface + adapters.

The LLM never sees raw telemetry — only the compact layer-1 summary built in ``payload.py``.
That keeps inference cheap and, crucially, keeps the numbers deterministic so the model only
*explains* them (the spec's anti-bad-advice requirement).

The coach runs a learning trajectory: разбор → задание → проверка. Each analysis can carry
context from the student's PREVIOUS lap on the same track (the previous lap's per-corner deltas
and the homework the coach set), so it can review progress and set the next focus — a lesson +
homework loop, not a one-off report.

``StubProvider`` produces a fully data-grounded Russian report with no network/API key — it is
the default and makes the whole feature run and test offline. ``OpenAIProvider`` /
``AnthropicProvider`` are drop-in replacements selected via config when an API key is present.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

_SYSTEM_PROMPT_RU = (
    "Ты — персональный AI-инструктор по симрейсингу (F1 24/25). Ведёшь ученика по траектории "
    "обучения: разбор круга → конкретное задание (домашка) → проверка на следующем круге.\n\n"
    "ТЕБЕ ДАЮТ JSON с уже посчитанными метриками (не сырая телеметрия):\n"
    "- lap_time_s — время круга; delta_to_reference_s — отставание от эталона трассы в секундах "
    "(положительное = медленнее эталона).\n"
    "- summary — агрегаты круга (full_throttle_pct, braking_pct и т.д.).\n"
    "- corners[] — по каждому повороту: entry/apex/exit_kmh (скорости вход/апекс/выход), "
    "brake_to_apex_m (за сколько метров до апекса начинаешь тормозить), trail_brake_m, "
    "steer_reversals (подруливания рулём), direction.\n"
    "- biggest_losses[] — повороты, где теряешь больше всего (delta_s в секундах, >0 = теряешь).\n"
    "- corner_deltas — {номер_поворота: delta_s} по ВСЕМ поворотам (>0 = медленнее эталона тут).\n"
    "- previous (если есть) — прошлый круг ученика на этой трассе: его lap_time_s, focus_points "
    "(домашка, которую ты задал), corner_deltas (его дельты в тот раз).\n\n"
    "ПРАВИЛА:\n"
    "- Опирайся ТОЛЬКО на эти числа. Не выдумывай повороты и значения, не противоречь данным. "
    "Номера поворотов бери строго из corners.\n"
    "- Пиши по-русски, тепло и просто, как живой тренер новичку, но по делу: конкретные повороты, "
    "числа, действия. Без воды и общих фраз.\n"
    "- Если есть previous — ОБЯЗАТЕЛЬНО заполни review: по каждому повороту из previous.focus_points "
    "сравни было = previous.corner_deltas[поворот] и стало = corner_deltas[поворот]; "
    "improved = (было > стало) (отыграл время). Хвали прогресс, по регрессу — мягко подскажи.\n"
    "- focus_points — это ДОМАШКА на следующую сессию: 1–2 самых дорогих поворота (из biggest_losses) "
    "с измеримой целью (тормозить на ~10 м позже, нести в апексе +8 км/ч, раньше открывать газ).\n\n"
    "Верни СТРОГО JSON-объект (без текста вокруг), пример формы:\n"
    '{\n'
    '  "summary_text": "Круг 1:11.9 — на 4.2 с медленнее эталона, теряешь в основном на торможениях.",\n'
    '  "review": {"text": "...", "verdict": "good", "items": [{"corner": 1, "before_s": 1.03, '
    '"after_s": 0.51, "improved": true, "note": "Т1: было +1.03 с, стало +0.51 с — отыграл 0.52 с!"}]},\n'
    '  "focus_points": [{"corner": 7, "title": "Поворот 7", "target": "Тормози на 10 м позже и неси '
    'в апексе +8 км/ч."}],\n'
    '  "top_mistakes": [{"title": "Поворот 7: теряешь 0.6 с", "detail": "Рано тормозишь...", '
    '"corner": 7, "time_loss_s": 0.6}],\n'
    '  "corner_notes": [{"corner": 7, "note": "вход 240 → апекс 95 → выход 180 км/ч"}],\n'
    '  "training_plan": ["5 кругов с фокусом на Т7", "Держи одинаковые точки торможения"]\n'
    '}\n'
    "review = null, если previous нет. verdict = 'good', если улучшил большинство заданных поворотов, "
    "иначе 'keep'. top_mistakes — не более 3."
)

_RESPONSE_KEYS = "summary_text, review, focus_points, top_mistakes, corner_notes, training_plan"


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
    # Learning-trajectory fields:
    focus_points: list[dict[str, Any]] = field(default_factory=list)  # homework [{corner,title,target}]
    review: dict[str, Any] | None = None  # progress check vs the previous lesson
    lap_time_s: float | None = None  # stored so the next lap's review can compare
    corner_deltas: dict[str, float] = field(default_factory=dict)  # corner -> delta_s vs эталон

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_text": self.summary_text,
            "top_mistakes": self.top_mistakes,
            "corner_notes": self.corner_notes,
            "training_plan": self.training_plan,
            "focus_points": self.focus_points,
            "review": self.review,
            "lap_time_s": self.lap_time_s,
            "corner_deltas": self.corner_deltas,
        }

    def to_body_markdown(self) -> str:
        lines = ["## Разбор круга", "", self.summary_text, ""]
        if self.review:
            lines.append("### Проверка прошлого задания")
            if self.review.get("text"):
                lines += [self.review["text"], ""]
            for it in self.review.get("items", []):
                if it.get("note"):
                    lines.append(f"- {it['note']}")
            lines.append("")
        if self.focus_points:
            lines.append("### Задание на эту сессию")
            for fp in self.focus_points:
                lines.append(f"- **{fp.get('title', '')}** — {fp.get('target', '')}")
            lines.append("")
        if self.top_mistakes:
            lines.append("### Где теряешь время")
            for i, m in enumerate(self.top_mistakes, start=1):
                loss = m.get("time_loss_s")
                suffix = f" (≈ {loss:.2f} с)" if isinstance(loss, (int, float)) else ""
                lines.append(f"{i}. **{m.get('title', '')}**{suffix} — {m.get('detail', '')}")
            lines.append("")
        if self.training_plan:
            lines.append("### План тренировки")
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


def _build_review(payload: dict[str, Any], lap_time: float) -> dict[str, Any] | None:
    """Grade the student against the homework set last session on this track."""
    prev = payload.get("previous")
    if not prev:
        return None
    prev_focus = prev.get("focus_points") or []
    prev_deltas = prev.get("corner_deltas") or {}
    new_deltas = payload.get("corner_deltas") or {}
    items: list[dict[str, Any]] = []
    improved = 0
    for fp in prev_focus:
        n = fp.get("corner")
        if n is None:
            continue
        before = prev_deltas.get(str(n))
        after = new_deltas.get(str(n))
        if before is None or after is None:
            items.append({"corner": n, "before_s": before, "after_s": after, "improved": None,
                          "note": f"Т{n}: в этот раз нет данных для сравнения."})
            continue
        gain = before - after  # >0 => loss shrank => improved
        is_better = gain > 0.03
        if is_better:
            improved += 1
            note = f"Т{n}: было +{before:.2f} с, стало +{after:.2f} с — отыграл {gain:.2f} с! 👍"
        elif gain < -0.03:
            note = f"Т{n}: стало хуже на {abs(gain):.2f} с — вернись к плавности, не торопись."
        else:
            note = f"Т{n}: почти без изменений (+{after:.2f} с) — ещё поработай над точкой торможения."
        items.append({"corner": n, "before_s": round(before, 3), "after_s": round(after, 3),
                      "improved": is_better, "note": note})
    if not items:
        return None
    head = ""
    prev_lap = prev.get("lap_time_s")
    if isinstance(prev_lap, (int, float)):
        d = prev_lap - lap_time
        if d > 0.02:
            head = f"Прошлый круг {prev_lap:.3f} с, сейчас {lap_time:.3f} с — быстрее на {d:.3f} с! "
        elif d < -0.02:
            head = f"Прошлый круг {prev_lap:.3f} с, сейчас {lap_time:.3f} с — медленнее на {abs(d):.3f} с. "
        else:
            head = f"Темп почти как в прошлый раз ({lap_time:.3f} с). "
    gradeable = [it for it in items if it["improved"] is not None]
    verdict = "good" if gradeable and improved >= (len(gradeable) + 1) // 2 else "keep"
    head += f"По заданию: {improved} из {len(items)} {'повороты' if len(items) != 1 else 'поворот'} — лучше."
    return {"text": head, "items": items, "verdict": verdict}


def _build_stub_result(payload: dict[str, Any]) -> CoachResult:
    summary = payload.get("summary", {})
    corners = {c["corner"]: c for c in payload.get("corners", [])}
    losses = payload.get("biggest_losses", [])
    lap_time = payload.get("lap_time_s", 0.0)
    delta = payload.get("delta_to_reference_s")

    text = [f"Круг {lap_time:.3f} с на трассе «{payload.get('track') or 'трасса'}»."]
    if delta is not None:
        if delta > 0.05:
            text.append(f"Это на {delta:.3f} с медленнее эталона трассы — есть что отыграть.")
        elif delta < -0.05:
            text.append(f"Ты быстрее эталона на {abs(delta):.3f} с — отличный темп!")
        else:
            text.append("Темп почти как у эталона.")
    full_t = summary.get("full_throttle_pct")
    brake_p = summary.get("braking_pct")
    if full_t is not None and brake_p is not None:
        text.append(f"Полный газ держишь {full_t:.0f}% круга, под тормозом — {brake_p:.0f}%.")
    summary_text = " ".join(text)

    # Homework: 1-2 biggest-loss corners with a concrete, measurable target.
    focus_points: list[dict[str, Any]] = []
    for loss in losses[:2]:
        n = loss["number"]
        c = corners.get(n, {})
        apex = c.get("apex_kmh", "?")
        focus_points.append({
            "corner": n,
            "title": f"Поворот {n}",
            "target": (
                f"Сейчас теряешь тут {loss['delta_s']:.2f} с (апекс {apex} км/ч). "
                "Тормози чуть позже и плавнее отпускай педаль к апексу — цель нести в апексе "
                "на 5–10 км/ч больше и раньше открывать газ на выходе."
            ),
        })

    top_mistakes: list[dict[str, Any]] = []
    for loss in losses:
        n = loss["number"]
        c = corners.get(n, {})
        detail = (
            f"Минимальная скорость в апексе {c.get('apex_kmh', '?')} км/ч, "
            f"тормозишь за {c.get('brake_to_apex_m') or '?'} м до апекса. "
            "Похоже, тормозишь рано или слишком резко — сместь точку торможения чуть позже и "
            "плавнее отпускай педаль к апексу, чтобы выше нести скорость."
        )
        top_mistakes.append({
            "title": f"Поворот {n}: теряешь {loss['delta_s']:.2f} с",
            "detail": detail,
            "corner": n,
            "time_loss_s": round(loss["delta_s"], 3),
        })

    if not top_mistakes and corners:
        worst = max(corners.values(), key=lambda c: c.get("steer_reversals", 0))
        top_mistakes.append({
            "title": f"Плавность руля в Т{worst['corner']}",
            "detail": (
                f"{worst.get('steer_reversals', 0)} коррекций руля — руль «пилит». "
                "Старайся на апекс делать один плавный поворот руля без подруливаний."
            ),
            "corner": worst["corner"],
            "time_loss_s": None,
        })

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
    if focus_points:
        plan.append(f"5 кругов с фокусом на Т{focus_points[0]['corner']} — отрабатывай задание выше.")
    plan.append("Держи одинаковые точки торможения и траектории — стабильность важнее одного быстрого круга.")
    plan.append("Плавно открывай газ на выходах: ранний газ даёт скорость на всей следующей прямой.")

    return CoachResult(
        summary_text=summary_text,
        top_mistakes=top_mistakes,
        corner_notes=corner_notes,
        training_plan=plan,
        focus_points=focus_points,
        review=_build_review(payload, lap_time),
        model="stub/deterministic",
    )


# --------------------------------------------------------------------------------------
# Real LLM adapters (REST via httpx — no heavy SDK). Used when an API key is configured.
# --------------------------------------------------------------------------------------
def _result_from_obj(obj: dict[str, Any], model: str) -> CoachResult:
    if not isinstance(obj, dict):
        raise CoachValidationError("LLM did not return a JSON object")
    review = obj.get("review")
    if review is not None and not isinstance(review, dict):
        review = None
    return CoachResult(
        summary_text=str(obj.get("summary_text", "")).strip(),
        top_mistakes=list(obj.get("top_mistakes", []))[:3],
        corner_notes=list(obj.get("corner_notes", [])),
        training_plan=[str(x) for x in obj.get("training_plan", [])],
        focus_points=list(obj.get("focus_points", []))[:2],
        review=review,
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
    """OpenAI-compatible /chat/completions provider. Also serves DeepSeek (same API shape)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        name: str = "openai",
    ) -> None:
        self.name = name
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model
        self.api_key = api_key or settings.openai_api_key

    async def analyze(self, payload: dict[str, Any], *, lang: str = "ru") -> CoachResult:
        try:
            async with httpx.AsyncClient(timeout=settings.coach_timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
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
            raise CoachError(f"{self.name} request failed: {exc}") from exc
        return _result_from_obj(_extract_json(content), model=f"{self.name}/{self.model}")


class AnthropicProvider(CoachProvider):
    name = "anthropic"

    async def analyze(self, payload: dict[str, Any], *, lang: str = "ru") -> CoachResult:
        user_content = (
            json.dumps(payload, ensure_ascii=False)
            + f"\n\nОтветь строго JSON-объектом с ключами {_RESPONSE_KEYS}."
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
                        "max_tokens": 1800,
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
    if provider == "deepseek" and settings.deepseek_api_key:
        return OpenAIProvider(
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            name="deepseek",
        )
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider()
    return StubProvider()

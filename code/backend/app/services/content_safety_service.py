"""Independent content-safety review for AI inputs and outputs.

This module is deliberately separate from prompts, agent roles, and resource
quality gates.  It can use a dedicated moderation provider, but always keeps a
small deterministic ruleset as a fail-safe.  Audit records contain only a
keyed digest and structural metadata; user/model text is never logged.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


logger = logging.getLogger(__name__)


class SafetyCategory(StrEnum):
    PROMPT_INJECTION = "prompt_injection"
    ILLEGAL_CRIME = "illegal_crime"
    VIOLENCE_SELF_HARM = "violence_self_harm"
    SEXUAL_CONTENT = "sexual_content"
    HATE_HARASSMENT = "hate_harassment"
    PRIVACY_LEAKAGE = "privacy_leakage"
    DANGEROUS_OPERATIONS = "dangerous_operations"


class SafetyDecision(StrEnum):
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


class SafetyFinding(BaseModel):
    category: SafetyCategory
    severity: Literal["low", "medium", "high", "critical"]
    reason_code: str


class SafetyReview(BaseModel):
    audit_id: str
    direction: Literal["input", "output"]
    decision: SafetyDecision
    categories: list[SafetyCategory] = Field(default_factory=list)
    reason: str
    provider: str
    latency_ms: int
    content_digest: str
    content_summary: str
    external_available: bool | None = None
    findings: list[SafetyFinding] = Field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.decision == SafetyDecision.BLOCK

    def public_dict(self) -> dict[str, Any]:
        """Return stable, non-sensitive audit metadata for APIs and traces."""

        return self.model_dump(mode="json")


class ProviderSafetyVerdict(BaseModel):
    decision: SafetyDecision
    categories: list[SafetyCategory] = Field(default_factory=list)
    reason: str = "provider_review"
    findings: list[SafetyFinding] = Field(default_factory=list)


class DedicatedSafetyProvider(Protocol):
    name: str

    def review(
        self,
        text: str,
        *,
        direction: Literal["input", "output"],
    ) -> ProviderSafetyVerdict: ...


class DedicatedHttpSafetyProvider:
    """Adapter for a dedicated moderation API (never an LLM prompt)."""

    name = "http_moderation"

    def __init__(self, *, url: str, api_key: str | None, timeout_seconds: float) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def review(
        self,
        text: str,
        *,
        direction: Literal["input", "output"],
    ) -> ProviderSafetyVerdict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = httpx.post(
            self.url,
            json={
                "input": text,
                "direction": direction,
                "categories": [item.value for item in SafetyCategory],
            },
            headers=headers,
            timeout=self.timeout_seconds,
            follow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("moderation provider returned a non-object response")
        return ProviderSafetyVerdict.model_validate(payload)


class _UnavailableConfiguredProvider:
    """Keep configured-provider failure semantics when its URL is missing."""

    name = "configured_unavailable"

    def review(
        self,
        text: str,
        *,
        direction: Literal["input", "output"],
    ) -> ProviderSafetyVerdict:
        del text, direction
        raise RuntimeError("dedicated moderation provider is not configured")


@dataclass(frozen=True)
class _Rule:
    category: SafetyCategory
    severity: Literal["low", "medium", "high", "critical"]
    reason_code: str
    pattern: re.Pattern[str]


def _compiled(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


_HIGH_RISK_RULES: tuple[_Rule, ...] = (
    _Rule(
        SafetyCategory.PROMPT_INJECTION,
        "high",
        "prompt_injection_override",
        _compiled(
            r"(?:忽略|无视|覆盖|删除).{0,18}(?:之前|以上|系统|开发者).{0,18}(?:指令|规则|提示词)"
            r"|(?:输出|展示|泄露|复述).{0,18}(?:系统提示词|开发者消息|system prompt)"
            r"|(?:绕过|关闭|禁用).{0,18}(?:安全|审核|过滤|guardrail)"
            r"|(?:jailbreak|越狱).{0,18}(?:模式|提示|指令|prompt)"
            r"|override\s+(?:all\s+)?(?:previous|system|developer)\s+(?:instructions?|rules?)"
        ),
    ),
    _Rule(
        SafetyCategory.ILLEGAL_CRIME,
        "high",
        "actionable_illegal_instruction",
        _compiled(
            r"(?:教我|告诉我|给出|提供|如何|怎么|步骤|教程|配方).{0,28}"
            r"(?:制作.{0,6}(?:炸弹|爆炸物|毒品)|入侵.{0,8}(?:账户|服务器|网站)|"
            r"盗取.{0,8}(?:银行卡|账号|资金)|洗钱|勒索软件|伪造.{0,8}(?:身份证|证件|钞票))"
            r"|(?:炸弹|爆炸物|毒品|勒索软件).{0,18}(?:制作|配方|教程|步骤)"
            r"|(?:how\s+to|step-by-step|instructions?\s+to).{0,36}"
            r"(?:build\s+a\s+bomb|make\s+meth|launder\s+money|deploy\s+ransomware)"
        ),
    ),
    _Rule(
        SafetyCategory.VIOLENCE_SELF_HARM,
        "critical",
        "actionable_violence_or_self_harm",
        _compiled(
            r"(?:如何|怎么|方法|计划|步骤|最快|不痛苦).{0,20}(?:自杀|结束生命|割腕|上吊)"
            r"|(?:自杀|割腕|上吊|结束生命).{0,18}(?:方法|步骤|教程|不痛苦|最快)"
            r"|(?:教我|告诉我|计划|如何|怎么).{0,20}(?:杀死|谋杀|袭击|重伤).{0,16}(?:某人|同学|老师|家人|他|她|人)"
            r"|(?:how\s+to|best\s+way\s+to).{0,32}(?:kill\s+(?:myself|someone)|commit\s+suicide)"
        ),
    ),
    _Rule(
        SafetyCategory.SEXUAL_CONTENT,
        "critical",
        "sexual_exploitation_or_explicit_instruction",
        _compiled(
            r"(?:未成年|儿童|小学生|初中生).{0,20}(?:色情|裸照|性行为|成人视频)"
            r"|(?:色情|裸照|性行为|成人视频).{0,20}(?:未成年|儿童|小学生|初中生)"
            r"|(?:教我|如何|怎么|步骤|教程).{0,18}(?:制作|传播|偷拍).{0,12}(?:色情|裸照|成人视频)"
            r"|(?:child|minor).{0,16}(?:porn|sexual|nude)"
        ),
    ),
    _Rule(
        SafetyCategory.HATE_HARASSMENT,
        "high",
        "targeted_hate_or_dehumanization",
        _compiled(
            r"(?:把|应该|必须|希望).{0,18}(?:某民族|某种族|同性恋|残疾人|女性|男性|宗教群体)"
            r".{0,18}(?:杀光|赶尽杀绝|清除|低等|畜生|不配活)"
            r"|(?:kill|exterminate|deport).{0,20}(?:all\s+)?(?:jews|muslims|gays|women|disabled)"
        ),
    ),
    _Rule(
        SafetyCategory.PRIVACY_LEAKAGE,
        "high",
        "privacy_exfiltration_or_secret",
        _compiled(
            r"(?:人肉|开盒|doxx?).{0,28}(?:地址|电话|身份证|行踪|隐私|学校|住址)"
            r"|(?:获取|盗取|泄露|公开|查出).{0,28}(?:密码|令牌|token|api[ _-]?key|身份证号|家庭住址)"
            r"|(?:api[ _-]?key|access[ _-]?token|password|密码)\s*[:=：]\s*(?:sk-)?[a-z0-9_-]{20,}"
        ),
    ),
    _Rule(
        SafetyCategory.DANGEROUS_OPERATIONS,
        "high",
        "destructive_operation_instruction",
        _compiled(
            r"(?:执行|运行|复制执行|请给出|生成).{0,32}(?:rm\s+-rf\s+/(?:\s|$)|mkfs(?:\.|\s)|dd\s+if=|"
            r"drop\s+database\s+(?:prod|production|postgres)|关闭防火墙|禁用杀毒|删除所有备份)"
            r"|```(?:bash|sh|shell)?[^`]{0,80}(?:rm\s+-rf\s+/(?:\s|$)|mkfs(?:\.|\s))"
        ),
    ),
)


_SENSITIVE_TOPIC_RULES: tuple[_Rule, ...] = (
    _Rule(
        SafetyCategory.ILLEGAL_CRIME,
        "low",
        "sensitive_illegal_topic",
        _compiled(r"炸弹|爆炸物|毒品|勒索软件|洗钱|网络入侵"),
    ),
    _Rule(
        SafetyCategory.VIOLENCE_SELF_HARM,
        "low",
        "sensitive_violence_topic",
        _compiled(r"自杀|自伤|谋杀|校园暴力|枪击"),
    ),
    _Rule(
        SafetyCategory.SEXUAL_CONTENT,
        "low",
        "sensitive_sexual_topic",
        _compiled(r"色情|性骚扰|性教育|性侵"),
    ),
    _Rule(
        SafetyCategory.HATE_HARASSMENT,
        "low",
        "sensitive_hate_topic",
        _compiled(r"仇恨言论|种族歧视|性别歧视|网络霸凌"),
    ),
    _Rule(
        SafetyCategory.PRIVACY_LEAKAGE,
        "low",
        "sensitive_privacy_topic",
        _compiled(r"隐私泄露|身份证号|家庭住址|api[ _-]?key|access[ _-]?token"),
    ),
    _Rule(
        SafetyCategory.DANGEROUS_OPERATIONS,
        "low",
        "sensitive_operation_topic",
        _compiled(r"rm\s+-rf|mkfs|drop\s+database|关闭防火墙"),
    ),
)


_INPUT_BLOCK_MESSAGE = "该请求涉及高风险内容，无法继续处理。你可以改为讨论安全、合法的学习目标。"
_OUTPUT_BLOCK_MESSAGE = "本次生成内容未通过安全审核，已停止展示。请调整问题后重试。"


class ContentSafetyBlockedError(RuntimeError):
    def __init__(self, review: SafetyReview) -> None:
        self.review = review
        super().__init__(stable_block_message(review.direction))


def stable_block_message(direction: Literal["input", "output"]) -> str:
    return _INPUT_BLOCK_MESSAGE if direction == "input" else _OUTPUT_BLOCK_MESSAGE


class ContentSafetyService:
    def __init__(
        self,
        *,
        external_provider: DedicatedSafetyProvider | None = None,
        provider_configured: bool = False,
        audit_secret: str | None = None,
    ) -> None:
        self.external_provider = external_provider
        self.provider_configured = provider_configured or external_provider is not None
        self._audit_secret = (audit_secret or "content-safety-audit").encode("utf-8")

    @classmethod
    def from_settings(cls) -> "ContentSafetyService":
        provider_name = str(settings.CONTENT_SAFETY_PROVIDER or "local").strip().lower()
        provider: DedicatedSafetyProvider | None = None
        configured = provider_name != "local"
        if configured and settings.CONTENT_SAFETY_API_URL:
            provider = DedicatedHttpSafetyProvider(
                url=settings.CONTENT_SAFETY_API_URL,
                api_key=settings.CONTENT_SAFETY_API_KEY,
                timeout_seconds=settings.CONTENT_SAFETY_TIMEOUT_SECONDS,
            )
        elif configured:
            provider = _UnavailableConfiguredProvider()
        return cls(
            external_provider=provider,
            provider_configured=configured,
            audit_secret=settings.SECRET_KEY,
        )

    @property
    def buffers_entire_stream(self) -> bool:
        """External moderation needs the complete output before disclosure."""

        return self.provider_configured

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "").lower()
        return re.sub(r"[\t\r ]+", " ", normalized).strip()

    def _digest(self, text: str) -> str:
        return hmac.new(
            self._audit_secret,
            (text or "").encode("utf-8", errors="replace"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _local_findings(text: str) -> list[SafetyFinding]:
        normalized = ContentSafetyService._normalize(text)
        findings: list[SafetyFinding] = []
        high_categories: set[SafetyCategory] = set()
        for rule in _HIGH_RISK_RULES:
            if rule.pattern.search(normalized):
                findings.append(
                    SafetyFinding(
                        category=rule.category,
                        severity=rule.severity,
                        reason_code=rule.reason_code,
                    )
                )
                high_categories.add(rule.category)
        for rule in _SENSITIVE_TOPIC_RULES:
            if rule.category in high_categories:
                continue
            if rule.pattern.search(normalized):
                findings.append(
                    SafetyFinding(
                        category=rule.category,
                        severity=rule.severity,
                        reason_code=rule.reason_code,
                    )
                )
        return findings

    @staticmethod
    def _has_high_risk(findings: list[SafetyFinding]) -> bool:
        return any(item.severity in {"high", "critical"} for item in findings)

    @staticmethod
    def _safe_reason_code(value: str, fallback: str) -> str:
        candidate = (value or "").strip().lower()
        if re.fullmatch(r"[a-z0-9_.:-]{1,80}", candidate):
            return candidate
        return fallback

    @staticmethod
    def _deduplicate_findings(findings: list[SafetyFinding]) -> list[SafetyFinding]:
        out: list[SafetyFinding] = []
        seen: set[tuple[str, str]] = set()
        for item in findings:
            key = (item.category.value, item.reason_code)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def review(
        self,
        text: str,
        *,
        direction: Literal["input", "output"],
        use_external: bool = True,
    ) -> SafetyReview:
        started = time.perf_counter()
        raw = text or ""
        local_findings = self._local_findings(raw)
        all_findings = list(local_findings)
        high_risk = self._has_high_risk(local_findings)
        decision = SafetyDecision.BLOCK if high_risk else SafetyDecision.ALLOW
        reason = "local_high_risk_rule" if high_risk else (
            "local_sensitive_topic_allowed" if local_findings else "no_risk_signal"
        )
        provider = "local"
        external_available: bool | None = None

        if use_external and self.provider_configured:
            external_available = False
            provider = "local_fallback"
            try:
                if self.external_provider is None:
                    raise RuntimeError("moderation provider is unavailable")
                verdict = self.external_provider.review(raw, direction=direction)
                external_available = True
                provider = self.external_provider.name
                all_findings.extend(
                    SafetyFinding(
                        category=item.category,
                        severity=item.severity,
                        reason_code=self._safe_reason_code(
                            item.reason_code,
                            "provider_finding",
                        ),
                    )
                    for item in verdict.findings[:32]
                )
                for category in verdict.categories:
                    if not any(item.category == category for item in all_findings):
                        all_findings.append(
                            SafetyFinding(
                                category=category,
                                severity="high" if verdict.decision != SafetyDecision.ALLOW else "low",
                                reason_code="provider_category",
                            )
                        )
                # Automated paths cannot pause for a human reviewer, so a
                # provider `review` verdict is handled as fail-closed.
                if verdict.decision in {SafetyDecision.BLOCK, SafetyDecision.REVIEW}:
                    decision = SafetyDecision.BLOCK
                    reason = self._safe_reason_code(verdict.reason, "provider_block")
                elif high_risk:
                    decision = SafetyDecision.BLOCK
                    reason = "local_high_risk_rule"
                else:
                    decision = SafetyDecision.ALLOW
                    reason = self._safe_reason_code(verdict.reason, "provider_allow")
            except Exception as exc:
                # Never log the provider body or user/model content. The class
                # name is sufficient to diagnose provider health.
                logger.warning(
                    "content_safety_provider_unavailable provider=%s error_type=%s",
                    getattr(self.external_provider, "name", "unavailable"),
                    exc.__class__.__name__,
                )
                if high_risk:
                    decision = SafetyDecision.BLOCK
                    reason = "provider_unavailable_high_risk_fail_closed"
                else:
                    decision = SafetyDecision.ALLOW
                    reason = "provider_unavailable_low_risk_local_fallback"

        all_findings = self._deduplicate_findings(all_findings)
        categories = list(dict.fromkeys(item.category for item in all_findings))
        latency_ms = max(0, round((time.perf_counter() - started) * 1000))
        review = SafetyReview(
            audit_id=f"csr_{uuid4().hex}",
            direction=direction,
            decision=decision,
            categories=categories,
            reason=reason,
            provider=provider,
            latency_ms=latency_ms,
            content_digest=self._digest(raw),
            content_summary=f"chars={len(raw)};lines={raw.count(chr(10)) + 1 if raw else 0}",
            external_available=external_available,
            findings=all_findings,
        )
        logger.info(
            "content_safety_audit %s",
            json.dumps(
                {
                    "audit_id": review.audit_id,
                    "direction": review.direction,
                    "decision": review.decision.value,
                    "categories": [item.value for item in review.categories],
                    "reason": review.reason,
                    "provider": review.provider,
                    "latency_ms": review.latency_ms,
                    "content_digest": review.content_digest,
                    "content_summary": review.content_summary,
                },
                ensure_ascii=True,
                sort_keys=True,
            ),
        )
        return review

    def ensure_safe(
        self,
        text: str,
        *,
        direction: Literal["input", "output"],
        use_external: bool = True,
    ) -> SafetyReview:
        review = self.review(text, direction=direction, use_external=use_external)
        if review.blocked:
            raise ContentSafetyBlockedError(review)
        return review


class ContentSafetyStreamGuard:
    """Hold a look-behind window so unsafe output is blocked before disclosure."""

    def __init__(
        self,
        service: ContentSafetyService,
        *,
        tail_chars: int = 256,
    ) -> None:
        self.service = service
        self.tail_chars = max(128, tail_chars)
        self._pending = ""
        self._closed = False
        self.last_review: SafetyReview | None = None

    def push(self, text: str) -> str:
        if self._closed or not text:
            return ""
        self._pending += text
        # A dedicated external provider must see the complete model answer.
        if self.service.buffers_entire_stream:
            return ""
        self.last_review = self.service.ensure_safe(
            self._pending,
            direction="output",
            use_external=False,
        )
        if len(self._pending) <= self.tail_chars:
            return ""
        safe_prefix = self._pending[:-self.tail_chars]
        self._pending = self._pending[-self.tail_chars :]
        return safe_prefix

    def finish(self) -> str:
        if self._closed:
            return ""
        self._closed = True
        self.last_review = self.service.ensure_safe(
            self._pending,
            direction="output",
            use_external=True,
        )
        safe_tail = self._pending
        self._pending = ""
        return safe_tail


content_safety_service = ContentSafetyService.from_settings()

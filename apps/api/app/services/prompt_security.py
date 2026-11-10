import logging
import re
from typing import Optional, Tuple
from fastapi import HTTPException, status

from app.models.audit import SecurityIncidentType, SecurityIncidentSeverity
from app.services.audit import audit_service

logger = logging.getLogger(__name__)

# Heuristic patterns for prompt injection and jailbreak attacks
INJECTION_PATTERNS = [
    # 1. Instruction Overrides & Negations
    (
        "INSTRUCTION_OVERRIDE",
        re.compile(
            r"(?:ignore|disregard|forget|bypass|override|drop|discard|cancel)\s+(?:all\s+)?(?:previous|prior|above|existing|system|original)\s+(?:instructions|prompts|directives|rules|constraints|mandates)",
            re.IGNORECASE,
        ),
    ),
    (
        "INSTRUCTION_RESET",
        re.compile(
            r"(?:start\s+fresh|reset\s+all\s+instructions|clear\s+your\s+memory|new\s+operating\s+mode)",
            re.IGNORECASE,
        ),
    ),
    # 2. System Prompt & Directive Extraction
    (
        "SYSTEM_PROMPT_EXTRACTION",
        re.compile(
            r"(?:reveal|show|print|display|output|repeat|leak|dump|copy)\s+(?:the|your)?\s*(?:system|initial|core|base|hidden|confidential)\s*(?:prompt|instructions|directives|rules|parameters)",
            re.IGNORECASE,
        ),
    ),
    (
        "SYSTEM_PROMPT_QUERY",
        re.compile(
            r"what\s+(?:are|were)\s+your\s+(?:system\s+instructions|initial\s+instructions|system\s+prompt|core\s+directives)",
            re.IGNORECASE,
        ),
    ),
    # 3. Known Jailbreak Personas & Modes (DAN, Developer Mode, Unrestricted)
    (
        "DAN_JAILBREAK",
        re.compile(r"\bDAN\b|\bDo\s+Anything\s+Now\b", re.IGNORECASE),
    ),
    (
        "DEVELOPER_MODE_EXPLOIT",
        re.compile(
            r"(?:enable|enter|switch\s+to|activate|turn\s+on)\s+(?:developer|unrestricted|god|jailbreak|debug|jailbroken)\s+mode",
            re.IGNORECASE,
        ),
    ),
    (
        "UNRESTRICTED_ROLEPLAY",
        re.compile(
            r"(?:you\s+are\s+now|pretend\s+to\s+be|act\s+as|roleplay\s+as)\s+(?:an?\s+)?(?:unfiltered|unrestricted|unconstrained|evil|jailbroken|rogue)\s+(?:ai|assistant|model|bot|entity)",
            re.IGNORECASE,
        ),
    ),
    # 4. Delimiter Spoofing & Control Token Injection
    (
        "CONTROL_TOKEN_INJECTION",
        re.compile(
            r"(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|\[SYSTEM\s+INSTRUCTION\]|###\s*SYSTEM:?|```system)",
            re.IGNORECASE,
        ),
    ),
    # 5. Ethical & Safety Filter Bypasses
    (
        "SAFETY_BYPASS_ATTEMPT",
        re.compile(
            r"(?:disable|bypass|ignore|circumvent)\s+(?:safety|ethical|content|censorship|veritas)\s+(?:filters|guidelines|protocols|restrictions|abstention)",
            re.IGNORECASE,
        ),
    ),
]


class PromptSecurityService:
    """
    Native Prompt Injection & Jailbreak Defense Service (SEC-16).
    Scans raw user queries across Chat, Agent, and Analysis workflows.
    Rejects malicious prompts with HTTP 400 and logs HIGH severity incidents.
    """

    @staticmethod
    def scan_prompt(text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Scans query text for prompt injection patterns.
        Returns:
            (is_safe, violation_rule, matched_snippet)
        """
        if not text:
            return True, None, None

        for rule_name, pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                matched_snippet = match.group(0)
                logger.warning(
                    f"Prompt injection detected! Rule: {rule_name}, Snippet: '{matched_snippet}'"
                )
                return False, rule_name, matched_snippet

        return True, None, None

    @classmethod
    def validate_prompt_or_raise(
        cls,
        text: str,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint_context: str = "chat",
    ):
        """
        Validates prompt text. If an injection or jailbreak is detected:
        1. Asynchronously logs a HIGH severity SecurityIncidentLog.
        2. Raises HTTP 400 Bad Request with a clear security warning.
        """
        is_safe, rule_name, snippet = cls.scan_prompt(text)
        if not is_safe:
            # Immutable Security Incident Logging
            audit_service.log_security_incident(
                incident_type=SecurityIncidentType.PROMPT_INJECTION.value,
                severity=SecurityIncidentSeverity.HIGH.value,
                details={
                    "rule": rule_name,
                    "snippet": snippet,
                    "input_length": len(text),
                    "context": endpoint_context,
                },
                workspace_id=workspace_id,
                user_id=user_id,
                ip_address=ip_address,
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security Warning: Malicious prompt injection or jailbreak attempt detected ({rule_name}). This incident has been logged.",
            )


prompt_security_service = PromptSecurityService()

"""
Output validation for AI agent responses.

Protects against:
- Hallucinations
- PII leakage
- Inappropriate content
- Data exposure
- Low confidence responses
"""

import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum


class OutputSeverity(Enum):
    """Severity levels for output validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class OutputIssue:
    """Represents an issue found in output."""
    severity: OutputSeverity
    message: str
    category: str
    redacted_content: Optional[str] = None


@dataclass
class OutputValidationResult:
    """Result of output validation."""
    is_safe: bool
    sanitized_output: str
    issues: List[OutputIssue]
    confidence_score: float  # From the LLM or agent
    should_escalate: bool  # Whether to escalate to human review
    
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(issue.severity == OutputSeverity.CRITICAL for issue in self.issues)


class OutputValidator:
    """
    Validates and sanitizes AI agent outputs before returning to users.
    
    Features:
    - PII detection and redaction
    - Hallucination detection via confidence thresholds
    - Inappropriate content filtering
    - Data leakage prevention
    - Consistency checking
    """
    
    # PII patterns
    PII_PATTERNS = {
        'email': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
        'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',  # Generic API key pattern
        'password': r'(password|passwd|pwd)[\s:=]+[^\s]+',
    }
    
    # Internal data patterns (should never be exposed)
    INTERNAL_PATTERNS = {
        'database_id': r'\b(user_id|customer_id|internal_id)[\s:=]+\d+',
        'sql_query': r'\b(SELECT|INSERT|UPDATE|DELETE)\s+.*\s+FROM\s+',
        'file_path': r'[/\\][a-zA-Z0-9_\-./\\]+',
        'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    }
    
    # Inappropriate content keywords
    INAPPROPRIATE_KEYWORDS = [
        'hack', 'exploit', 'bypass', 'jailbreak',
        'illegal', 'fraud', 'scam',
    ]
    
    # Hallucination indicators
    HALLUCINATION_INDICATORS = [
        r'I (don\'t|do not) (have|know|remember)',
        r'I (cannot|can\'t) (access|retrieve|find)',
        r'(as an AI|as a language model)',
        r'I (apologize|sorry)',
    ]
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        redact_pii: bool = True,
        redact_internal_data: bool = True,
        strict_mode: bool = False
    ):
        """
        Initialize the output validator.
        
        Args:
            min_confidence: Minimum confidence score to accept output
            redact_pii: Whether to redact PII from outputs
            redact_internal_data: Whether to redact internal system data
            strict_mode: If True, be more aggressive with filtering
        """
        self.min_confidence = min_confidence
        self.redact_pii = redact_pii
        self.redact_internal_data = redact_internal_data
        self.strict_mode = strict_mode
    
    def validate(
        self,
        output: str,
        confidence: Optional[float] = None,
        context: Optional[Dict] = None
    ) -> OutputValidationResult:
        """
        Validate and sanitize AI output.
        
        Args:
            output: The raw output from the AI agent
            confidence: Confidence score from the agent (0.0 to 1.0)
            context: Optional context (e.g., user_tier, query_type)
        
        Returns:
            OutputValidationResult with validation status and sanitized output
        """
        issues: List[OutputIssue] = []
        sanitized = output
        should_escalate = False
        
        # Check confidence score
        if confidence is not None:
            if confidence < self.min_confidence:
                issues.append(OutputIssue(
                    severity=OutputSeverity.WARNING,
                    message=f"Low confidence score: {confidence:.2f}",
                    category="low_confidence"
                ))
                should_escalate = True
            
            # Very low confidence is critical
            if confidence < 0.3:
                issues.append(OutputIssue(
                    severity=OutputSeverity.CRITICAL,
                    message=f"Critically low confidence: {confidence:.2f}",
                    category="critical_low_confidence"
                ))
        
        # Check for hallucination indicators
        hallucination_found = False
        for pattern in self.HALLUCINATION_INDICATORS:
            if re.search(pattern, output, re.IGNORECASE):
                hallucination_found = True
                issues.append(OutputIssue(
                    severity=OutputSeverity.WARNING,
                    message="Potential hallucination detected",
                    category="hallucination"
                ))
                break
        
        # Check and redact PII
        if self.redact_pii:
            for pii_type, pattern in self.PII_PATTERNS.items():
                matches = list(re.finditer(pattern, sanitized, re.IGNORECASE))
                if matches:
                    for match in matches:
                        # Skip if it's the user's own email in context
                        if pii_type == 'email' and context and context.get('user_email') == match.group(0):
                            continue
                        
                        issues.append(OutputIssue(
                            severity=OutputSeverity.ERROR,
                            message=f"PII detected: {pii_type}",
                            category="pii_leakage",
                            redacted_content=match.group(0)
                        ))
                        
                        # Redact the PII
                        sanitized = sanitized.replace(
                            match.group(0),
                            f"[REDACTED_{pii_type.upper()}]"
                        )
        
        # Check and redact internal data
        if self.redact_internal_data:
            for data_type, pattern in self.INTERNAL_PATTERNS.items():
                matches = list(re.finditer(pattern, sanitized, re.IGNORECASE))
                if matches:
                    for match in matches:
                        issues.append(OutputIssue(
                            severity=OutputSeverity.CRITICAL,
                            message=f"Internal data exposure: {data_type}",
                            category="data_leakage",
                            redacted_content=match.group(0)[:50]
                        ))
                        
                        # Redact internal data
                        sanitized = sanitized.replace(
                            match.group(0),
                            f"[REDACTED_{data_type.upper()}]"
                        )
        
        # Check for inappropriate content
        output_lower = output.lower()
        for keyword in self.INAPPROPRIATE_KEYWORDS:
            if keyword in output_lower:
                issues.append(OutputIssue(
                    severity=OutputSeverity.WARNING,
                    message=f"Potentially inappropriate content: {keyword}",
                    category="inappropriate_content"
                ))
                if self.strict_mode:
                    should_escalate = True
        
        # Check output length (too short might indicate failure)
        if len(sanitized.strip()) < 10:
            issues.append(OutputIssue(
                severity=OutputSeverity.WARNING,
                message="Output is suspiciously short",
                category="short_output"
            ))
        
        # Check for empty or "None" outputs
        if not sanitized.strip() or sanitized.strip().lower() == "none":
            issues.append(OutputIssue(
                severity=OutputSeverity.ERROR,
                message="Output is empty or null",
                category="empty_output"
            ))
            sanitized = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
        
        # Determine if output is safe
        is_safe = not any(
            issue.severity in [OutputSeverity.CRITICAL, OutputSeverity.ERROR]
            for issue in issues
        )
        
        # In strict mode, warnings also make output unsafe
        if self.strict_mode:
            is_safe = is_safe and not any(
                issue.severity in [OutputSeverity.WARNING, OutputSeverity.ERROR]
                for issue in issues
            )
        
        # Escalate if we have critical issues or multiple errors
        error_count = sum(
            1 for issue in issues
            if issue.severity in [OutputSeverity.ERROR, OutputSeverity.CRITICAL]
        )
        if error_count >= 2:
            should_escalate = True
        
        return OutputValidationResult(
            is_safe=is_safe,
            sanitized_output=sanitized,
            issues=issues,
            confidence_score=confidence or 0.0,
            should_escalate=should_escalate
        )
    
    @staticmethod
    def redact_emails_except(text: str, allowed_emails: Set[str]) -> str:
        """
        Redact all emails except those in the allowed set.
        
        Args:
            text: Text containing emails
            allowed_emails: Set of emails that should not be redacted
        
        Returns:
            Text with unauthorized emails redacted
        """
        email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        
        def replace_email(match):
            email = match.group(0)
            if email in allowed_emails:
                return email
            return "[REDACTED_EMAIL]"
        
        return re.sub(email_pattern, replace_email, text)
    
    @staticmethod
    def create_safe_error_message(error: Exception, include_details: bool = False) -> str:
        """
        Create a safe error message that doesn't leak internal details.
        
        Args:
            error: The exception that occurred
            include_details: Whether to include error details (only for debugging)
        
        Returns:
            Safe error message for users
        """
        if include_details:
            return f"An error occurred: {str(error)}"
        else:
            return "I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists."


# Example usage and testing
if __name__ == "__main__":
    validator = OutputValidator(min_confidence=0.6)
    
    # Test cases
    test_outputs = [
        ("Your subscription has been updated successfully.", 0.95),
        ("I don't have access to that information.", 0.4),
        ("User email: user@example.com, ID: 12345", 0.8),
        ("Your API key is: abc123def456ghi789jkl012mno345pqr", 0.9),
        ("SELECT * FROM users WHERE id=1", 0.7),
        ("", 0.5),
    ]
    
    print("Output Validation Test Results:\n")
    for output, confidence in test_outputs:
        result = validator.validate(output, confidence)
        print(f"Output: {output[:60]}...")
        print(f"Confidence: {confidence:.2f}")
        print(f"Safe: {result.is_safe}")
        print(f"Should Escalate: {result.should_escalate}")
        print(f"Issues: {len(result.issues)}")
        for issue in result.issues:
            print(f"  - [{issue.severity.value}] {issue.message}")
        print(f"Sanitized: {result.sanitized_output[:60]}...")
        print()

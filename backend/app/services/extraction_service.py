import re
from typing import Dict, List, Optional


STOP_WORDS = {
    "what",
    "when",
    "where",
    "who",
    "whom",
    "which",
    "why",
    "how",
    "is",
    "are",
    "was",
    "were",
    "the",
    "a",
    "an",
    "does",
    "do",
    "did",
    "can",
    "could",
    "would",
    "should",
    "in",
    "on",
    "at",
    "of",
    "for",
    "to",
    "from",
    "with",
    "and",
    "or",
    "tell",
    "me",
    "about",
    "please",
    "provide",
    "give",
    "find",
    "show",
    "explain",
    "mentioned",
    "listed",
    "take",
    "place",
    "happen",
    "scheduled",
    "held",
    "event",
    "date",
    "day",
}


PATTERNS = {
    "date": re.compile(
        r"\b(?:"
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
        r"|\d{1,2}[- ]"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[- ]\d{4}"
        r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+\d{1,2},?\s+\d{4}"
        r"|\d{4}-\d{2}-\d{2}"
        r")\b",
        re.IGNORECASE,
    ),
    "amount": re.compile(
        r"(?:₹|Rs\.?|INR|USD|\$|€|£)\s*[\d,]+(?:\.\d{1,2})?"
        r"|[\d,]+(?:\.\d{1,2})?\s*(?:INR|USD|rupees|rupee)",
        re.IGNORECASE,
    ),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(
        r"(?<!\w)(?:\+?\d{1,3}[- ]?)?"
        r"(?:\d[- ]?){9,12}\d(?!\w)"
    ),
    "url": re.compile(
        r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
        re.IGNORECASE,
    ),
}


QUESTION_INTENTS = {
    "date": (
        "when",
        "date",
        "starts",
        "started",
        "deadline",
    ),
    "amount": (
        "fee",
        "fees",
        "cost",
        "price",
        "amount",
        "salary",
        "payment",
        "budget",
    ),
    "email": ("email", "mail", "contact"),
    "phone": ("phone", "mobile", "telephone", "contact number"),
    "url": ("website", "url", "link", "web address"),
}


def get_question_keywords(question: str) -> List[str]:
    """Extract meaningful keywords from the question."""

    words = re.findall(r"[a-zA-Z0-9]+", question.lower())

    return [word for word in words if word not in STOP_WORDS and len(word) > 1]


def detect_fact_type(question: str) -> Optional[str]:
    """Identify the requested fact type."""

    normalized = question.lower()

    # If the question already contains a date, it may be asking
    # what event occurs on that date, not asking for a date.
    if PATTERNS["date"].search(question):
        return None

    for fact_type, keywords in QUESTION_INTENTS.items():
        if any(
            re.search(r"\b" + re.escape(keyword) + r"\b", normalized)
            for keyword in keywords
        ):
            return fact_type

    return None


def find_matching_fact(
    question: str,
    chunks: List[Dict],
    window: int = 80,
) -> Optional[Dict]:
    """Extract facts according to the user's question intent."""

    fact_type = detect_fact_type(question)

    # Extract module/session facts only when the question
    # explicitly requests a supported schedule detail.
    if fact_type in ("date", "faculty", "topic", "time"):
        schedule_fact = extract_schedule_fact(
            question,
            chunks,
            fact_type=fact_type,
        )

        if schedule_fact:
            return schedule_fact

    # Continue with the existing generic fact extraction.
    if not fact_type:
        return None

    pattern = PATTERNS.get(fact_type)

    if not pattern:
        return None

    question_keywords = get_question_keywords(question)

    if not question_keywords:
        return None

    candidates = []

    for chunk in chunks:
        text = chunk.get("text", "")

        if not text:
            continue

        normalized_text = text.lower()
        keyword_positions = []

        for keyword in question_keywords:
            for keyword_match in re.finditer(
                r"\b" + re.escape(keyword) + r"\b",
                normalized_text,
            ):
                keyword_positions.append(keyword_match.start())

        if not keyword_positions:
            continue

        for match in pattern.finditer(text):
            fact_position = match.start()

            nearest_distance = min(
                abs(fact_position - position) for position in keyword_positions
            )

            if nearest_distance > window:
                continue

            candidates.append(
                {
                    "fact_type": fact_type,
                    "value": match.group(0),
                    "page_number": chunk.get("page_number"),
                    "similarity_score": chunk.get("similarity_score") or 0,
                    "context": text[
                        max(0, fact_position - window) : min(
                            len(text), fact_position + window
                        )
                    ].strip(),
                    "keyword_matches": 1,
                    "distance": nearest_distance,
                }
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            -item["keyword_matches"],
            item["distance"],
            -item["similarity_score"],
        )
    )

    return candidates[0]


SCHEDULE_DATE_PATTERN = re.compile(
    r"\b\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"[- ]\d{4}\b",
    re.IGNORECASE,
)


def extract_schedule_fact(
    question: str,
    chunks: List[Dict],
    fact_type: str = "date",
) -> Optional[Dict]:
    """
    Extract date, faculty, topic, or time for a specific
    module and session.
    """

    module_match = re.search(
        r"\bmodule\s*(\d+)\b",
        question,
        re.IGNORECASE,
    )

    session_match = re.search(
        r"\bsession\s*(\d+)\b",
        question,
        re.IGNORECASE,
    )

    if not module_match or not session_match:
        return None

    requested_module = int(module_match.group(1))
    requested_session = int(session_match.group(1))

    current_module = None

    faculty_pattern = re.compile(
        r"\b(?:"
        r"Prof(?:essor)?\.?\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*"
        r"|Wing\s+Cdr\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*"
        r"|Industry Expert"
        r"|SME from IITB"
        r")\b",
        re.IGNORECASE,
    )

    for chunk in chunks:
        text = chunk.get("text", "")

        if not text:
            continue

        date_matches = list(SCHEDULE_DATE_PATTERN.finditer(text))

        for index, date_match in enumerate(date_matches):
            segment_start = date_match.end()

            segment_end = (
                date_matches[index + 1].start()
                if index + 1 < len(date_matches)
                else len(text)
            )

            row_text = text[segment_start:segment_end]

            module_heading = re.search(
                r"\bModules?\s+(\d+)(?:\s*&\s*(\d+))?\s*:",
                row_text,
                re.IGNORECASE,
            )

            if module_heading:
                current_module = int(module_heading.group(1))

            session_heading = re.search(
                r"\bSession\s+(\d+)\b",
                row_text,
                re.IGNORECASE,
            )

            if not session_heading:
                continue

            session_number = int(session_heading.group(1))

            if (
                current_module != requested_module
                or session_number != requested_session
            ):
                continue

            value = None

            if fact_type == "date":
                value = date_match.group(0)

            elif fact_type == "faculty":
                faculty_match = faculty_pattern.search(row_text)

                if faculty_match:
                    value = faculty_match.group(0)

            elif fact_type == "time":
                time_match = re.search(
                    r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b",
                    row_text,
                    re.IGNORECASE,
                )

                if time_match:
                    value = time_match.group(0)

            elif fact_type == "topic":
                # Topic extraction needs a reliable session-row
                # boundary and should not guess from nearby text.
                return None

            if not value:
                return None

            return {
                "fact_type": fact_type,
                "value": value,
                "page_number": chunk.get("page_number"),
                "similarity_score": chunk.get("similarity_score"),
                "context": row_text.strip(),
            }

    return None

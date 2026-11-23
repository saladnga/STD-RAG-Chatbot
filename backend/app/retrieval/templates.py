"""
Strict no-hallucination prompt templates for RAG.
Ensures the model only uses information from retrieved context.
Includes citation formatting and no-answer mode handling.
"""
from typing import Optional

from prompts import load as load_prompt

# ============================================================================
# SYSTEM PROMPT - Answer Only From Context
# ============================================================================
RAG_SYSTEM_PROMPT = load_prompt("rag_answer_system")

# ============================================================================
# USER PROMPT TEMPLATE
# ============================================================================
RAG_USER_PROMPT_TEMPLATE = load_prompt("rag_answer_user")

# ============================================================================
# NO-ANSWER RESPONSE TEMPLATES
# ============================================================================
NO_ANSWER_RESPONSES = [
    "I don't have enough information in the provided documents to answer this question.",
    "The provided documents do not contain sufficient information to answer this question.",
    "I cannot answer this question based on the information available in the uploaded documents.",
    "The uploaded documents do not cover the information needed to answer this question."
]

DEFAULT_NO_ANSWER_RESPONSE = NO_ANSWER_RESPONSES[0]

# ============================================================================
# CITATION FORMATTING
# ============================================================================
CITATION_FORMAT = "[Source: {source}, Chunk: {chunk_index}]"
CITATION_FORMAT_WITH_RELEVANCE = "[Source: {source}, Chunk: {chunk_index}, Relevance: {relevance:.2f}]"

# Citation patterns for extraction
CITATION_PATTERN_SIMPLE = r"\[Source:\s*([^,]+),\s*Chunk:\s*(\d+)\]"
CITATION_PATTERN_WITH_RELEVANCE = r"\[Source:\s*([^,]+),\s*Chunk:\s*(\d+)(?:,\s*Relevance:\s*([\d.]+))?\]"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_rag_prompt_template() -> str:
    """Get the RAG user prompt template."""
    return RAG_USER_PROMPT_TEMPLATE


def get_system_prompt() -> str:
    """Get the system prompt for no-hallucination enforcement."""
    return RAG_SYSTEM_PROMPT


def format_rag_prompt(context: str, question: str) -> str:
    """Format the RAG prompt with context and question."""
    return RAG_USER_PROMPT_TEMPLATE.format(context=context, question=question)


def format_citation(
    source: str, 
    chunk_index: int, 
    relevance: Optional[float] = None
) -> str:
    """
    Format a citation for inclusion in the answer.
    Args:
    - source: Source document filename
    - chunk_index: Chunk index number
    - relevance: Optional relevance score
    Returns:
    - Formatted citation string
    """
    if relevance is not None:
        return CITATION_FORMAT_WITH_RELEVANCE.format(
            source=source,
            chunk_index=chunk_index,
            relevance=relevance
        )
    return CITATION_FORMAT.format(source=source, chunk_index=chunk_index)


def get_no_answer_response(variant: int = 0) -> str:
    """
    Get a no-answer response text.
    Args:
    - variant: Which variant to use (0-3)
    Returns:
    - No-answer response text
    """
    if 0 <= variant < len(NO_ANSWER_RESPONSES):
        return NO_ANSWER_RESPONSES[variant]
    return DEFAULT_NO_ANSWER_RESPONSE


def is_no_answer_response(text: str) -> bool:
    """
    Check if a response is a no-answer response.
    Args:
    - text: Response text to check
    Returns:
    - True if the text is a no-answer response
    """
    text_lower = text.lower().strip()
    
    # Check for exact matches
    for no_answer in NO_ANSWER_RESPONSES:
        if no_answer.lower().strip() == text_lower:
            return True
    
    # Check for key phrases
    no_answer_indicators = [
        "don't have enough information",
        "do not contain sufficient information",
        "cannot answer this question",
        "do not cover the information",
        "not enough information",
        "don't know",
        "cannot answer",
        "unclear from the context",
        "not available in the",
        "not found in the"
    ]
    
    return any(indicator in text_lower for indicator in no_answer_indicators)


def extract_citations_from_text(text: str) -> list:
    """
    Extract citations from answer text.
    Args:
    - text: Answer text containing citations
    Returns:
    - List of citation dictionaries with source and chunk_index
    """
    import re
    
    citations = []
    
    # Try pattern with relevance first
    matches = re.finditer(CITATION_PATTERN_WITH_RELEVANCE, text, re.IGNORECASE)
    for match in matches:
        source = match.group(1).strip()
        chunk_index = int(match.group(2))
        relevance = float(match.group(3)) if match.group(3) else None
        
        citations.append({
            "source": source,
            "chunk_index": chunk_index,
            "relevance": relevance,
            "full_match": match.group(0)
        })
    
    # Also try simple pattern for citations without relevance
    if not citations:
        matches = re.finditer(CITATION_PATTERN_SIMPLE, text, re.IGNORECASE)
        for match in matches:
            source = match.group(1).strip()
            chunk_index = int(match.group(2))
            
            # Avoid duplicates
            if not any(c["source"] == source and c["chunk_index"] == chunk_index for c in citations):
                citations.append({
                    "source": source,
                    "chunk_index": chunk_index,
                    "relevance": None,
                    "full_match": match.group(0)
                })
    
    return citations


def validate_answer_has_citations(text: str, min_citations: int = 1) -> bool:
    """
    Validate that an answer contains the required number of citations.
    Args:
    - text: Answer text
    - min_citations: Minimum number of citations required
    Returns:
    - True if answer has sufficient citations
    """
    citations = extract_citations_from_text(text)
    return len(citations) >= min_citations


def enhance_prompt_with_examples(
    base_prompt: str,
    include_citation_examples: bool = True,
    include_no_answer_example: bool = True
) -> str:
    """
    Enhance a prompt with examples of good answers.
    Args:
    - base_prompt: Base prompt template
    - include_citation_examples: Whether to include citation examples
    - include_no_answer_example: Whether to include no-answer example
    Returns:
    - Enhanced prompt with examples
    """
    examples = []
    
    if include_citation_examples:
        examples.append(
            """
            EXAMPLE OF GOOD ANSWER WITH CITATIONS:
            Question: What are the treatment options for chlamydia?
            Answer: According to the medical documents, chlamydia is typically treated with antibiotics. The recommended treatments include doxycycline or azithromycin [Source: medical_guide.pdf, Chunk: 15]. Treatment should be completed as prescribed, and sexual partners should also be treated [Source: medical_guide.pdf, Chunk: 16].
            """
        )
    
    if include_no_answer_example:
        examples.append(
            """
            EXAMPLE OF NO-ANSWER RESPONSE:
            Question: What is the recommended dosage for experimental drug XYZ?
            Answer: I don't have enough information in the provided documents to answer this question.
            """
        )
    
    if examples:
        examples_text = "\n".join(examples)
        return base_prompt + "\n\n" + examples_text
    
    return base_prompt

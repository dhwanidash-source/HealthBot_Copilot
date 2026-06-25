import re

def universal_tag_cleaner(text: str) -> str:
    """
    Strips internal agent tags, thoughts, and routing markers from LLM output.
    """
    if not text:
        return text

    # 1.DESTROY INTERNAL THOUGHT BLOCKS (XML/HTML Style)
    # Removes things like <think>...</think>, <scratchpad>...</scratchpad> completely.
    # We use re.DOTALL to ensure it deletes everything even if it spans multiple lines.
    text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Removes any standalone XML tags like <system_note> or </end>
    text = re.sub(r'<[^>]+>', '', text)

    # 2. EXTRACT DATA FROM KEY-VALUE BRACKETS
    # Transforms [NEXT_QUESTION: How are you?] -> How are you?
    # Transforms [CLINIC_NAME: City Med] -> City Med
    # The [A-Z_]+ ensures it only targets system tags (all caps with underscores).
    text = re.sub(r'\[[A-Z_]+:\s*([\s\S]*?)\]', r'\1', text)

    # 3. DESTROY STANDALONE BRACKET TAGS
    # Removes things like [CLINICAL_DIAGNOSIS], [SYSTEM_PROMPT], [END_OF_TURN]
    text = re.sub(r'\[[A-Z_]+\]', '', text)

    # 4. CLEAN UP FORMATTING
    # Removing tags often leaves behind ugly double spaces or triple line breaks.
    # This compresses multiple blank lines down to a maximum of two.
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()
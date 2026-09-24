"""Resolve model-selected spans back to exact server-owned text."""


def exact_support(text: str, proposed: str) -> str | None:
    if len(proposed.strip()) < 4:
        return None
    if proposed in text:
        return proposed
    # Only layout whitespace is normalized during lookup. The returned evidence is
    # always an exact slice of the stored version; words and punctuation cannot change.
    offsets = [i for i, char in enumerate(text) if not char.isspace()]
    compact = ''.join(text[i] for i in offsets)
    wanted = ''.join(char for char in proposed if not char.isspace())
    index = compact.find(wanted)
    if len(wanted) < 4 or index < 0:
        return None
    return text[offsets[index]:offsets[index + len(wanted) - 1] + 1]

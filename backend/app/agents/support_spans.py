"""Resolve model-selected spans back to exact server-owned text."""

import re


def evidence_spans(text: str) -> list[dict]:
    # Contiguous, server-owned slices; multiple selections remain separate.
    pieces = [match.group().strip() for match in re.finditer(r'[^\r\n。！？；]+[。！？；]?', text)]
    return [{'span_id': i, 'text': value} for i, value in enumerate(p for p in pieces if p)]


def selection_scope(evidence) -> list[dict]:
    """Keep the applicability selector's scope separate from complete originals."""
    return [{'citation_id': e.source.citation_id, 'role': e.role,
             'answer_span_ids': [span for span in e.support_span_ids if span not in e.context_span_ids],
             'context_span_ids': list(e.context_span_ids)}
            for e in evidence if e.role in {'direct', 'supporting'}]


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

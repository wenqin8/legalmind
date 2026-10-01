"""Limit a partial semantic repair to the sentences that failed validation."""

import json
import re

from app.agents.grounding import sentence_units
from app.core.errors import ModelUnavailableError


def repair_scope(paragraph, feedback):
    units = sentence_units(paragraph)
    ids = {item.get('unit_id') for item in feedback}
    if not ids or any(type(index) is not int or not 0 <= index < len(units) for index in ids):
        return []
    if len(ids) == len(units):
        return []
    return [{'unit_id': index, 'text': units[index]} for index in sorted(ids)]


def apply_sentence_repairs(paragraph, scope, response):
    try:
        data = json.loads(response)
        if not isinstance(data, dict) or set(data) != {'replacements'} or not isinstance(data['replacements'], list):
            raise ValueError('Invalid sentence repair')
        replacements = {}
        for item in data['replacements']:
            if not isinstance(item, dict) or set(item) != {'unit_id', 'text'}:
                raise ValueError('Invalid replacement')
            index, text = item['unit_id'], item['text']
            if type(index) is not int or index in replacements or not isinstance(text, str):
                raise ValueError('Invalid replacement type or duplicate')
            # A semicolon joins clauses within one replacement sentence. Each
            # clause still becomes an audit unit in the full revalidation.
            # A canonical citation after terminal punctuation is metadata, not
            # an extra sentence. Ordinary citation validation still follows.
            without_citations = re.sub(r'\[S[1-5]\]', '', text)
            sentences = [part for part in re.split(r'(?<=[。！？])', without_citations) if part.strip()]
            if not text.strip() or len(text) > 2000 or '\n' in text or '\r' in text or len(sentences) != 1:
                raise ValueError('Replacement must remain one sentence')
            replacements[index] = text.strip()
        if set(replacements) != {item['unit_id'] for item in scope}:
            raise ValueError('Repair scope changed')
        pieces, cursor = [], 0
        for index, original in enumerate(sentence_units(paragraph)):
            position = paragraph.index(original, cursor)
            pieces.extend([paragraph[cursor:position], replacements.get(index, original)])
            cursor = position + len(original)
        return ''.join([*pieces, paragraph[cursor:]])
    except (ValueError, TypeError, KeyError) as exc:
        raise ModelUnavailableError() from exc

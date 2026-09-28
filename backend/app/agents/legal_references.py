"""Describe statutory cross-references without inventing their missing contents."""

import re

from app.agents.evidence import Evidence

REFERENCE = re.compile(r'(民法典|劳动合同法|本解释|本法)(第[一二三四五六七八九十百千万零〇\d]+条)')


def reference_context(evidence: list[Evidence]) -> list[dict]:
    result = []
    for item in evidence:
        if item.source.source_type != 'legal_provision':
            continue
        for name, article in dict.fromkeys(REFERENCE.findall(item.text)):
            title = item.source.title if name in {'本法', '本解释'} else '中华人民共和国' + name
            matches = [e for e in evidence if e.source.title == title and e.source.reference_number == article]
            target = matches[0].source.citation_id if len(matches) == 1 else None
            result.append({'from_citation': item.source.citation_id, 'reference': name + article,
                           'target_citation': target, 'status': 'provided' if target else 'not_provided'})
    return result


def normalize_cross_references(text: str, evidence: list[Evidence]) -> str:
    """Resolve only cross-references actually present in the selected originals.

    This changes an identifier, never its surrounding legal assertion. The result
    still requires citation and semantic audits. Unknown identifiers stay visible
    to the rejecting validator; a missing provision never becomes a source.
    """
    known = {item['reference'] for item in reference_context(evidence)}
    return REFERENCE.sub(lambda match: '该依据援引的条款' if match.group() in known else match.group(), text)


REFERENCE_RULE = (
    'reference_context由服务端解析原文交叉引用。provided表示对应原文已在本轮提供，可用target_citation核对具体条件；'
    'not_provided表示仅知道存在该引用，不能补出该条的内容或结果。'
    '编号本身不等于实质条件；在本条已明确条件、转述未改变法律含义时，不仅因未复写编号而否定。'
    '若判断还依赖缺失条文的具体内容，应明确该部分依据不足，保留本条独立说明的规则；不扩写该缺失条文。'
)

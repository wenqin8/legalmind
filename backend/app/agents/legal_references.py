"""Describe statutory cross-references without inventing their missing contents."""

import re

from app.agents.evidence import Evidence

REFERENCE = re.compile(r'(民法典|劳动合同法|本解释|本法)(第[一二三四五六七八九十百千万零〇\d]+条)')
SECTION_REFERENCE = re.compile(r'(?:本法|本解释)((?:第[一二三四五六七八九十百千万零〇\d]+[编章节])+)')


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
    context = reference_context(evidence)
    # Models may omit the statute name. Only originals with an explicit
    # cross-reference can supply an alias; unknown identifiers stay rejected.
    aliases = {}
    for index, item in enumerate(context, 1):
        article = REFERENCE.fullmatch(item['reference']).group(2)
        replacement = ('本轮已提供的配套条款' if item['status'] == 'provided'
                       else '该依据援引的条款（被引用全文本轮未提供）') + f'（配套引用{index}）'
        name, _ = REFERENCE.fullmatch(item['reference']).groups()
        owner = next(e.source.title for e in evidence if e.source.citation_id == item['from_citation'])
        identity = (owner if name in {'本法', '本解释'} else name, article, item['target_citation'])
        for alias in (item['reference'], article):
            # Equal missing/provided status does not make different statutes
            # or targets interchangeable. Bare ambiguous aliases stay rejected.
            aliases.setdefault(alias, {}).setdefault(identity, replacement)
    for item in evidence:
        if item.source.source_type == 'legal_provision':
            for match in SECTION_REFERENCE.finditer(item.text):
                for alias in (match.group(), match.group(1)):
                    aliases.setdefault(alias, {})[(item.source.title, match.group())] = (
                        '该依据援引的条款（被引用全文本轮未提供）')
    for reference in sorted(aliases, key=len, reverse=True):
        replacements = aliases[reference]
        if len(replacements) != 1:
            continue  # Ambiguous cross-statute aliases cannot invent identity.
        text = text.replace(reference, next(iter(replacements.values())))
    return text


REFERENCE_RULE = (
    'reference_context由服务端解析原文交叉引用。provided表示对应原文已在本轮提供，可用target_citation核对具体条件；'
    'not_provided表示仅知道存在该引用，不能补出该条的内容或结果。'
    '原条文已提供不等于它援引的其他条文全文已提供；不得把not_provided的被引用全文缺口误判为来源原条文缺失。'
    '编号本身不等于实质条件；在本条已明确条件、转述未改变法律含义时，不仅因未复写编号而否定。'
    '按reference_context的顺序使用配套引用1、配套引用2等定位交叉条文，每个标识只对应该项引用；标识不是新来源或条文全文。'
    '若拒绝理由是被援引条号没有重复，先区分引用定位与实质条件：必须指出给定原文中具体缺失的主体、行为、前提或例外，不能把条号本身当成新增前提。'
    'not_provided也不能推定缺失条文一定有某项附加条件；但候选扩写缺失条文的具体内容或依其断定结果时，仍应拒绝。'
    '若判断还依赖缺失条文的具体内容，应明确该部分依据不足，保留本条独立说明的规则；不扩写该缺失条文。'
)

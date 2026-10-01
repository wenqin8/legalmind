"""Preserve an observed omitted limitation as exact, server-owned source text.

This is a narrow completeness guard, not proof of general answer correctness.
It cannot validate or rescue a contradictory main claim.
"""

import re

from app.core.errors import ModelUnavailableError
from app.agents.legal_references import reference_context


def missing_cross_reference_notice(rendered, evidence):
    """Display a server-verified material gap without guessing legal effects."""
    if '该依据援引的条款' not in rendered:
        return ''
    used = set(re.findall(r'\[(S[1-5])\]', rendered))
    labels = dict.fromkeys(item['from_citation'] for item in reference_context(evidence)
                          if item['status'] == 'not_provided' and item['from_citation'] in used)
    if not labels:
        return ''
    return '\n\n资料边界\n' + '\n'.join(
        f'[{label}] 本轮所选该依据的原文还引用了其他条文，其中有被引用条文的完整内容未提供；'
        '依赖这些缺失内容的具体后果，本次不作判断。' for label in labels)


def omitted_limitation_notice(rendered, evidence):
    if not ('违约金' in rendered and '减少' in rendered) or '恶意违约' in rendered:
        return ''
    notices = []
    for item in evidence:
        if item.source.source_type != 'legal_provision':
            continue
        for match in re.finditer(r'(?:^|[。\n])(恶意违约[^。\n]*请求减少违约金[^。\n]*一般不予支持。)', item.text):
            quote = match[1]
            if not item.source.original_text or quote not in item.source.original_text:
                raise ModelUnavailableError()
            notices.append(f'[{item.source.citation_id}] 原文同时规定：{quote}')
    if not notices:
        return ''
    return '\n\n风险补充\n' + '\n'.join(notices) + '\n该限制是否涉及本次个案，仍需核实具体事实。'

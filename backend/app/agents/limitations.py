"""Preserve an observed omitted limitation as exact, server-owned source text.

This is a narrow completeness guard, not proof of general answer correctness.
It cannot validate or rescue a contradictory main claim.
"""

import re

from app.core.errors import ModelUnavailableError


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

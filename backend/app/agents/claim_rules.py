"""Small, explicit counterexamples that must not depend on model agreement.

These guards cover observed logical errors, not general legal entailment. The
ordinary two semantic audits remain mandatory for every other generated claim.
"""

import re


def deterministic_rejections(units, evidence):
    rejected = []
    for index, unit in enumerate(units):
        labels = set(re.findall(r'\[(S[1-5])\]', unit))
        scoped = [e for e in evidence if e.source.citation_id in labels] if labels else evidence
        originals = '\n'.join(e.text for e in scoped)
        optional_opinion = '可以参照' in originals and '意见' in originals
        enumerated_property = '下列财产' in originals and re.search(r'夫妻(?:的)?共同财产', originals)
        # Check individual clauses, so a disclaimer elsewhere cannot conceal a
        # contradictory mandatory requirement. Negative examples remain allowed.
        reason = None
        for clause in re.split(r'[。；]', unit):
            if optional_opinion and '意见' in clause:
                strengthened = re.search(r'(取决于|只有|必须|必备|前提是)', clause)
                if strengthened:
                    prefix = clause[max(0, strengthened.start() - 8):strengthened.start()]
                    denied = re.search(r'(?:不|并非|不是|不能说|不意味着|不等于|不得认定为|不能改写成)[“「\s]*$', prefix)
                    if not denied:
                        reason = '原文仅允许参照意见，不得把取得该意见写成必要条件；保留原文的可选性质。'
            if enumerated_property and re.search(
                r'共同财产.{0,4}(?:以|是|为).{0,6}婚姻关系存续期间.{0,4}所得.{0,4}(?:范围|财产|共同)', clause
            ) and not any(word in clause for word in ('下列', '列举', '并非', '不是', '不等于')):
                reason = '原文限定为列举的财产类型并有例外，不能概括为婚姻期间所有所得；请保留列举范围和例外或不作该概括。'
        if reason:
            rejected.append({'unit_id': index, 'text': unit, 'explanation': reason})
    return rejected

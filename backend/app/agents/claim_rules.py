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
        conditional_refund = ('有前款规定情形' in originals and
                              '返还已支付的社会保险费补偿' in originals)
        nutrition_reference = '营养费根据受害人伤残情况参照医疗机构的意见确定' in re.sub(r'\s+', '', originals)
        # Check individual clauses, so a disclaimer elsewhere cannot conceal a
        # contradictory mandatory requirement. Negative examples remain allowed.
        reason = None
        for clause in re.split(r'[。；]', unit):
            if nutrition_reference and '意见' in clause:
                unnecessary = re.search(r'(?:不是|并非).{0,18}(?:必要条件|必备)|无需|无须|不需要|不必', clause)
                uncertain = any(word in clause for word in ('不能据此认定', '不能认定', '不能推出', '无法确定', '不作判断'))
                if unnecessary and not uncertain:
                    reason = ('原文仅规定营养费根据伤残情况参照医疗机构意见确定，未规定该意见不是必要条件。'
                              '不要从“参照”推导“无需意见也可获得赔偿”，仅保留原文明示规则；'
                              '是否需要其他证明材料，本次不作判断。')
            if conditional_refund and re.search(r'返还.*(?:社会保险|社保).*补偿', clause):
                linked = re.search(r'(?:前款|上述|前述).{0,24}(?:情形|条件|前提)', clause)
                nonconclusion = any(word in clause for word in ('不能仅', '不作判断', '无法判断', '不能确定'))
                if not linked and not nonconclusion:
                    reason = ('返还社保补偿的原文以“有前款规定情形”为前提，不能缩写为只要补缴即可返还。'
                              '本句须明确保留“有前款规定情形”并承接前文规则，或说明本次不作判断；'
                              '不得自行推断前款各情形的且/或者关系，仍需保留依法补缴、请求和已支付等条件。')
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

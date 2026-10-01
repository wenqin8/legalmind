"""Small, explicit counterexamples that must not depend on model agreement.

These guards cover observed logical errors, not general legal entailment. The
ordinary two semantic audits remain mandatory for every other generated claim.
"""

import re


def deterministic_rejections(units, evidence):
    rejected = []
    all_originals = '\n'.join(e.text for e in evidence)
    paragraph = ''.join(units)
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
            gift_scope = ('一方父母全额出资' in originals and '赠与合同' in originals
                          and '没有约定或者约定不明确' in originals)
            if (gift_scope and re.search(r'未.{0,8}约定.{0,4}只.{0,6}(?:自己|子女|一方)', clause)
                    and re.search(r'判决|房屋归|补偿', clause)):
                reason = ('父母出资购房的该分支限定为赠与合同没有约定或者约定不明确。'
                          '不能改成未明确约定只赠与自己子女，这会包含明确赠与双方等原文未覆盖情况；'
                          '必须恢复原文明示的赠与合同条件，并保留婚姻关系存续期间、一方父母全额出资、离婚分割共同财产等前提。')
            invalidity_scope = '合同存在无效或者可撤销的情形' in originals
            if (invalidity_scope and re.search(r'备案|批准|变更登记|移转登记', clause)
                    and '不予支持' in clause
                    and not re.search(r'合同.{0,8}(?:无效.{0,6}可撤销|可撤销.{0,6}无效)', paragraph)):
                reason = ('备案、批准或登记不能支持有效主张的该规则，以合同存在无效或者可撤销的情形为前提。'
                          '必须在本句明确保留这一前提，不能变成所有已经备案、批准或登记的合同有效主张都不予支持。')
            # A quoted, explicitly missing topic must not contradict another
            # selected source. Scope-only statements and genuine gaps stay valid.
            gap = re.search(r'(?:资料|材料|原文).{0,6}(?:未提供|未包含|未展开|没有).{0,4}[“「]([^”」]{4,40})[”」]', clause)
            if gap and gap.group(1) in all_originals:
                reason = '本轮完整证据已经包含所称缺失的规则，不得虚构资料缺口；可说明本次不展开该争点，但不能说资料未提供。'
            life_needs = ('确因生活需要进行交易' in originals and '不应当认定合同无效' in originals)
            if (life_needs and re.search(r'国家安全|社会公共秩序|善良风俗', clause)
                    and re.search(r'认定|无效|审查', clause)
                    and not all(term in paragraph for term in ('生活需要', '重大影响', '不影响国家安全', '不违背善良风俗'))):
                reason = ('列举公序良俗无效情形时须同时保留同条例外：当事人确因生活需要进行交易，'
                          '未给社会公共秩序造成重大影响，且不影响国家安全，也不违背善良风俗的，不应认定合同无效。'
                          '不能以另句不作判断代替该例外；完整保留全部例外条件并使用一个句子。'
                          '若本句列举无效情形，不只保留国家安全、公共秩序、善良风俗三个概称：'
                          '同时保留政治安全、经济安全、军事安全等国家安全；社会稳定、公平竞争秩序或者损害社会公共利益；'
                          '社会公德、家庭伦理或者有损人格尊严等原文明示范围，不作新的效力推论。')
            if nutrition_reference and '意见' in clause:
                unnecessary = re.search(r'(?:不是|并非).{0,18}(?:必要条件|必备)|无需|无须|不需要|不必', clause)
                mandatory = re.search(r'(?:不是|并非|而非).{0,8}可有可无', clause)
                uncertain = any(word in clause for word in ('不能据此认定', '不能认定', '不能推出', '无法确定', '不作判断'))
                if (unnecessary or mandatory) and not uncertain:
                    reason = ('原文仅规定营养费根据伤残情况参照医疗机构意见确定，未明确该意见的必要性。'
                              '不要从“参照”推导“无需意见也可获得赔偿”或“该意见并非可有可无”，仅保留原文明示规则；'
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
            property_claim = re.search(
                r'共同财产.{0,4}(?:以|是|为|包括).{0,6}婚姻关系存续期间.{0,6}所得.{0,4}(?:范围|财产|共同)'
                r'|婚姻关系存续期间所得的(?:相关|全部|所有)?财产(?:均|都)?(?:为|是|属于)夫妻(?:的)?共同财产', clause
            ) if enumerated_property else None
            if property_claim:
                prefix = clause[max(0, property_claim.start() - 10):property_claim.start()]
                denied = re.search(r'(?:不能(?:说|认为|认定)|不得(?:说|认为|认定))[“「\s]*$', prefix)
                limited = any(word in property_claim.group() for word in ('下列', '列举', '并非', '不是', '不等于'))
                if not denied and not limited:
                    reason = '原文限定为列举的财产类型并有例外，不能概括为婚姻期间所有所得；请保留列举范围和例外或不作该概括。'
        if reason:
            rejected.append({'unit_id': index, 'text': unit, 'explanation': reason})
    return rejected

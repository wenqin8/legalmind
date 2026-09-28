# RAG 端到端复核

本报告从原始36场景输出离线复算，不重新调用模型、不修改冻结标签。
结构校验与开发代理语义复核分别记录；尚无法律专家审核，不给出法律正确率认证。

## 自动化指标

```json
{
  "planned_turns": 52,
  "http_successes": 1,
  "scenario_structural_passes": 1,
  "expected_answer_behavior_counts": {
    "answer": 1,
    "service_error": 27
  },
  "behavior_match_including_errors": {
    "value": 0.019230769230769232,
    "denominator": 52
  },
  "answerable_but_insufficient_rate": {
    "value": 0.0,
    "denominator": 28
  },
  "answerable_but_clarifying_rate": {
    "value": 0.0,
    "denominator": 28
  },
  "hard_check_failures": {
    "source_integrity": 0,
    "known_citations": 0,
    "verbatim_quotes": 0,
    "no_model_urls": 0,
    "version_interval": 0,
    "field_provenance": 0,
    "conflict_preserved": 0,
    "confirmed_field": 0
  },
  "candidate_hit_on_expected_answers": {
    "value": 0.03571428571428571,
    "denominator": 28
  },
  "candidate_recall_on_expected_answers": {
    "value": 0.03571428571428571,
    "denominator": 28
  },
  "selected_hit_on_expected_answers": {
    "value": 0.03571428571428571,
    "denominator": 28
  },
  "selected_recall_on_expected_answers": {
    "value": 0.03571428571428571,
    "denominator": 28
  },
  "returned_hit_on_expected_answers": {
    "value": 0.03571428571428571,
    "denominator": 28
  },
  "returned_recall_on_expected_answers": {
    "value": 0.03571428571428571,
    "denominator": 28
  },
  "by_domain": {
    "contract_dispute": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 0.0,
        "denominator": 13
      },
      "http_successes": 0
    },
    "labor_dispute": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 0.0,
        "denominator": 13
      },
      "http_successes": 0
    },
    "marriage_family": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 0.07692307692307693,
        "denominator": 13
      },
      "http_successes": 1
    },
    "traffic_accident": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 0.0,
        "denominator": 13
      },
      "http_successes": 0
    }
  },
  "source_recall_by_grade": {
    "3": {
      "candidate": {
        "macro_recall": 0.03571428571428571,
        "turns_with_grade": 28,
        "matched_sources": 1,
        "gold_sources": 29
      },
      "selected": {
        "macro_recall": 0.03571428571428571,
        "turns_with_grade": 28,
        "matched_sources": 1,
        "gold_sources": 29
      },
      "returned": {
        "macro_recall": 0.03571428571428571,
        "turns_with_grade": 28,
        "matched_sources": 1,
        "gold_sources": 29
      }
    },
    "2": {
      "candidate": {
        "macro_recall": 0.05263157894736842,
        "turns_with_grade": 19,
        "matched_sources": 1,
        "gold_sources": 23
      },
      "selected": {
        "macro_recall": 0.05263157894736842,
        "turns_with_grade": 19,
        "matched_sources": 1,
        "gold_sources": 23
      },
      "returned": {
        "macro_recall": 0.05263157894736842,
        "turns_with_grade": 19,
        "matched_sources": 1,
        "gold_sources": 23
      }
    },
    "1": {
      "candidate": {
        "macro_recall": 0.1111111111111111,
        "turns_with_grade": 9,
        "matched_sources": 1,
        "gold_sources": 10
      },
      "selected": {
        "macro_recall": 0.1111111111111111,
        "turns_with_grade": 9,
        "matched_sources": 1,
        "gold_sources": 10
      },
      "returned": {
        "macro_recall": 0.1111111111111111,
        "turns_with_grade": 9,
        "matched_sources": 1,
        "gold_sources": 10
      }
    }
  }
}
```

## 逐场景复核

### E-L-MF-01

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-MF-02

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-MF-03

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-MF-04

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-MF-05

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-MF-06

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 conflict；实际 dependency_failed；未通过项：无。
- 第 3 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-MF-12

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-MF-13

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 cancelled；实际 dependency_failed；未通过项：无。

### E-L-MF-14

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-LD-01

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-LD-02

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-LD-03

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-LD-04

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-LD-05

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-LD-06

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 conflict；实际 dependency_failed；未通过项：无。
- 第 3 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-LD-12

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-LD-13

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 cancelled；实际 dependency_failed；未通过项：无。

### E-L-LD-14

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-TA-01

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-TA-02

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-TA-03

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-TA-04

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-TA-05

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-TA-06

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 conflict；实际 dependency_failed；未通过项：无。
- 第 3 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-TA-12

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-TA-13

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 cancelled；实际 dependency_failed；未通过项：无。

### E-L-TA-14

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-01

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-02

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-03

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-04

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-05

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-CD-06

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 conflict；实际 dependency_failed；未通过项：无。
- 第 3 轮：预期 answer；实际 dependency_failed；未通过项：无。

### E-L-CD-12

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-13

- 第 1 轮：预期 clarify；实际 MODEL_UNAVAILABLE；未通过项：无。
- 第 2 轮：预期 cancelled；实际 dependency_failed；未通过项：无。

### E-L-CD-14

- 第 1 轮：预期 insufficient；实际 MODEL_UNAVAILABLE；未通过项：无。

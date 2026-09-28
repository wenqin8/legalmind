# RAG 端到端复核

本报告从原始36场景输出离线复算，不重新调用模型、不修改冻结标签。
结构校验与开发代理语义复核分别记录；尚无法律专家审核，不给出法律正确率认证。

## 自动化指标

```json
{
  "planned_turns": 52,
  "http_successes": 51,
  "scenario_structural_passes": 35,
  "expected_answer_behavior_counts": {
    "answer": 27,
    "service_error": 1
  },
  "behavior_match_including_errors": {
    "value": 0.9807692307692307,
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
    "value": 1.0,
    "denominator": 28
  },
  "candidate_recall_on_expected_answers": {
    "value": 0.9196428571428571,
    "denominator": 28
  },
  "selected_hit_on_expected_answers": {
    "value": 1.0,
    "denominator": 28
  },
  "selected_recall_on_expected_answers": {
    "value": 0.8839285714285714,
    "denominator": 28
  },
  "returned_hit_on_expected_answers": {
    "value": 0.9642857142857143,
    "denominator": 28
  },
  "returned_recall_on_expected_answers": {
    "value": 0.8482142857142857,
    "denominator": 28
  },
  "by_domain": {
    "contract_dispute": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 1.0,
        "denominator": 13
      },
      "http_successes": 13
    },
    "labor_dispute": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 0.9230769230769231,
        "denominator": 13
      },
      "http_successes": 12
    },
    "marriage_family": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 1.0,
        "denominator": 13
      },
      "http_successes": 13
    },
    "traffic_accident": {
      "turns": 13,
      "behavior_match_including_errors": {
        "value": 1.0,
        "denominator": 13
      },
      "http_successes": 13
    }
  },
  "source_recall_by_grade": {
    "3": {
      "candidate": {
        "macro_recall": 1.0,
        "turns_with_grade": 28,
        "matched_sources": 29,
        "gold_sources": 29
      },
      "selected": {
        "macro_recall": 1.0,
        "turns_with_grade": 28,
        "matched_sources": 29,
        "gold_sources": 29
      },
      "returned": {
        "macro_recall": 0.9642857142857143,
        "turns_with_grade": 28,
        "matched_sources": 28,
        "gold_sources": 29
      }
    },
    "2": {
      "candidate": {
        "macro_recall": 0.8157894736842105,
        "turns_with_grade": 19,
        "matched_sources": 19,
        "gold_sources": 23
      },
      "selected": {
        "macro_recall": 0.7894736842105263,
        "turns_with_grade": 19,
        "matched_sources": 18,
        "gold_sources": 23
      },
      "returned": {
        "macro_recall": 0.7368421052631579,
        "turns_with_grade": 19,
        "matched_sources": 17,
        "gold_sources": 23
      }
    },
    "1": {
      "candidate": {
        "macro_recall": 0.7222222222222222,
        "turns_with_grade": 9,
        "matched_sources": 7,
        "gold_sources": 10
      },
      "selected": {
        "macro_recall": 0.5,
        "turns_with_grade": 9,
        "matched_sources": 5,
        "gold_sources": 10
      },
      "returned": {
        "macro_recall": 0.3888888888888889,
        "turns_with_grade": 9,
        "matched_sources": 4,
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

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-MF-03

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-MF-04

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-MF-05

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 answer；实际 answer；未通过项：无。

### E-L-MF-06

- 第 1 轮：预期 answer；实际 answer；未通过项：无。
- 第 2 轮：预期 conflict；实际 conflict；未通过项：无。
- 第 3 轮：预期 answer；实际 answer；未通过项：无。

### E-L-MF-12

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

### E-L-MF-13

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 cancelled；实际 cancelled；未通过项：无。

### E-L-MF-14

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

### E-L-LD-01

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-LD-02

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-LD-03

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-LD-04

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-LD-05

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 answer；实际 answer；未通过项：无。

### E-L-LD-06

- 第 1 轮：预期 answer；实际 answer；未通过项：无。
- 第 2 轮：预期 conflict；实际 conflict；未通过项：无。
- 第 3 轮：预期 answer；实际 answer；未通过项：无。

### E-L-LD-12

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

### E-L-LD-13

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 cancelled；实际 cancelled；未通过项：无。

### E-L-LD-14

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

### E-L-TA-01

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-TA-02

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-TA-03

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-TA-04

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-TA-05

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 answer；实际 answer；未通过项：无。

### E-L-TA-06

- 第 1 轮：预期 answer；实际 answer；未通过项：无。
- 第 2 轮：预期 conflict；实际 conflict；未通过项：无。
- 第 3 轮：预期 answer；实际 answer；未通过项：无。

### E-L-TA-12

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

### E-L-TA-13

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 cancelled；实际 cancelled；未通过项：无。

### E-L-TA-14

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

### E-L-CD-01

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-CD-02

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-CD-03

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-CD-04

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-CD-05

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 answer；实际 answer；未通过项：无。

### E-L-CD-06

- 第 1 轮：预期 answer；实际 answer；未通过项：无。
- 第 2 轮：预期 conflict；实际 conflict；未通过项：无。
- 第 3 轮：预期 answer；实际 answer；未通过项：无。

### E-L-CD-12

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

### E-L-CD-13

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 cancelled；实际 cancelled；未通过项：无。

### E-L-CD-14

- 第 1 轮：预期 insufficient；实际 insufficient；未通过项：无。

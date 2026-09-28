# RAG 端到端复核

本报告从原始6场景输出离线复算，不重新调用模型、不修改冻结标签。
结构校验与开发代理语义复核分别记录；尚无法律专家审核，不给出法律正确率认证。

## 自动化指标

```json
{
  "planned_turns": 9,
  "http_successes": 7,
  "scenario_structural_passes": 4,
  "expected_answer_behavior_counts": {
    "answer": 5,
    "service_error": 2
  },
  "behavior_match_including_errors": {
    "value": 0.7777777777777778,
    "denominator": 9
  },
  "answerable_but_insufficient_rate": {
    "value": 0.0,
    "denominator": 7
  },
  "answerable_but_clarifying_rate": {
    "value": 0.0,
    "denominator": 7
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
    "denominator": 7
  },
  "candidate_recall_on_expected_answers": {
    "value": 0.8095238095238095,
    "denominator": 7
  },
  "selected_hit_on_expected_answers": {
    "value": 0.7142857142857143,
    "denominator": 7
  },
  "selected_recall_on_expected_answers": {
    "value": 0.5238095238095238,
    "denominator": 7
  },
  "returned_hit_on_expected_answers": {
    "value": 0.7142857142857143,
    "denominator": 7
  },
  "returned_recall_on_expected_answers": {
    "value": 0.5238095238095238,
    "denominator": 7
  },
  "by_domain": {
    "contract_dispute": {
      "turns": 4,
      "behavior_match_including_errors": {
        "value": 0.75,
        "denominator": 4
      },
      "http_successes": 3
    },
    "labor_dispute": {
      "turns": 1,
      "behavior_match_including_errors": {
        "value": 1.0,
        "denominator": 1
      },
      "http_successes": 1
    },
    "marriage_family": {
      "turns": 3,
      "behavior_match_including_errors": {
        "value": 1.0,
        "denominator": 3
      },
      "http_successes": 3
    },
    "traffic_accident": {
      "turns": 1,
      "behavior_match_including_errors": {
        "value": 0.0,
        "denominator": 1
      },
      "http_successes": 0
    }
  },
  "source_recall_by_grade": {
    "3": {
      "candidate": {
        "macro_recall": 1.0,
        "turns_with_grade": 7,
        "matched_sources": 7,
        "gold_sources": 7
      },
      "selected": {
        "macro_recall": 0.7142857142857143,
        "turns_with_grade": 7,
        "matched_sources": 5,
        "gold_sources": 7
      },
      "returned": {
        "macro_recall": 0.7142857142857143,
        "turns_with_grade": 7,
        "matched_sources": 5,
        "gold_sources": 7
      }
    },
    "2": {
      "candidate": {
        "macro_recall": 0.6,
        "turns_with_grade": 5,
        "matched_sources": 5,
        "gold_sources": 7
      },
      "selected": {
        "macro_recall": 0.4,
        "turns_with_grade": 5,
        "matched_sources": 4,
        "gold_sources": 7
      },
      "returned": {
        "macro_recall": 0.4,
        "turns_with_grade": 5,
        "matched_sources": 4,
        "gold_sources": 7
      }
    },
    "1": {
      "candidate": {
        "macro_recall": 0.3333333333333333,
        "turns_with_grade": 3,
        "matched_sources": 1,
        "gold_sources": 3
      },
      "selected": {
        "macro_recall": 0.3333333333333333,
        "turns_with_grade": 3,
        "matched_sources": 1,
        "gold_sources": 3
      },
      "returned": {
        "macro_recall": 0.3333333333333333,
        "turns_with_grade": 3,
        "matched_sources": 1,
        "gold_sources": 3
      }
    }
  }
}
```

## 逐场景复核

### E-L-MF-04

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-MF-05

- 第 1 轮：预期 clarify；实际 clarify；未通过项：无。
- 第 2 轮：预期 answer；实际 answer；未通过项：无。

### E-L-LD-03

- 第 1 轮：预期 answer；实际 answer；未通过项：无。

### E-L-TA-03

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-02

- 第 1 轮：预期 answer；实际 MODEL_UNAVAILABLE；未通过项：无。

### E-L-CD-06

- 第 1 轮：预期 answer；实际 answer；未通过项：无。
- 第 2 轮：预期 conflict；实际 conflict；未通过项：无。
- 第 3 轮：预期 answer；实际 answer；未通过项：无。

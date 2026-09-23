# RAG-v1 检索基线

相关性为固定语料内的开发代理标注草案，未经法律专家复核。空标签题不进入 Recall/MRR/NDCG 分母。

| 分组 | 题数 | Hit@5 | Recall@5 | Precision@5 | MRR@5 | NDCG@5 | 无答案误召回率 | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| case_bm25 | 80 | 0.984 | 0.977 | 0.165 | 0.905 | 0.919 | 1.000 | 5.5 |
| case_bm25/split/development | 60 | 0.979 | 0.969 | 0.167 | 0.899 | 0.912 | 1.000 | 5.6 |
| case_bm25/split/holdout | 20 | 1.000 | 1.000 | 0.160 | 0.922 | 0.941 | 1.000 | 5.1 |
| case_bm25/domain/contract_dispute | 20 | 0.938 | 0.938 | 0.160 | 0.849 | 0.873 | 1.000 | 5.0 |
| case_bm25/domain/labor_dispute | 20 | 1.000 | 1.000 | 0.170 | 0.922 | 0.941 | 1.000 | 5.5 |
| case_bm25/domain/marriage_family | 20 | 1.000 | 0.969 | 0.160 | 0.911 | 0.909 | 1.000 | 5.9 |
| case_bm25/domain/traffic_accident | 20 | 1.000 | 1.000 | 0.170 | 0.938 | 0.954 | 1.000 | 5.0 |
| case_bm25/category/multi_evidence | 4 | 1.000 | 0.875 | 0.350 | 0.833 | 0.789 | N/A | 5.0 |
| case_bm25/category/paraphrase | 60 | 0.983 | 0.983 | 0.197 | 0.910 | 0.928 | N/A | 5.6 |
| case_bm25/category/uncovered_topic | 16 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 4.9 |
| case_hybrid | 80 | 1.000 | 0.992 | 0.168 | 0.956 | 0.961 | 1.000 | 15.7 |
| case_hybrid/split/development | 60 | 1.000 | 0.990 | 0.170 | 0.965 | 0.966 | 1.000 | 15.8 |
| case_hybrid/split/holdout | 20 | 1.000 | 1.000 | 0.160 | 0.927 | 0.946 | 1.000 | 15.1 |
| case_hybrid/domain/contract_dispute | 20 | 1.000 | 1.000 | 0.170 | 0.927 | 0.946 | 1.000 | 15.1 |
| case_hybrid/domain/labor_dispute | 20 | 1.000 | 1.000 | 0.170 | 0.969 | 0.977 | 1.000 | 15.4 |
| case_hybrid/domain/marriage_family | 20 | 1.000 | 0.969 | 0.160 | 1.000 | 0.976 | 1.000 | 17.2 |
| case_hybrid/domain/traffic_accident | 20 | 1.000 | 1.000 | 0.170 | 0.927 | 0.946 | 1.000 | 14.6 |
| case_hybrid/category/multi_evidence | 4 | 1.000 | 0.875 | 0.350 | 1.000 | 0.903 | N/A | 14.6 |
| case_hybrid/category/paraphrase | 60 | 1.000 | 1.000 | 0.200 | 0.953 | 0.965 | N/A | 15.8 |
| case_hybrid/category/uncovered_topic | 16 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 14.4 |
| case_vector | 80 | 1.000 | 1.000 | 0.170 | 0.964 | 0.970 | 1.000 | 10.2 |
| case_vector/split/development | 60 | 1.000 | 1.000 | 0.173 | 0.979 | 0.981 | 1.000 | 10.2 |
| case_vector/split/holdout | 20 | 1.000 | 1.000 | 0.160 | 0.917 | 0.938 | 1.000 | 10.1 |
| case_vector/domain/contract_dispute | 20 | 1.000 | 1.000 | 0.170 | 1.000 | 0.995 | 1.000 | 10.1 |
| case_vector/domain/labor_dispute | 20 | 1.000 | 1.000 | 0.170 | 0.969 | 0.977 | 1.000 | 10.1 |
| case_vector/domain/marriage_family | 20 | 1.000 | 1.000 | 0.170 | 0.969 | 0.972 | 1.000 | 11.2 |
| case_vector/domain/traffic_accident | 20 | 1.000 | 1.000 | 0.170 | 0.917 | 0.938 | 1.000 | 10.0 |
| case_vector/category/multi_evidence | 4 | 1.000 | 1.000 | 0.400 | 1.000 | 0.960 | N/A | 9.8 |
| case_vector/category/paraphrase | 60 | 1.000 | 1.000 | 0.200 | 0.961 | 0.971 | N/A | 10.4 |
| case_vector/category/uncovered_topic | 16 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 9.7 |
| law_bm25 | 80 | 0.929 | 0.762 | 0.200 | 0.884 | 0.811 | 0.208 | 12.9 |
| law_bm25/split/development | 60 | 0.932 | 0.769 | 0.213 | 0.898 | 0.834 | 0.250 | 12.8 |
| law_bm25/split/holdout | 20 | 0.917 | 0.739 | 0.160 | 0.833 | 0.727 | 0.125 | 13.1 |
| law_bm25/domain/contract_dispute | 20 | 1.000 | 0.917 | 0.290 | 0.964 | 0.945 | 0.000 | 13.1 |
| law_bm25/domain/labor_dispute | 20 | 0.929 | 0.833 | 0.180 | 0.893 | 0.795 | 0.167 | 10.1 |
| law_bm25/domain/marriage_family | 20 | 0.929 | 0.750 | 0.170 | 0.893 | 0.841 | 0.167 | 9.8 |
| law_bm25/domain/traffic_accident | 20 | 0.857 | 0.550 | 0.160 | 0.786 | 0.663 | 0.500 | 7.8 |
| law_bm25/category/answerable | 19 | 0.947 | 0.947 | 0.189 | 0.921 | 0.928 | N/A | 13.1 |
| law_bm25/category/historical_uncovered | 4 | N/A | N/A | 0.000 | N/A | N/A | 0.000 | 6.7 |
| law_bm25/category/knowledge_gap | 8 | N/A | N/A | 0.000 | N/A | N/A | 0.500 | 12.6 |
| law_bm25/category/missing_date | 8 | N/A | N/A | 0.000 | N/A | N/A | 0.000 | 0.0 |
| law_bm25/category/multi_evidence | 37 | 0.919 | 0.668 | 0.335 | 0.865 | 0.751 | N/A | 12.8 |
| law_bm25/category/out_of_scope | 4 | N/A | N/A | 0.000 | N/A | N/A | 0.250 | 11.8 |

Precision@K 分母固定为 K，缺少返回项不补分；无答案题的正例排序指标为空。每项指标的精确分母见 JSON。
版本匹配率仅检查固定元数据的日期区间，不证明司法解释过渡适用正确。案例路线不作日期版本判分。
计时不含资料导入、建索引和权重加载；记录本机顺序查询耗时，首次查询可能包含缓存开销。不是并发负载测试。未调节检索参数。

## 失败明细

- `C-MF-14` / case_bm25: 相关资料未全部进入 Top-5
- `C-MF-14` / case_hybrid: 相关资料未全部进入 Top-5
- `C-MF-N1` / case_vector: 无答案题返回候选
- `C-MF-N1` / case_bm25: 无答案题返回候选
- `C-MF-N1` / case_hybrid: 无答案题返回候选
- `C-MF-N2` / case_vector: 无答案题返回候选
- `C-MF-N2` / case_bm25: 无答案题返回候选
- `C-MF-N2` / case_hybrid: 无答案题返回候选
- `C-MF-N3` / case_vector: 无答案题返回候选
- `C-MF-N3` / case_bm25: 无答案题返回候选
- `C-MF-N3` / case_hybrid: 无答案题返回候选
- `C-MF-N4` / case_vector: 无答案题返回候选
- `C-MF-N4` / case_bm25: 无答案题返回候选
- `C-MF-N4` / case_hybrid: 无答案题返回候选
- `C-LD-N1` / case_vector: 无答案题返回候选
- `C-LD-N1` / case_bm25: 无答案题返回候选
- `C-LD-N1` / case_hybrid: 无答案题返回候选
- `C-LD-N2` / case_vector: 无答案题返回候选
- `C-LD-N2` / case_bm25: 无答案题返回候选
- `C-LD-N2` / case_hybrid: 无答案题返回候选
- `C-LD-N3` / case_vector: 无答案题返回候选
- `C-LD-N3` / case_bm25: 无答案题返回候选
- `C-LD-N3` / case_hybrid: 无答案题返回候选
- `C-LD-N4` / case_vector: 无答案题返回候选
- `C-LD-N4` / case_bm25: 无答案题返回候选
- `C-LD-N4` / case_hybrid: 无答案题返回候选
- `C-TA-N1` / case_vector: 无答案题返回候选
- `C-TA-N1` / case_bm25: 无答案题返回候选
- `C-TA-N1` / case_hybrid: 无答案题返回候选
- `C-TA-N2` / case_vector: 无答案题返回候选
- `C-TA-N2` / case_bm25: 无答案题返回候选
- `C-TA-N2` / case_hybrid: 无答案题返回候选
- `C-TA-N3` / case_vector: 无答案题返回候选
- `C-TA-N3` / case_bm25: 无答案题返回候选
- `C-TA-N3` / case_hybrid: 无答案题返回候选
- `C-TA-N4` / case_vector: 无答案题返回候选
- `C-TA-N4` / case_bm25: 无答案题返回候选
- `C-TA-N4` / case_hybrid: 无答案题返回候选
- `C-CD-12` / case_bm25: 相关资料未全部进入 Top-5
- `C-CD-N1` / case_vector: 无答案题返回候选
- `C-CD-N1` / case_bm25: 无答案题返回候选
- `C-CD-N1` / case_hybrid: 无答案题返回候选
- `C-CD-N2` / case_vector: 无答案题返回候选
- `C-CD-N2` / case_bm25: 无答案题返回候选
- `C-CD-N2` / case_hybrid: 无答案题返回候选
- `C-CD-N3` / case_vector: 无答案题返回候选
- `C-CD-N3` / case_bm25: 无答案题返回候选
- `C-CD-N3` / case_hybrid: 无答案题返回候选
- `C-CD-N4` / case_vector: 无答案题返回候选
- `C-CD-N4` / case_bm25: 无答案题返回候选
- `C-CD-N4` / case_hybrid: 无答案题返回候选
- `L-MF-01` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-03` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-04` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-07` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-08` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-12` / law_bm25: 无答案题返回候选
- `L-MF-17` / law_bm25: 相关资料未全部进入 Top-5
- `L-LD-01` / law_bm25: 相关资料未全部进入 Top-5
- `L-LD-03` / law_bm25: 相关资料未全部进入 Top-5
- `L-LD-09` / law_bm25: 相关资料未全部进入 Top-5
- `L-LD-12` / law_bm25: 无答案题返回候选
- `L-LD-17` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-03` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-04` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-06` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-07` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-08` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-09` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-11` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-12` / law_bm25: 无答案题返回候选
- `L-TA-15` / law_bm25: 无答案题返回候选
- `L-TA-16` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-17` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-18` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-20` / law_bm25: 无答案题返回候选
- `L-CD-01` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-05` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-06` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-11` / law_bm25: 相关资料未全部进入 Top-5

以上是基线发现，不通过改标签或重跑挑选较好成绩消除失败。

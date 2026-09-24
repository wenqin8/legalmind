# RAG-v1 检索基线

相关性为固定语料内的开发代理标注草案，未经法律专家复核。空标签题不进入 Recall/MRR/NDCG 分母。

| 分组 | 题数 | Hit@5 | Recall@5 | Precision@5 | MRR@5 | NDCG@5 | 无答案误召回率 | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| case_bm25 | 60 | 0.979 | 0.969 | 0.167 | 0.899 | 0.912 | 1.000 | 6.5 |
| case_bm25/split/development | 60 | 0.979 | 0.969 | 0.167 | 0.899 | 0.912 | 1.000 | 6.5 |
| case_bm25/domain/contract_dispute | 15 | 0.917 | 0.917 | 0.160 | 0.799 | 0.831 | 1.000 | 6.6 |
| case_bm25/domain/labor_dispute | 15 | 1.000 | 1.000 | 0.173 | 0.896 | 0.922 | 1.000 | 5.1 |
| case_bm25/domain/marriage_family | 15 | 1.000 | 0.958 | 0.160 | 0.944 | 0.926 | 1.000 | 7.0 |
| case_bm25/domain/traffic_accident | 15 | 1.000 | 1.000 | 0.173 | 0.958 | 0.969 | 1.000 | 5.4 |
| case_bm25/category/multi_evidence | 4 | 1.000 | 0.875 | 0.350 | 0.833 | 0.789 | N/A | 6.7 |
| case_bm25/category/paraphrase | 44 | 0.977 | 0.977 | 0.195 | 0.905 | 0.923 | N/A | 6.4 |
| case_bm25/category/uncovered_topic | 12 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 5.2 |
| case_hybrid | 60 | 1.000 | 0.990 | 0.170 | 0.965 | 0.966 | 1.000 | 17.0 |
| case_hybrid/split/development | 60 | 1.000 | 0.990 | 0.170 | 0.965 | 0.966 | 1.000 | 17.0 |
| case_hybrid/domain/contract_dispute | 15 | 1.000 | 1.000 | 0.173 | 0.903 | 0.928 | 1.000 | 17.1 |
| case_hybrid/domain/labor_dispute | 15 | 1.000 | 1.000 | 0.173 | 0.958 | 0.969 | 1.000 | 16.0 |
| case_hybrid/domain/marriage_family | 15 | 1.000 | 0.958 | 0.160 | 1.000 | 0.968 | 1.000 | 17.9 |
| case_hybrid/domain/traffic_accident | 15 | 1.000 | 1.000 | 0.173 | 1.000 | 1.000 | 1.000 | 15.6 |
| case_hybrid/category/multi_evidence | 4 | 1.000 | 0.875 | 0.350 | 1.000 | 0.903 | N/A | 17.3 |
| case_hybrid/category/paraphrase | 44 | 1.000 | 1.000 | 0.200 | 0.962 | 0.972 | N/A | 16.9 |
| case_hybrid/category/uncovered_topic | 12 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 14.7 |
| case_vector | 60 | 1.000 | 1.000 | 0.173 | 0.979 | 0.981 | 1.000 | 11.1 |
| case_vector/split/development | 60 | 1.000 | 1.000 | 0.173 | 0.979 | 0.981 | 1.000 | 11.1 |
| case_vector/domain/contract_dispute | 15 | 1.000 | 1.000 | 0.173 | 1.000 | 0.993 | 1.000 | 11.2 |
| case_vector/domain/labor_dispute | 15 | 1.000 | 1.000 | 0.173 | 0.958 | 0.969 | 1.000 | 10.9 |
| case_vector/domain/marriage_family | 15 | 1.000 | 1.000 | 0.173 | 0.958 | 0.963 | 1.000 | 10.9 |
| case_vector/domain/traffic_accident | 15 | 1.000 | 1.000 | 0.173 | 1.000 | 1.000 | 1.000 | 10.5 |
| case_vector/category/multi_evidence | 4 | 1.000 | 1.000 | 0.400 | 1.000 | 0.960 | N/A | 10.9 |
| case_vector/category/paraphrase | 44 | 1.000 | 1.000 | 0.200 | 0.977 | 0.983 | N/A | 11.1 |
| case_vector/category/uncovered_topic | 12 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 9.5 |
| law_bm25 | 60 | 1.000 | 0.873 | 0.240 | 0.966 | 0.922 | 0.500 | 16.3 |
| law_bm25/split/development | 60 | 1.000 | 0.873 | 0.240 | 0.966 | 0.922 | 0.500 | 16.3 |
| law_bm25/domain/contract_dispute | 15 | 1.000 | 0.871 | 0.307 | 0.955 | 0.918 | 0.500 | 18.0 |
| law_bm25/domain/labor_dispute | 15 | 1.000 | 0.955 | 0.213 | 0.955 | 0.941 | 0.500 | 11.2 |
| law_bm25/domain/marriage_family | 15 | 1.000 | 0.803 | 0.187 | 0.955 | 0.901 | 0.500 | 12.3 |
| law_bm25/domain/traffic_accident | 15 | 1.000 | 0.864 | 0.253 | 1.000 | 0.927 | 0.500 | 9.0 |
| law_bm25/category/answerable | 16 | 1.000 | 1.000 | 0.200 | 0.969 | 0.977 | N/A | 17.6 |
| law_bm25/category/historical_uncovered | 4 | N/A | N/A | 0.000 | N/A | N/A | 0.000 | 8.2 |
| law_bm25/category/knowledge_gap | 4 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 15.5 |
| law_bm25/category/missing_date | 4 | N/A | N/A | 0.000 | N/A | N/A | 0.000 | 0.0 |
| law_bm25/category/multi_evidence | 28 | 1.000 | 0.801 | 0.400 | 0.964 | 0.891 | N/A | 15.9 |
| law_bm25/category/out_of_scope | 4 | N/A | N/A | 0.000 | N/A | N/A | 1.000 | 13.8 |

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
- `C-LD-N1` / case_vector: 无答案题返回候选
- `C-LD-N1` / case_bm25: 无答案题返回候选
- `C-LD-N1` / case_hybrid: 无答案题返回候选
- `C-LD-N2` / case_vector: 无答案题返回候选
- `C-LD-N2` / case_bm25: 无答案题返回候选
- `C-LD-N2` / case_hybrid: 无答案题返回候选
- `C-LD-N3` / case_vector: 无答案题返回候选
- `C-LD-N3` / case_bm25: 无答案题返回候选
- `C-LD-N3` / case_hybrid: 无答案题返回候选
- `C-TA-N1` / case_vector: 无答案题返回候选
- `C-TA-N1` / case_bm25: 无答案题返回候选
- `C-TA-N1` / case_hybrid: 无答案题返回候选
- `C-TA-N2` / case_vector: 无答案题返回候选
- `C-TA-N2` / case_bm25: 无答案题返回候选
- `C-TA-N2` / case_hybrid: 无答案题返回候选
- `C-TA-N3` / case_vector: 无答案题返回候选
- `C-TA-N3` / case_bm25: 无答案题返回候选
- `C-TA-N3` / case_hybrid: 无答案题返回候选
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
- `L-MF-01` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-03` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-04` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-08` / law_bm25: 相关资料未全部进入 Top-5
- `L-MF-12` / law_bm25: 无答案题返回候选
- `L-MF-15` / law_bm25: 无答案题返回候选
- `L-LD-03` / law_bm25: 相关资料未全部进入 Top-5
- `L-LD-12` / law_bm25: 无答案题返回候选
- `L-LD-15` / law_bm25: 无答案题返回候选
- `L-TA-03` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-09` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-11` / law_bm25: 相关资料未全部进入 Top-5
- `L-TA-12` / law_bm25: 无答案题返回候选
- `L-TA-15` / law_bm25: 无答案题返回候选
- `L-CD-01` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-03` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-05` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-06` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-11` / law_bm25: 相关资料未全部进入 Top-5
- `L-CD-12` / law_bm25: 无答案题返回候选
- `L-CD-15` / law_bm25: 无答案题返回候选

以上是基线发现，不通过改标签或重跑挑选较好成绩消除失败。

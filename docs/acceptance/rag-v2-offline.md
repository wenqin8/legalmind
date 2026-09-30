# RAG验证方法

以下命令在`backend`目录执行，输出路径必须尚不存在。日常使用离线回归；最新结论和证据见[最终验收](rag-v2-final-acceptance.md)。

## 离线回归

无需真实模型额度或Redis。测试使用假模型、假Redis和隔离数据库，不修改默认数据。

```powershell
# 相关回归和60条法条开发查询
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite quick --output ../tmp/offline-quick-new.json

# 全部测试和120条开发查询（案例三路检索+法条检索）
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite full --include-vectors --output ../tmp/offline-full-new.json

# 附加旧答案指标复算，不生成新答案
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite quick --recording ../docs/acceptance/rag-v2-development-answers-run21.json --output ../tmp/offline-recording-new.json
```

`--include-vectors`要求已缓存BGE权重，缺失时失败，不自动下载。临时数据库和日志位于隔离临时目录。HTTP/DNS与真实模型请求受拦截，非预期联网会使验证失败；本地业务TCP和MockTransport允许，用于SSE及接口测试。

| 验证层 | 能确认的内容 |
| --- | --- |
| 自动化测试 | 固定输入下的路由、状态、引用、保存补偿及SSE行为 |
| 冻结检索 | 当前实现对固定语料和标签的Hit/Recall等指标；法条领域由金标准提供 |
| 严格节点回放 | 旧模型输出在当前节点中的处理；提示哈希、输入和顺序不匹配即报错，无真实模型兜底 |
| 旧答案复算 | 对该份原始输出重新计算指标，不代表当前代码生成新答案的质量 |

离线报告的`real_model_quality_passed`始终为`null`。放宽旧录制提示校验会标明`prompt_verified=false`；离线通过不能代替真实模型、Redis或新答案语义验收。

## 真实开发集复验

需要明确调用授权、可用的Redis与后端DeepSeek配置；会消耗API额度。只使用合成输入及隔离SQLite/Chroma，结束后精确清理本轮Redis键；不修改`.env`或默认运行库。

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag --split development --corpus-profile eval-rag-v2-209 --output ../tmp/rag-retrieval-new.json
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --allow-real-model --split development --corpus-profile eval-rag-v2-209 --output ../tmp/rag-answers-new.json
.\.venv\Scripts\python.exe -m scripts.review_rag_answers --input ../tmp/rag-answers-new.json --output ../tmp/rag-review-new.json
```

前两条分别运行120条检索查询和36场景/52轮真实对话，第三条离线复算结构指标。定向排查可给第二条追加`--scenario <开发场景ID>`，可重复指定；局部通过不代表全量通过。401/402/403会停止后续模型请求，保留未执行题目与分母，不自动换模型或重试。检查报告的`complete`、失败轮次与`cleanup`，不能仅依据进程退出码判断质量。

逐条阅读新回答及对应来源后，另建`semantic-review.json`：`raw_report_sha256`绑定答案文件，`reviewer`记录复核身份，`turns`以`场景ID:轮次`为键，每项记录`faithfulness`、`applicability`（`pass/fail`）及具体`notes`。然后执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_quality_gates --answers ../tmp/rag-answers-new.json --retrieval ../tmp/rag-retrieval-new.json --reviews ../tmp/semantic-review.json --output ../tmp/rag-gates-new.json
```

检索、回答须使用同一实现与语料版本。门槛以[配置](../../backend/data/evaluation/rag-v2/quality-gates.json)为准；不得复用旧语义结论、删除失败分母、拼接最佳答案或使用已观察保留集调优。

## 排查入口

`python -m scripts.diagnose_source_losses --input <原始报告> --output <新路径>`可离线分析候选→筛选→最终回答的来源损失；不会生成新答案。数据定义见[评估集](../../backend/data/evaluation/rag-v1/README.md)，回放约束见[离线样本](../../backend/data/evaluation/offline-v1/README.md)，接口错误和状态语义见[API合同](../api-contract.md)。

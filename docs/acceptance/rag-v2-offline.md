# RAG验证方法

以下命令在`backend`目录执行，输出路径必须尚不存在。日常使用离线回归；当前结论和证据见[M4阶段验收](m4-progress.md)，[Run21](rag-v2-final-acceptance.md)是历史验收。

## 离线回归

无需真实模型额度或Redis。测试使用假模型、假Redis和隔离数据库，不修改默认数据。

```powershell
# 相关回归和60条法条开发查询
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite quick --output ../tmp/offline-quick-new.json

# 全部测试和120条开发查询（案例三路检索+法条检索）
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite full --include-vectors --output ../tmp/offline-full-new.json

# 附加旧答案指标复算，不生成新答案
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite quick --recording ../docs/acceptance/rag-v2-development-answers-run21.json --output ../tmp/offline-recording-new.json

# 已观察M4审查片段；严格匹配旧提示与输入，无真实模型兜底
.\.venv\Scripts\python.exe -m scripts.evaluate_recorded_audits --output ../tmp/m4-audits-strict-new.json
# 显式检查旧输出的程序合同，不能验证新提示；旧缺失记录仍报不匹配
.\.venv\Scripts\python.exe -m scripts.evaluate_recorded_audits --allow-unverified-prompts --output ../tmp/m4-audits-contract-new.json
```

`--include-vectors`要求已缓存BGE权重，缺失时失败，不自动下载。临时数据库和日志位于隔离临时目录。HTTP/DNS与真实模型请求受拦截，非预期联网会使验证失败；本地业务TCP和MockTransport允许，用于SSE及接口测试。

| 验证层 | 能确认的内容 |
| --- | --- |
| 自动化测试 | 固定输入下的路由、状态、引用、保存补偿及SSE行为 |
| 冻结检索 | 当前实现对固定语料和标签的Hit/Recall等指标；法条领域由金标准提供 |
| 严格节点回放 | 旧模型输出在当前节点中的处理；提示哈希、输入和顺序不匹配即报错，无真实模型兜底 |
| 旧答案复算 | 对该份原始输出重新计算指标，不代表当前代码生成新答案的质量 |

离线报告的`real_model_quality_passed`始终为`null`。放宽旧录制提示校验会标明`prompt_verified=false`；离线通过不能代替真实模型、Redis或新答案语义验收。

[M4回放清单](../../backend/data/evaluation/offline-m4-v1/README.md)绑定六份报告及186个片段。缺失的旧第二层审核保留不匹配和非零退出码；pytest验证该拒绝符合预期，而不是伪造缺失输出。quick包括审查回放、原观察失败、一次性记录及真实评估预算保护。先使用quick排查，必要时再full，不以频繁真实重跑代替测试。

quick已加入[MF04离线套件](../../backend/tests/unit/test_mf04_rag_scope.py)20项，覆盖引用召回、片段角色、身份歧义、共同财产范围及一次修订；完整原文仍进入双审核。原因、失败记录和当前验证见[MF04修复](m4-mf04-rag-fix-20261001.md)。新提示或输入改变后旧节点不匹配属于回放边界，不能用假模型通过率宣称新模型语义通过。

## 真实开发集复验

需要明确调用授权、可用的Redis与后端DeepSeek配置；会消耗API额度。只使用合成输入及隔离SQLite/Chroma，结束后精确清理本轮Redis键；不修改`.env`或默认运行库。

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag --split development --corpus-profile eval-rag-v2-209 --output ../tmp/rag-retrieval-new.json
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --allow-real-model --max-model-calls 16 --scenario E-L-MF-04 --output ../tmp/rag-targeted-new.json
.\.venv\Scripts\python.exe -m scripts.review_rag_answers --input ../tmp/rag-targeted-new.json --output ../tmp/rag-review-new.json
```

前两条分别运行120条检索查询和1个开发场景的预算受限真实对话，第三条离线复算结构指标。真实评估默认硬上限16次供应商请求，失败/成功、stream/complete统一计数；`--scenario`可重复指定，但局部通过不代表全量通过。只有必要最终验收才运行36场景/52轮，须明确提高预算，日常不整轮真实重跑。401/402/403或达到预算即停止后续模型请求，保留未执行题目与分母，不自动换模型、重试或提高预算。检查`complete`、`call_budget`、失败轮次与`cleanup`。

逐条阅读新回答及对应来源后，另建`semantic-review.json`：`raw_report_sha256`绑定答案文件，`reviewer`记录复核身份，`turns`以`场景ID:轮次`为键，每项记录`faithfulness`、`applicability`（`pass/fail`）及具体`notes`。然后执行：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_quality_gates --answers ../tmp/rag-final-answers-new.json --retrieval ../tmp/rag-retrieval-new.json --reviews ../tmp/semantic-review.json --output ../tmp/rag-gates-new.json
```

检索、回答须使用同一实现与语料版本。门槛以[配置](../../backend/data/evaluation/rag-v2/quality-gates.json)为准；不得复用旧语义结论、删除失败分母或拼接最佳答案。已观察保留集可明确转为开发材料，不能继续称盲测。

上述门槛命令只用于另行完成并保存的`rag-final-answers-new.json`整轮，不能给定向报告改名后称整轮通过；当前不运行该真实整轮。必要最终验收时须明确预算，删除`--scenario`，保存新的整轮路径。

## 一次性验收与已观察开发回归

v6首次观察永久保留；后续重跑使用独立入口，必须有匹配的原始观察记录与输入哈希，不重置记录或改标签：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --observed-development-package data/evaluation/m4-once-v6 --output ../tmp/m4-observed-v6-development-new.json --allow-real-model
```

该入口显式记录`unseen_before_this_run=false`，当前实现可改变；默认16次预算不能当作整包通过证明，优先使用离线回放。[v12储备包](../../backend/data/evaluation/m4-once-v12/README.md)尚未执行，绑定当前实现、24条输入及rubric。独立法律标注待完成；标注及最终预算明确后才首次执行。新包CLI必须显式给出`--max-model-calls`，否则在消耗观察记录前拒绝；失败或部分执行也消耗未见状态。实现改变使冻结失效。

## 排查入口

`python -m scripts.diagnose_source_losses --input <原始报告> --output <新路径>`可离线分析候选→筛选→最终回答的来源损失；不会生成新答案。数据定义见[评估集](../../backend/data/evaluation/rag-v1/README.md)，回放约束见[离线样本](../../backend/data/evaluation/offline-v1/README.md)，接口错误和状态语义见[API合同](../api-contract.md)。

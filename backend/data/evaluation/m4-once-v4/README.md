# M4 一次性验收候选集 v4

24条查询、24个单轮场景，四领域各6条。16条针对旧查询金标准未使用的法条，8条检查事实缺失与地方资料不足。v1–v3均从未向待测模型提交；v4复用同一组未执行问题，绑定安全依赖修复后的实现。旧包和manifest保留，没有观察后重置。

实现指纹现在覆盖后端/前端业务代码、评估脚本、依赖约束与Dockerfiles、前端锁文件、Compose和Nginx配置。实际安装的版本另以部署/依赖审计快照记录。

当前未执行，没有observation-receipt。标签由同一开发代理生成，独立法律标注与主题独立性复核尚未完成；只能称为未向待测模型提交的一次性候选集，不能称为独立第三方盲测。原已观察保留集继续作为历史资料，不用于新集调优。

首次运行前用load_package核对实现和文件指纹。执行先以排他写入方式留下观察记录；失败、部分执行也消耗首次资格，不能删除记录后重跑并继续称未见。当前供应商曾返回HTTP 402，本轮没有启动该包；等待确认模型账户恢复。独立标注和逐条语义复核完成前，不宣称正式验收通过。

在backend目录整包首次运行，报告必须使用新路径：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --allow-real-model --corpus-profile eval-rag-v2-209 --acceptance-package data/evaluation/m4-once-v4 --output ../tmp/m4-once-v4-first-observation.json
```

manifest冻结门槛：行为匹配至少85%、服务失败0、结构安全失败0，要求逐条语义复核和独立标注。标签有歧义时保留原结果及标注问题，不改标签凑通过率。观察后继续调优，应另建真正未执行的问题集。

# M4 已观察记录的离线回放

六份原始报告由manifest保存SHA-256，覆盖186个证据与条件审核片段，包括原两条424、最新MF04单次修订失败、字段/引用相关片段和供应商402。只使用合成问题；原报告、标签和一次性观察记录不改写。

默认严格核对任务、输入、顺序及系统提示词哈希。旧提示或输入发生变化时明确报不匹配，绝不转调真实模型。`--allow-unverified-prompts`仅用于显式核对旧输出在当前程序中的合同：仍严格匹配输入和来源，但不能验证新提示词。两种模式均为零模型调用，并拦截外部HTTP/DNS。

186个片段中有1个旧记录只保存了部分第一层拒绝，当前流程还需第二层审核，无法完整回放。保留该不匹配，不能虚构缺失输出以使整份报告通过。当前另有5个旧片段被确定性保护提前拒绝，单独记录；新MF04保护改变了原五节点修订输入，不能复用旧输出证明新提示效果。

在backend目录执行，输出路径必须尚不存在：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_recorded_audits --output ../tmp/m4-recorded-audits-strict-new.json
.\.venv\Scripts\python.exe -m scripts.evaluate_recorded_audits --allow-unverified-prompts --output ../tmp/m4-recorded-audits-contract-new.json
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite quick --output ../tmp/m4-offline-quick-new.json
```

回放报告如实保留不匹配并返回非零退出码；pytest检查可回放合同、缺失记录必须报错、旧修订输入改变仍报不匹配、输入/提示改变和原报告篡改。测试通过不等于所有片段已完整回放，也不代表新模型输出或独立法律复核通过。

日常开发先运行quick；只有代码变更或失败需要时再运行full。真实评估必须显式使用`--allow-real-model`，默认最多16次供应商请求，失败和流式调用均计数，不自动提高预算。达到上限仍保留原题目和未执行分母，不能将部分执行计作验收通过。

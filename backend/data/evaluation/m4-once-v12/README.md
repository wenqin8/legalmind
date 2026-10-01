# M4 未执行储备集 v12

2026-10-01：24题、四领域各6题；16条可回答、4条缺事实、4条缺地方文件。复用v11从未提交的输入与rubric，仅在MF04检索、片段角色和提示约束修复后重新绑定实现哈希。旧问题、标签、manifest和已有观察记录保持原样。

用户已确认先交付课程MVP，法律质量验收保留未完成，本包继续封存；不降低原manifest门槛。本包未向模型提交，无观察记录。同一开发代理编写问题与标注，独立法律复核待完成，不能称为独立第三方盲测。与旧开发集及已观察v6的精确文本重复为0，不代表语义主题独立。

实现再改变会使冻结失效；首次失败或部分执行也消耗未见状态。日常先运行离线测试；独立标注和最终预算明确后才执行以下付费验收，在backend目录使用新报告路径：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --acceptance-package data/evaluation/m4-once-v12 --output ../tmp/m4-once-v12-first-observation.json --allow-real-model --max-model-calls 180
```

门槛：行为匹配至少85%、服务失败0、硬性结构失败0，另需语义复核及独立标注。预算不会自动提高；已执行包只能使用`--observed-development-package`作为开发回归。当前未执行，不能声明通过。

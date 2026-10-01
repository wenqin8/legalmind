# M4 未执行储备集 v10

本包未执行；新增离线回放与调用上限工具后，实现冻结哈希已失效。原输入与manifest保持原样，同一组未提交问题的新冻结见[v11](../m4-once-v11/README.md)。

2026-10-01创建：24条新问题/24场景，四领域各6条（16条可回答、4条缺事实、4条缺地方文件）。本包问题未提交给模型，没有观察记录；只进行了文件哈希、结构、查询与场景映射检查。

v6首次执行后的问题已经观察，保留原始成绩并用于开发回归。本包另写新问题，与旧开发集及v6精确文本重复为0；不能据此证明语义主题完全独立。来源使用仓库核验快照，rubric保存原文、元数据和待核对条件。

由同一开发代理编写，标注和语义复核待独立法律专家完成，不能称为独立第三方盲测。manifest绑定当前实现及查询、场景、rubric文件；任何实现改变均使本次冻结失效。首次失败或部分执行也会写入不可重置的观察记录。

在backend目录首次执行（使用API额度，必须保留新的原始报告路径）：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --acceptance-package data/evaluation/m4-once-v10 --output ../tmp/m4-once-v10-first-observation.json --allow-real-model
```

门槛：行为匹配至少85%、服务失败0、硬性结构失败0，另需语义复核及独立标注。当前状态为未执行，不能声明已通过。

已执行包只能通过`--observed-development-package`进入开发回归；该入口要求原始观察记录和文件哈希一致，允许当前实现改变，并显式标记`unseen_before_this_run=false`。不修改首次报告或标签。

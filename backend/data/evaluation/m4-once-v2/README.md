# M4 一次性验收候选集 v2

当前实现冻结后重新绑定的24条查询/24个单轮场景，四领域各6条；16条针对旧查询金标准未使用的法条，另8条覆盖事实缺失和地方资料不足。v1未执行，因退出登录状态竞态修复导致实现指纹改变；v2复用同一组从未向待测模型提交的问题，保留v1原文件及manifest。

标签仍为开发代理候选，独立法律复核待完成。同一代理编写生成器，主题独立性未由专家确认，不能称为独立第三方盲测。原rag-v1保留集已经观察，仅保留作历史证据。

manifest冻结文件、实现指纹和质量门槛。首次真实运行前写入observation-receipt.json；运行失败、部分完成或基础设施故障也消耗本包，保留记录。观察结果后不得重新绑定实现或删除记录冒充未见验收。

取得真实调用授权并完成独立标注核对后，在backend目录整包运行，输出使用新路径：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --allow-real-model --acceptance-package data/evaluation/m4-once-v2 --corpus-profile eval-rag-v2-209 --output ../tmp/m4-once-v2-answers-new.json
```

验收门槛：行为匹配至少85%，服务失败和结构安全失败均为0，完成独立标注及逐条语义复核。complete=true仅表示执行完整，不代表验收通过。保留全部失败分母、原始输出及标注更正理由，不能定向选题拼接通过答案。

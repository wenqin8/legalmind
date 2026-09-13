# 第二周演示案例原始数据

`cases.jsonl` 是第二周 Day 1 冻结的原始演示案例基线，采用 UTF-8 JSON Lines 格式，每行一条记录。

## 数据边界

- 共 16 条案例，婚姻家庭、劳动争议、交通事故、合同纠纷各 4 条。
- 所有编号均为 `DEMO-<DOMAIN>-<NNN>`，只是项目内演示标识，不是真实案号。
- 所有记录均设置 `source_kind=demo`、`source_type=case`、`is_demo=true`、`is_synthetic=true`。
- `court`、`judgment_date`、`source_url` 固定为空，不虚构法院、裁判日期或外部来源。
- `law_references` 固定为空；第二周不填充未经权威来源核验的法条资料。
- `source_description` 和 `authorization_note` 明确说明数据仅用于课程演示、开发、测试与检索评估。

## 使用约束

本文件不是司法案例库，不得作为法律依据或真实裁判样本展示。后续 Day 2 的 Schema、清洗和导入流程必须保留这些来源与演示标识，不能在规范化过程中补造法院、案号、裁判日期、法条或链接。

Day 2 实现内容哈希和导入模型后，原始记录仍保留在本目录；任何清洗产物和向量索引均由脚本重新生成，不直接改写该基线文件。

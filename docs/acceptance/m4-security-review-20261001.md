# M4 安全复核

复核日期：2026-10-01。已完成应用边界检查和已安装依赖的公告查询，修复有可用补丁的问题。Chroma仍有上游公告，依赖审计结果为未通过；当前措施缩小本地部署的暴露范围，不能称为漏洞已消除或安全认证。

## 依赖结果与修复

| 检查 | 最新结果 | 证据 |
| --- | --- | --- |
| 前端官方npm审计 | 已知漏洞0 | [官方结果](m4-frontend-audit-official-20261001-utf8.json) |
| 本地后端 | 138/138包查询完成，1包有公告，passed=false | [审计Run3](m4-local-python-audit-20261001-run3.json)、[安装快照](m4-local-python-packages-20261001-run4.txt) |
| 运行中Docker后端 | 135/135包查询完成，1包有公告，passed=false | [审计Run3](m4-docker-python-audit-20261001-run3.json)、[安装快照](m4-docker-python-packages-20261001-run3.txt) |

查询使用[PyPI逐版本JSON API](https://docs.pypi.org/api/json/)，包含pip、setuptools及应用依赖，不只检查requirements里的直接依赖。CPU轮子的`+cpu`后缀映射至公开版本公告；这不验证轮子内容。OS与基础镜像软件包、未知漏洞及独立渗透测试不在此检查内。

最初本地查询标记Chroma、PyJWT、oauthlib和urllib3，Docker另标记setuptools；补查pip后也发现需升级。修复版本如下：

| 包 | 本地安装 | Docker安装 | 修复方式 |
| --- | --- | --- | --- |
| PyJWT | 2.15.0 | 2.15.1 | requirements提高版本，增加嵌套JWT头部及载荷拒绝测试 |
| setuptools | 84.0.0 | 84.0.0 | constraints及Docker构建工具升级 |
| pip | 26.2.1 | 26.2.1 | constraints及Docker构建工具升级 |
| urllib3 | 2.8.0 | 2.8.0 | 约束已有依赖下限 |
| oauthlib | 4.0.0 | 4.0.0 | 约束已有依赖下限 |

没有新增应用运行时依赖。版本下限集中在[constraints.txt](../../backend/constraints.txt)，实际安装版本保存在上述快照。双方`pip check`通过，最新686项后端离线回归通过。运行容器核对为PyJWT 2.15.1、pip 26.2.1、setuptools 84.0.0。RAG修复后的镜像已更新，课程收尾没有运行代码或依赖变更，实际浏览器重启后运行检查9项通过。

修复依据包括维护者公告：[PyJWT](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-42vr-xj54-vc7v)、[setuptools](https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c)、[urllib3](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77)、[oauthlib](https://github.com/oauthlib/oauthlib/security/advisories/GHSA-xpv3-w29h-x7cv)。初始失败及升级过程中的审计报告保留，未改写为通过。

npm镜像站审计返回404，已保留[失败输出](m4-frontend-audit-20261001.json)，随后改用官方registry。任务内临时pip-audit工具安装未完成，不能声称运行过pip-audit；最终结果来自逐版本PyPI查询，完整覆盖和失败状态均写入报告。

## Chroma剩余问题及当前边界

Chroma 1.5.9的查询结果含四条不同CVE：CVE-2026-45829、45830、45831、45833；GHSA与PYSEC同一问题的重复记录不另算漏洞。逐版本PyPI结果没有提供修复版本，原始描述保存在上述审计JSON。2026-10-01查询的[官方最新发布](https://github.com/chroma-core/chroma/releases/latest)仍为1.5.9；已审查的[45829](https://github.com/advisories/GHSA-f4j7-r4q5-qw2c)、[45831](https://github.com/advisories/GHSA-xph7-9rjv-w5fr)、[45833](https://github.com/advisories/GHSA-36p7-vc44-83pf)公告均列patched versions为None；[45830](https://github.com/advisories/GHSA-2wm9-hf6c-p5cr)为未审查公告，相关版本字段Unknown，不能把Unknown等同已确认无补丁。当前没有据此可升级的已确认修复版本。涉及服务端集合接口的远程代码加载及跨租户授权；不能只升级其他包后宣称后端零漏洞。

当前代码使用本地`PersistentClient`，`embedding_function=None`；由应用生成数值向量，模型revision固定。未启动Chroma HTTP服务，用户不能指定模型仓库或`trust_remote_code`。Nginx只代理LegalMind API，Chroma路径检查返回404。Compose仅公开`127.0.0.1:8080`，数据库、Redis及Chroma均无公开端口。代码位置见[向量存储](../../backend/app/rag/vector_store.py)和[嵌入模型](../../backend/app/rag/embeddings.py)。这些是当前调用路径与部署配置的缓解措施，没有修改Chroma上游包。

当前交付保持本机使用范围。若扩大为公开服务、启用Chroma HTTP或允许用户配置模型，应先处理这些上游问题并重新复核，不能直接沿用本次结论。

## 应用边界证据

[收尾边界检查Run6](m4-security-boundary-20261001-run6.json)4项通过：实际配置密钥未出现在检查的Git已跟踪/未跟踪交付文本及前端构建中；Chroma调用使用嵌入模式及外部向量；其HTTP路径未暴露；嵌套JWT经Nginx送达应用后被401拒绝。Run2的过大输入在代理处被拒绝，未满足应用401探测条件，该失败报告保留；缩小输入后通过。检查没有输出密钥值，也不证明所有未知秘密或漏洞不存在。

JWT、越权、退出期间晚到响应、输入校验、会话隔离和限流由相关单元/集成测试覆盖；真实PostgreSQL、Redis与Nginx由部署烟测和浏览器报告覆盖。认证20次/分钟、业务120次/分钟采用单进程配额，本地代理用户共享配额，不作为公开部署的分布式限流方案。

运行镜像为非root UID 10001，应用镜像没有.env，Nginx配置检查通过，详见[收尾运行证据Run8](m4-deployment-runtime-20261001-run8.json)。密钥保存在忽略的本地配置，未提交或对外发送。

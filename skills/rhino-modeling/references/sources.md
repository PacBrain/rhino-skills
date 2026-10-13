# 官方来源索引

2026-10-12 核对了下列官方页面的指定主题，表内记录结论与适用范围。命令选项先与目标安装的版本及 `--help` 对照。文档依据与原生运行证据分开，后者见 [validation.md](validation.md)。

| 编号 | 官方页面 | 支持的结论 | 适用范围 |
|---|---|---|---|
| R01 | [Rhino - RhinoCode Command Line Interface](https://developer.rhino3d.com/guides/scripting/advanced-cli/) | 版本前提、StartScriptServer、按实例 ID 调度、JSON 实例查询 | Rhino 8.11+；Windows/macOS |
| R02 | [Rhino - Scripting: Python](https://developer.rhino3d.com/guides/scripting/scripting-python/) | CPython/Python.NET 与 IronPython 的区别、脚本运行时标记和依赖 | Rhino 8；具体运行时/包能力以安装版本为准 |
| R03 | [Rhino - Code-Driven File IO](https://developer.rhino3d.com/guides/rhinocommon/code-driven-file-io/) | 格式 options 字典、headless 文档、GH 独立文档导出 | Rhino 8；格式取决于对应导入/导出插件 |
| R04 | [Stereolithography (.stl) import/export — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8mac/help/en-us/fileio/stereolithography_stl_import_export.htm) | STL 保存网格、显式生成网格、导入焊接/分离选项和回读要求 | Rhino 8 macOS 帮助；跨软件 STL 单位需回查 |
| R05 | [Units properties — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/documentproperties/units.htm) | 文档单位、缩放、公差和显示精度的区别；导入不自动改变目标公差 | Rhino 8 |
| R07 | [ShowEdges — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/showedges.htm) | 裸边/非流形边的定义与 ShowEdges 检查范围 | Rhino 8；surface/mesh/SubD 的具体显示能力不同 |
| R08 | [Zebra — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/zebra.htm) | Zebra 的连续性观察、分析网格精度对结果的影响 | Rhino 8；依赖分析网格设置 |
| R10 | [Loft — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/loft.htm) | Loft 曲线顺序、方向/闭合缝、触碰端点、重建和 refit | Rhino 8 |
| R11 | [Sweep2 — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/sweep2.htm) | Sweep2 的导轨/截面对应关系和复杂度传递 | Rhino 8 |
| R12 | [BlendSrf — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/blendsrf.htm) | BlendSrf 连续性、手柄/内部形状和局部下陷风险 | Rhino 8；连续性与整体形态分别评价 |
| R13 | [BooleanUnion — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/booleanunion.htm) | 布尔失败提示点、法线、重叠面、交线的诊断 | Rhino 8；开放面布尔受法线影响 |
| R14 | [FilletEdge — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/filletedge.htm) | FilletEdge 局部半径上限、倒圆次序及简化交汇 | Rhino 8 |
| R15 | [Check — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/commands/check.htm) | 数据结构检查的限制、微小修剪边和网格缺陷类型 | Rhino 8；Check 不覆盖全局自交 |
| R16 | [STEP (.stp; .step) import/export — Rhino 3-D modeling](https://docs.mcneel.com/rhino/8/help/en-us/fileio/step_stp_import_export.htm) | STEP 导入单位/公差、导出选项及 SubD 导出为 polysurface | Rhino 8；核对安装版本提供的 STEP schema |
| R17 | [Rhino - Grasshopper Scripting: Python](https://developer.rhino3d.com/guides/scripting/scripting-gh-python/) | Item/List/Tree 输入形状、类型提示、Required 输入、脚本与 SDK 模式 | Rhino 8 Python 组件；Required 输入选项为 8.14+ |
| R18 | [EdgeContinuity](https://docs.mcneel.com/rhino/8/help/en-us/commands/edgecontinuity.htm) | 边对 G0/G1/G2 偏差、用户设定阈值、采样显示密度和最大值 | Rhino 8 当前帮助；先检查安装版本是否有此命令 |
| R19 | [Curvature / CurvatureAnalysis / CurvatureGraph](https://docs.mcneel.com/rhino/8/help/en-us/commands/curvature.htm) | 内部鼓包/凹陷/波纹诊断、Gaussian/Mean/半径显示与色标 | Rhino 8；分析网格密度影响诊断 |
| R20 | [PointDeviation](https://docs.mcneel.com/rhino/8/help/en-us/commands/pointdeviation.htm) | 采样点来源、方向、Ignore/角度过滤和统计量 | Rhino 8 当前帮助；被测对象与目标支持类型不相同 |
| R21 | [ToNURBS](https://docs.mcneel.com/rhino/8/help/en-us/commands/tonurbs.htm) | SubD packed/unpacked、非规则顶点的近似、强制 G2 的鼓包或凹陷 | Rhino 8 当前帮助；转换选项以安装版本为准 |
| R22 | [Rebuild / RebuildCrvNonUniform](https://docs.mcneel.com/rhino/8/help/en-us/commands/rebuild.htm) | 结构和次数重建、曲面偏差采样、RequestedTolerance 不必然达到 | Rhino 8；命令报告与采样范围有边界 |
| R23 | [QuadRemesh](https://docs.mcneel.com/rhino/8/help/en-us/commands/quadremesh.htm) | 近似面数/边长目标、导线、转 SubD 与插值选项影响形态 | Rhino 8 |
| R24 | [ShrinkWrap](https://docs.mcneel.com/rhino/8/help/en-us/commands/shrinkwrap.htm) | 包裹网格、偏移/平滑/填洞的形态影响及设计微缝风险 | Rhino 8 新增功能；用于包裹网格重建 |
| R25 | [mcneel/rhino3dm README](https://github.com/mcneel/rhino3dm) | 独立于 Rhino 的 OpenNURBS 风格库，几何/属性与 3DM I/O；高级操作可调用 Compute | 核对时仓库默认 9.x 分支；具体 API 依安装包版本 |
| R26 | [What is RhinoCommon?](https://developer.rhino3d.com/guides/rhinocommon/what-is-rhinocommon/) | RhinoCommon 与 Rhino/Grasshopper、Rhino UI/IO 插件的关系 | Windows/macOS 的 Rhino .NET SDK；文档更新 2024-10-07 |
| R27 | [Compute: Features](https://developer.rhino3d.com/guides/compute/features/) | 无状态 REST、RhinoCommon 高级几何、GH 和客户端；本地显示使用 Rhino 视口 | 文档更新 2026-03-16；服务部署条件见 R28/R29 |
| R28 | [Getting Started with Rhino.Compute on Linux](https://developer.rhino3d.com/guides/compute/compute-linux-getting-started/) | Linux 路线为 WIP；非 3DM FileIO 与第三方插件限制；许可依赖 | 文档更新 2026-09-15；Rhino WIP；Ubuntu 24.04/AmazonLinux 2023 |
| R29 | [Deployment to Production Servers](https://developer.rhino3d.com/guides/compute/deploy-to-iis/) | Rhino 8 Compute 服务部署与本地桌面执行不同，许可/服务器条件独立 | 文档更新 2026-05-21；Rhino 8 / Windows IIS 路线 |
| R30 | [Agent Skills Specification](https://agentskills.io/specification) | 通用 SKILL.md、frontmatter、可选 scripts/references 和按需加载 | 核对日期的格式标准；各宿主发现规则独立 |

[sources.json](sources.json) 保存逐条核对日期、主题、适用范围与证据等级。方法选择、验收组合和副本管理按任务应用这些资料。

核对时 `curvatureanalysis.htm` 仅返回跳转壳，R19 使用已读取正文的 `curvature.htm`；Linux Compute 的 WIP 条件见 R28。命令引入版本查对应发布说明，未明确的小版本按安装环境探测。

来源或本地行为冲突时记录软件完整版本、平台、最小复现与实际结果，并更新对应条目的结论与核对日期。

---
name: rhino-modeling
description: Build, inspect, repair, script, and export Rhino CAD models. Use for curves, NURBS/Brep, SubD, meshes, Grasshopper, surface quality checks, native viewport evidence, and CAD or printing exports.
license: MIT
compatibility: Agent-independent instructions. Bundled dispatcher requires Python 3.10+ and licensed Rhino 8.11+ on Windows or macOS; geometry scripts use Rhino's Python 3 and RhinoCommon. No agent-specific connector required.
---

# Rhino 建模与验证

适用于能读取文件的 agent；可由技能加载器发现，也可直接读取此文件并使用 CLI。`agents/openai.yaml` 仅为可选宿主元数据，`$rhino-modeling` 等调用语法由宿主决定。脚本和参考文件均相对此技能目录定位，不要求在仓库根目录运行。[标准依据](https://agentskills.io/specification)

先明确目标形态、尺寸来源、可修改范围、单位与交付用途。读取当前模型和项目约束；已有曲线、参数或原生几何优先于截图重建。

## 按需读取

- 方法选择、曲线/NURBS/Brep、SubD、网格、Grasshopper：[modeling.md](references/modeling.md)。
- 曲面内部起伏、接缝连续性、单位、公差、拓扑：[geometry-quality.md](references/geometry-quality.md)。
- 环境依赖、平台边界、只读 `inspect`、调度与文档句柄：[automation.md](references/automation.md)。
- 3DM/STEP/STL/3MF、导出回读、事务发布与视口证据：[delivery.md](references/delivery.md)。
- 逐项官方依据及适用版本：[sources.md](references/sources.md)、[sources.json](references/sources.json)；实际验证范围：[validation.md](references/validation.md)。

## 操作原则

按任务选择原生命令、RhinoCommon 或 Grasshopper。完整方法指导不代表所有命令已有自动化实现。桌面 Rhino、rhino3dm、Compute 的能力不同；离线读写 3DM 不替代 Rhino 原生运算与导出。

修改前核对实例、文档路径、单位、对象 ID 和人工变化。候选先在内存或独立文档验证，再替换明确受控的对象；保留源文件和上一成功版本。多实体是否正确取决于任务，单实体导出器的限制不应改变设计。

保留必要控制曲线和参数。不要用强制 JoinEdge、增大公差或偷偷转网格掩盖 NURBS 失败。用户只要求导出时不改形；设计峰谷、阶差和功能转折须与缺陷区分。镜像后重新检查实体与网格方向。

## 验证与交付

按用途检查有效性、裸边/非流形、方向、尺寸、关键断面、内部曲率和接缝。`Check`、`IsSolid`、斑马纹及采样各有边界；单项通过不能证明全局无自交、全表面 G2、可制造或实物性能。

使用 `scripts/rhino_run.py` 时，等待匹配作业 token 的完成结果，不能把 CLI 排队成功当作作业成功。超时先查原作业状态，不能自动重复提交。`native_job.py`、`native_ops.py` 和视口脚本在 Rhino 内执行。

导出先隔离生成并回读，全部检查通过后发布。报告分别列出请求公差、实际测量、采样方法和 `not_run` 项；附源哈希、软件版本、单位、对象身份。截图来自实际候选的 Rhino 视口。制造、装配、承重和人体工学结论需对应实测。

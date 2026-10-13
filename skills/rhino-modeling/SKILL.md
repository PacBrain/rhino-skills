---
name: rhino-modeling
description: Build, inspect, repair, script, and export Rhino CAD models. Use for curves, NURBS/Brep, SubD, meshes, Grasshopper, surface quality checks, native viewport evidence, and CAD or printing exports.
license: MIT
compatibility: Python 3.10+ for the dispatcher; licensed Rhino 8.11+ on Windows or macOS for geometry, RhinoCommon, and viewport operations.
---

# Rhino 建模与验证

从建模目标选择方法，检查实际几何并交付 CAD 文件。脚本和参考文件均相对此技能目录定位，可通过绝对路径从任意工作目录调用。

先明确目标形态、尺寸来源、可修改范围、单位与交付用途。读取当前模型和项目约束；已有曲线、参数或原生几何优先于截图重建。

## 按需读取

- 方法选择、曲线/NURBS/Brep、SubD、网格、Grasshopper：[modeling.md](references/modeling.md)。
- 曲面内部起伏、接缝连续性、单位、公差、拓扑：[geometry-quality.md](references/geometry-quality.md)。
- 环境依赖、平台边界、只读 `inspect`、调度与文档句柄：[automation.md](references/automation.md)。
- 3DM/STEP/STL/3MF、导出回读、事务发布与视口证据：[delivery.md](references/delivery.md)。
- 逐项官方依据及适用版本：[sources.md](references/sources.md)、[sources.json](references/sources.json)；实际验证范围：[validation.md](references/validation.md)。

## 操作原则

按任务选择原生命令、RhinoCommon 或 Grasshopper；文件读写可用 rhino3dm，服务端运算可用 Compute。环境与接口选择见自动化参考。

修改前核对实例、文档路径、单位、对象 ID 和人工变化。候选先在内存或独立文档验证，再替换明确受控的对象；保留源文件和上一成功版本。根据设计保留单实体或多实体结构，为导出器准备对应选集。

保留必要控制曲线、参数和源几何。NURBS 失败先定位交线、边界和约束；修复后按原公差验收。导出使用原形，改形遵循任务范围；区分设计峰谷、阶差与缺陷。镜像后重新检查实体与网格方向。

## 验证与交付

按用途分别检查数据有效性、拓扑、方向、尺寸、关键断面、内部曲率和接缝。记录各项检查的方法、范围与结果。

使用 `scripts/rhino_run.py` 时，以匹配作业 token 的完成结果确认执行。超时先查原作业状态，再决定后续操作。`native_job.py`、`native_ops.py` 和视口脚本在 Rhino 内执行。

导出先隔离生成并回读，全部检查通过后发布。报告分别列出请求公差、实际测量、采样方法和 `not_run` 项；附源哈希、软件版本、单位、对象身份。截图来自实际候选的 Rhino 视口。制造、装配、承重和人体工学结论需对应实测。

---
name: rhino-modeling
description: Build, inspect, repair, script, and export Rhino 8 CAD models using RhinoCommon and official Rhino tools. Use for curves, NURBS/Brep, SubD or mesh workflows, geometry quality checks, Grasshopper scripting, native viewport evidence, and CAD/printing exports.
---

# Rhino 建模与验证

先理解目标形态、尺寸来源、可修改范围、单位和交付用途。读取当前文件与项目规则；优先利用已有曲线/参数/原生模型，避免按截图凭空重建已存在几何。

## 路由

- 曲线、曲面、实体、SubD/网格和 Grasshopper 路线：[modeling.md](references/modeling.md)。
- 单位、公差、封闭性、接缝和自交筛查：[geometry-quality.md](references/geometry-quality.md)。
- Python 3、RhinoCommon、实例/文档、执行确认：[automation.md](references/automation.md)。
- 3DM/STEP/STL/3MF、实际视口、回读：[delivery.md](references/delivery.md)。
- 官方资料：[sources.md](references/sources.md)；实测能力：[validation.md](references/validation.md)。

## 操作原则

以任务选择手工命令、RhinoCommon 脚本或 Grasshopper，不强迫所有工作用同一路线。可用官方 `rhinocode` 时先查询版本和实例，显式指定目标。其他接口可用时遵守其文档句柄语义，不混用工具注入文档、ActiveDoc 与 Grasshopper 文档。

修改前核对文件路径、单位、对象身份及人工变化。参数化重建先在内存/临时文档生成候选，检查后才替换受控对象；失败不覆盖上一成功版本。保留手工对象，不全选删除或覆盖来源文件。多实体是否正确取决于任务，不能一律要求一个 Brep。

建模方法解释得清楚，保留必要控制曲线和参数。不通过强制 JoinEdge、放大公差或偷偷转网格掩盖 NURBS 失败。用户只要求导出时不擅自改形；镜像与展示平移分开，镜像后重新检查法线。

## 验证与交付

按用途验证：对象有效性、裸边/非流形、方向、尺寸、体积、关键断面、曲面异常、导出回读。开放曲面在设计中可能正常，但不能当封闭打印实体交付。

Check/IsValid/IsSolid、斑马纹、自交筛查分别回答不同问题；单项通过不证明全表面精确 G2、无任何自交、可制造或实物性能。报告标明方法、采样间距/范围、公差和未运行项目。

脚本用 `scripts/rhino_run.py` 执行并等待 token 完成确认，不能把 CLI 成功排队当作脚本成功。`native_job.py` 与 `native_ops.py` 只能在 Rhino 内运行。外部 Python 语法检查、rhino3dm 读文件不替代完整 Rhino 几何运算。

输出记录源哈希、软件版本、单位、尺寸及检查状态。视口证据来自真实模型，生成式示意图不可当建模成功证据。CAD 原件保留；派生文件导出后回读。制造/人体工学结论仅在有对应实测证据时提出。

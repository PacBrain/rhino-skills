# Rhino Skills

依据 McNeel 官方文档编写的中文 Codex Skill，支持 Rhino 建模方法选择、几何验收、Python/RhinoCommon 自动化、原生截图及 CAD/打印文件交付。独立项目，不是 McNeel 官方产品。

## 安装与调用

克隆后运行 `python install.py`，安装为本机 Codex 可发现技能；不会覆盖已有不同技能。Windows 不支持符号链接时，将 `skills/rhino-modeling` 复制到 Codex 的 `skills` 目录。重新加载技能目录或开启新对话后调用：

```text
使用 $rhino-modeling，检查这个 Rhino 模型的单位、封闭性和曲面质量，然后导出并回读 STEP/STL。
```

自动选择默认启用。入口：[SKILL.md](skills/rhino-modeling/SKILL.md)。

## 运行

外部调度器使用 Python 3.10+ 标准库。几何脚本依赖已安装、可运行的 Rhino；不能用系统 Python 执行 `native_ops.py` 或 `native_job.py`。

```bash
python skills/rhino-modeling/scripts/rhino_run.py env
python -m unittest discover -s tests -v
```

先在 Rhino 启动官方 ScriptServer，并核对实际实例/文档。参数化合成测试、导出和截图接口见 [自动化参考](skills/rhino-modeling/references/automation.md)。

## 能力与证据

- 曲线、Loft/Sweep/Blend、布尔/倒圆的选择与诊断；SubD/mesh/Grasshopper 的适用路线。
- 单位与公差、裸边/非流形、法线、断面、接缝、自交筛查及方法边界。
- 带实例/文档保护和完成 token 的官方 RhinoCode 调度。
- 实际 Rhino 几何测试、STEP/STL 回读及 ViewCapture 截图。

本机实测为 macOS Rhino 8.35；其他平台/版本、SubD 和 Grasshopper 自动建图未做运行验证。有效实体不自动等于无任何自交、可制造或人体工学验证通过。详见 [验证记录](skills/rhino-modeling/references/validation.md) 和 [官方来源](skills/rhino-modeling/references/sources.md)。

两套工具可通过模型和验证清单衔接，但不依赖拓竹 Skill。公开内容只含通用方法与合成测试，不含客户模型或私人项目路径。原创内容 MIT；第三方权利见 [NOTICE.md](NOTICE.md)。

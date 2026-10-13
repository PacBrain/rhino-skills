# Rhino Skills

Rhino 建模、曲面检查、RhinoCommon 自动化和 CAD 导出 Skills。采用 [Agent Skills 格式](https://agentskills.io/specification)，从 [SKILL.md](skills/rhino-modeling/SKILL.md) 按任务加载参考资料和脚本。

## 功能

- 曲线、NURBS/Brep、SubD、网格和 Grasshopper 工作流。
- 单位、公差、拓扑、法线、断面、曲率与接缝检查。
- RhinoCode 调度、模型检查、导出回读和视口截图。

## 安装

```bash
git clone https://github.com/PacBrain/rhino-skills.git
cd rhino-skills
```

按需要选择安装命令：

```bash
# 安装到 ~/.agents/skills
python install.py
# 指定 agent 或项目使用的 skills 目录
python install.py --dest /path/to/skills
# 预览安装位置
python install.py --dest /path/to/skills --dry-run
# 链接源码目录，随仓库更新
python install.py --dest /path/to/skills --mode symlink
```

安装器使用 Python 3.10+，默认复制完整技能目录。相同版本可重复安装；更新副本时先保存本地修改，再替换目录。符号链接模式跟随源码更新。

也可直接复制 `skills/rhino-modeling` 到 agent 的技能目录。使用自定义加载方式时，让 agent 读取其中的 `SKILL.md`；脚本和参考文件路径均以技能目录为基准。`agents/` 保存客户端使用的界面元数据。

## 使用

> 使用 rhino-modeling，检查模型的单位、封闭性和曲面质量，然后导出并回读 STEP/STL。

Python 3.10+；几何运算使用 Windows/macOS 上的 Rhino 8.11+、Rhino Python 3 和 RhinoCommon。外部调度器使用 Python 标准库。

```bash
python skills/rhino-modeling/scripts/rhino_run.py env
python -m unittest discover -s tests -v
```

在 Rhino 中运行 `StartScriptServer`，再选择实例和文档。作业格式、只读检查、导出和截图示例见[自动化参考](skills/rhino-modeling/references/automation.md)。

## 验证与资料

CI 覆盖 Windows、macOS、Linux 上的 Python 3.10/3.14 安装与离线测试，以及官方 `skills-ref` 格式校验。软件集成结果和待验证项目见[验证记录](skills/rhino-modeling/references/validation.md)。

[来源索引](skills/rhino-modeling/references/sources.md)记录官方文档、具体版本和适用条件。格式检查命令：`skills-ref validate skills/rhino-modeling`。

## 许可

原创代码和文档采用 [MIT](LICENSE) 许可，引用资料见 [NOTICE.md](NOTICE.md)。许可文件随技能目录分发。

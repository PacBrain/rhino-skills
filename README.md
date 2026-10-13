# Rhino Skills

面向各类智能体的 Rhino 建模、检查、自动化和交付技能，采用开放的 [Agent Skills 格式](https://agentskills.io/specification)。依据 McNeel 官方资料编写，独立维护，不是 McNeel 官方产品。技能内容不依赖特定模型、客户端或 MCP 服务。

## 使用与安装

- 支持 Agent Skills 的客户端：将完整 `skills/rhino-modeling` 目录安装到该客户端实际扫描的技能目录。
- 能读取文件、但没有技能发现功能的智能体：直接读取 [SKILL.md](skills/rhino-modeling/SKILL.md)，再按任务读取其中引用的资料。
- 没有本机 Rhino 访问能力的智能体：可以用于方法分析、脚本准备和已有报告检查；原生几何运算、视口及导出验收仍需可运行的 Rhino 环境。

```bash
# 默认复制到 ~/.agents/skills；不需要符号链接权限
python install.py
# 指定客户端或项目的技能父目录
python install.py --dest /path/to/agent/skills
# 查看操作，不写入文件
python install.py --dest /path/to/agent/skills --dry-run
# 开发时可将技能链接到当前源码目录
python install.py --dest /path/to/agent/skills --mode symlink
```

安装器不会覆盖不同内容；同一链接或内容一致的副本可重复安装。源码更新后，已有副本不同会被拒绝，需先保存自己的改动并选择新的目标位置或手动替换；符号链接跟随源码更新。保留显式 `--codex-home DIR`，等价于 `--dest DIR/skills`；默认路径不读取 `CODEX_HOME`，也不自动迁移旧安装。Windows 使用同样的 Python 命令和本机路径。

`~/.agents/skills` 是跨客户端约定，具体发现和启用方式取决于客户端。[Gemini CLI](https://geminicli.com/docs/cli/skills/) 明确支持此路径；[Claude Code](https://code.claude.com/docs/en/skills) 可用 `--dest ~/.claude/skills`，项目安装则指定 `.claude/skills`。其他客户端以其文档为准。`agents/openai.yaml` 仅为可选的 OpenAI 界面元数据，不参与脚本运行，也不表示仅限 Codex。

通用调用示例：

> 使用 rhino-modeling 技能，检查这个 Rhino 模型的单位、封闭性和曲面质量，然后导出并回读 STEP/STL。

客户端可能使用 `/rhino-modeling`、`$rhino-modeling` 或自动选择；安装本身不保证这些调用方式均可用。

## 运行与验证

外部调度器使用 Python 3.10+ 标准库；几何脚本依赖已安装且可运行的 Rhino。脚本路径以实际技能目录为基准，可以从任意工作目录通过绝对路径调用。`native_ops.py`、`native_job.py` 和 `capture_views.py` 需要 Rhino 的 Python 环境。

从仓库根目录运行：

```bash
python skills/rhino-modeling/scripts/rhino_run.py --help
python skills/rhino-modeling/scripts/rhino_run.py env
python -m unittest discover -s tests -v
```

先在 Rhino 启动官方 ScriptServer，核对实际实例与文档。作业、完成确认、合成测试和截图接口见[自动化参考](skills/rhino-modeling/references/automation.md)。原生交互可以使用智能体已有的受支持界面或接口；不强制某种客户端工具。

## 覆盖与证据

- 曲线、Loft/Sweep/Blend、布尔与倒圆诊断，以及 SubD、网格和 Grasshopper 路线选择。
- 单位、公差、裸边、非流形、法线、断面、接缝、自交筛查和方法边界。
- 带实例与文档保护、完成 token 的 RhinoCode 调度；3DM/STEP/STL 导出回读及真实 ViewCapture 证据。

[验证记录](skills/rhino-modeling/references/validation.md)列明实际运行的软件版本、平台、结果和未运行项目。CI 只检查 Linux、macOS、Windows 的技能安装包与离线 Python 行为；通过 CI 不代表对应平台已运行 Rhino，也不代表每种智能体客户端均已实测。有效实体不自动证明无全部自交、可制造或人体工学性能。

格式验证另用官方 Agent Skills `skills-ref`，CI 固定到提交 `69ef37e9424c0a7ea9dd2293b559e43ec8176379` 并使用 Python 3.14。安装该校验器后运行 `skills-ref validate skills/rhino-modeling`。这项检查验证标准元数据；客户端自带的旧版校验器可能尚不认识 `compatibility` 等标准字段，不能以此判断技能格式无效。

## 维护与许可

详细知识按任务读取，不必一次加载整个资料库。[官方来源](skills/rhino-modeling/references/sources.md)用于核查版本和适用条件；修改行为时运行能暴露问题的测试。公开内容只含通用方法与合成测试，不含客户模型或私人项目路径。

原创内容 [MIT](LICENSE)；第三方权利见 [NOTICE.md](NOTICE.md)。完整技能目录自带同样的许可和说明，可独立分发。

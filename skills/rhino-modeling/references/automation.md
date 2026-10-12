# Rhino 执行环境与作业

## 依赖和能力边界

| 路线 | 能力和依赖 | 边界 |
|---|---|---|
| 桌面 Rhino 8 | 有效许可；Windows/macOS；原生命令、视口、RhinoCommon | 插件及具体 API 随平台/版本变化；本机测试范围单列 |
| 本技能调度器 | 外部 Python 3.10+，仅标准库；官方 RhinoCode 从 Rhino 8.11 起提供 | 要有运行中实例及 ScriptServer；不是无安装的 CAD 引擎 [R01] |
| Rhino 内 Python 3 | Rhino 的 CPython、Python.NET、RhinoCommon；截图使用随 Rhino 提供的 .NET 图形接口 | 外部 Python 的版本/包不会自动复制到 Rhino；Python 2/IronPython 的重载与集合习惯不可照搬 [R02、R26] |
| rhino3dm | 可独立读取/写入 3DM、访问几何/属性/图层和部分操作 | 基于 OpenNURBS 的独立库，不等同完整 RhinoCommon 建模内核；不要假设可做原生布尔或 STEP 导出 [R25、R27] |
| Compute | 独立部署的 Rhino 运算服务与 REST 客户端，可解 GH 定义 | 服务端版本、许可、插件、文件格式支持须另核对；不等于本机视口或本技能 CLI [R27–R29] |

Linux 可运行本技能的纯 Python 检查，以及适配版本的 rhino3dm。官方另有 Linux Compute 指南，但核对时标为 Rhino WIP，不建议生产使用，非 3DM FileIO 与第三方插件仍有限制。不能把 Windows Rhino 8 的导出测试迁移声明为 Linux Compute 已通过。[R28] 常规 Rhino 8 Compute 的 Windows IIS 路线见 R29；部署不是使用此技能的前提。

## 从任意目录调用

把下方 `/absolute/skill` 换成包含此 `SKILL.md` 的实际目录。`--binary` 为全局参数，放在子命令前；也可设 `RHINO_CODE_BIN`。显式指定不存在的路径会失败。

```bash
python /absolute/skill/scripts/rhino_run.py env
python /absolute/skill/scripts/rhino_run.py --binary /absolute/rhinocode env
python /absolute/skill/scripts/rhino_run.py run --instance ACTUAL_ID --expected-doc /absolute/project/work.3dm --script /absolute/skill/scripts/native_job.py --job /absolute/jobs/inspect.json --output /absolute/results/inspect-run
```

路径含空格时按当前 shell 规则引用。CLI 返回安装版本与真实实例；先在目标 Rhino 中运行 `StartScriptServer`，本工具不修改全局启动设置。[R01] 网络不是本地作业依赖；查文档、安装软件/包或访问 Compute 才可能需要网络。

`--expected-doc @none` 仅接受无文档或没有对象的未命名文档，用于隔离合成测试。已有项目使用绝对文档路径；guard 在 Rhino 内再次核对，以免外部列举后用户切换文档。不要为了让测试通过关闭用户未保存的工作。

## 作业 JSON

`native_job.py` 使用调度器注入的 `JOB`、`OUT_DIR`；不能直接用外部 Python 运行。JSON 使用 UTF-8，路径为绝对路径。`sources` 必须非空且为不同的现存 `.3dm` 文件。

只读检查：

```json
{"mode":"inspect","sources":["/absolute/model.3dm"]}
```

输出 `<stem>.inspection.json`，包含源哈希、Rhino 版本、单位/公差、对象数量及类型统计，每对象包含 ID、名称、图层、类型、有效性、包围盒及可执行的 Brep/mesh 检查。其他类型保留身份并标记未运行的类型专项检查；不隐式转换、不修复、不覆盖源文件。`status: inspected` 表示检查完成，不表示所有几何达到制造要求。

单实体派生导出：

```json
{"mode":"export","sources":["/absolute/model.3dm"],"mesh_tolerance_mm":0.05,"minimum_edge_length_mm":0.0}
```

每文件必须恰有一个对象，且为有效、封闭、outward Brep，单位为 mm。混合对象、多个实体、Extrusion/SubD/块等不会被静默跳过或自动转换。需导出装配或保留辅助对象时，按明确对象 ID 在独立文档构造选集并另行验收；不能删除源对象满足限制。公差必须有限且为正，最小边长可为零；非零最小边长会约束细分，应复查采样偏差。

合成回归：

```json
{"mode":"synthetic","dimensions_mm":[24,36,18]}
```

在独立 headless 文档构造箱体及曲面样例，测试方向、缺面、导出回读和负向输入。尺寸是测试数据，不是工程默认。实现了测试入口不代表本次机器已经运行通过，见 [validation.md](validation.md)。

## 执行确认、缓存与失败

每次作业使用 UUID 与独立 `.dispatch-…` 请求/结果目录；只有匹配 token 的 `passed`/`failed` 是完成确认，CLI 返回零只可能表示排队。超时保留原作业信息，检查结果与实例后才能决定是否重试，不能自动重复提交。

内置作业按自身脚本绝对路径，每次重新读取并独立加载 sibling 模块，不依赖当前目录、`sys.path` 顺序、`sys.modules` 或时间戳字节码缓存。自定义脚本若另有 import，需要自行管理依赖和生命周期。

macOS Rhino 8.35 曾出现官方 shell launcher 展开带空格参数异常；调度器在相应安装结构存在时调用同一安装的 `RhinoCode.dll` 和 bundled dotnet，保持参数数组边界。此为记录过的适配，不能推断所有 Rhino/macOS 版本均有相同问题。

导出/检查先写独立 staging，验证完整批次后独占发布，不覆盖同名文件。Python 异常会撤回本批已发布文件；进程崩溃时多个平铺文件不能保证原子性，下游必须等完成 token。失败诊断保存在 `.dispatch-…/result.json`；不能把残留文件当成功交付。[delivery.md](delivery.md)

## 文档句柄与真实视口

`RhinoDoc.ActiveDoc`、`scriptcontext.doc`、MCP/插件注入的文档句柄、headless 文档和 GH 文档可能不同。读取具体接口契约；把核对过的句柄传给操作，不能混用 ActiveDoc 和注入句柄。活动文档修改使用撤销记录与受控对象 ID；无头文档完成后 Dispose。[R03]

`capture_views.py` 的 `views` 每项含 PNG 文件名、camera、target、bounds，可选 up；可设置 width、height 和已有 display_mode_id；图像宽高为正整数，每维不超过 16384，总像素不超过 6400 万。它在已核对的活动文档截图，完成后恢复相机、显示模式和网格。先确认可见对象；脚本不会自动隐藏用户内容。

欢迎/模板窗口可能没有文档或视口；headless 几何作业成功不代表可截图。需要视口时使用独立测试文档或明确目标文件，截取实际候选并验证恢复状态。

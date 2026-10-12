# Rhino 执行环境

来源 R01–R03、R17。Python 3.10+ 的外部调度器与 Rhino 内 Python 运行时分别处理；实际几何依赖安装且可运行的 Rhino。

```bash
python scripts/rhino_run.py env
python scripts/rhino_run.py run --instance ACTUAL_ID --expected-doc /absolute/project/work.3dm --script /absolute/skill/scripts/native_job.py --job /tmp/job.json --output /tmp/job-output
```

`env` 返回 CLI 版本和真实实例。Rhino 内须启动 ScriptServer（官方 `StartScriptServer`）；本工具不静默改全局启动设置。没有目标实例时报告，不向不明窗口发送命令。[R01]

`--expected-doc @none` 仅接受无文档或没有对象的未命名文档，用于隔离合成/无头测试。普通项目使用明确绝对文件路径。调度器在 Rhino 内再次检查路径，CLI 的外部检查不是唯一保护。

## 已处理的本机行为

Rhino 8.35 macOS 官方 shell launcher 对带空格参数展开不正确时，调用同一安装内的 `RhinoCode.dll` 和 bundled dotnet，并用 subprocess 数组传参。没有改变官方几何引擎，也不依赖第三方 MCP。其他平台使用发现的 CLI；未实测平台不标记已通过。

CLI 返回成功可能只表示排队。调度器为每次作业生成 UUID 和独立请求/结果目录，等到 Rhino 写出匹配 token 的 passed/failed 才结束。超时不立即重复提交，以免旧任务仍在执行。

## 作业类型

```json
{"mode":"synthetic","dimensions_mm":[24,36,18]}
```

在 headless 文档测试实体、镜像、缺面识别、3DM/STEP/STL 读写。尺寸是合成例子，不是工程默认。

```json
{"mode":"export","sources":["/absolute/model.3dm"],"mesh_tolerance_mm":0.05}
```

当前导出入口接受每文件一个封闭 outward Brep、mm 单位；输出 STL、网页可用三角网格 JSON 和验证 JSON。多实体装配需要明确对象选择，不能偷偷选第一件或把全部合成一体。

## 文档保护

在内存/无头文档计算几何；如果任务确需改活动文档，使用撤销记录、项目对象标签和已确认的对象 ID。不要仅凭易变边索引改形；脚本重新加载模块，避免旧缓存。

ActiveDoc、scriptcontext.doc、工具注入句柄、GH 文档可能不同；读取具体运行接口说明。不要把 Python 2/.NET 习惯无条件照搬 Python 3，尤其集合重载、ref/out 返回值和类型转换。[R02、R17]

## 真实视口截图

`capture_views.py` 接收 `views` 列表，每项含 PNG 文件名、camera、target、bounds，可选 up；作业可给 width、height 和已有 display_mode_id。它在已明确的活动文档内截图，完成后恢复相机/显示模式/网格。调用前确认场景可见内容；脚本不自动隐藏用户对象。

Rhino 停在欢迎/模板窗口时可能没有活动文档或视口，此时几何 headless 测试可以成功而截图无法进行。先通过原生界面打开目标文件，再按实际文档路径执行；不把空白欢迎窗口截图当模型。

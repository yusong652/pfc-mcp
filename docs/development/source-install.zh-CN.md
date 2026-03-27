# 开发者指南：从源码安装与运行

这份指南面向需要直接使用本地源码进行开发、在发布到 PyPI 之前验证修改，或将 bridge 从本地源码安装到 PFC 内嵌 Python 环境中的贡献者。

## 运行时拆分

这个仓库实际上包含两个独立运行时：

- `pfc-mcp`
  位于 [`src/pfc_mcp`](../../src/pfc_mcp) 的 MCP 服务端包，运行在标准 Python `>=3.10`
- `pfc-mcp-bridge`
  位于 [`pfc-mcp-bridge`](../../pfc-mcp-bridge) 的 bridge 包，运行在 PFC 内嵌 Python 中

虽然它们在同一个仓库里，但安装和验证时应当视为两个独立目标。

## 1. 克隆仓库并安装开发依赖

在仓库根目录执行：

```bash
uv sync --group dev
```

常用本地命令：

```bash
uv run pytest tests
uv run pfc-mcp
```

## 2. 让 MCP 客户端指向本地源码

如果你希望 MCP 客户端使用本地 checkout 而不是 PyPI 发布版，可以用 `uv run --directory` 指向仓库：

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/pfc-mcp", "pfc-mcp"]
    }
  }
}
```

这是验证 MCP 侧改动最简单的方式，不需要先构建或发布包。

## 3. 直接从源码启动 Bridge

如果你只是想让 bridge 侧代码修改在 PFC 中生效，其实不需要先安装 bridge 包。在 PFC 的 IPython 控制台里执行：

```python
%run C:/path/to/pfc-mcp/pfc-mcp-bridge/start_bridge.py
```

注意：

- 路径请使用正斜杠
- `%run` 后面的路径不要加引号
- 修改 bridge 源码后需要重启 bridge

这是 bridge 开发时最快的工作流。

## 4. 将 Bridge 从本地源码安装到内嵌 Python

如果你要验证“包安装路径”本身，而不只是直接 `%run`，建议从终端调用 PFC 的内嵌 Python 解释器，把 `pfc-mcp-bridge` 从本地源码安装进去。

先根据 PFC 版本选择正确解释器：

- PFC `6.0` / `7.0`：`C:/Program Files/Itasca/.../exe64/python36/python.exe`
- PFC `9.0`：`C:/Program Files/Itasca/.../exe64/python310/python.exe`

示例命令：

```powershell
& "C:\Program Files\Itasca\PFC700\exe64\python36\python.exe" -m pip install --user -e C:\path\to\pfc-mcp\pfc-mcp-bridge
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -m pip install --user -e C:\path\to\pfc-mcp\pfc-mcp-bridge
```

为什么推荐在终端里直接调用内嵌解释器：

- 安装目标就是 PFC 实际使用的那个 Python 环境
- 不依赖在 PFC 控制台里通过 `subprocess` 再起一个解释器
- 对 editable install 来说最稳定

bridge 包会自动拉取匹配的 `websockets` 版本：

- Python `3.6` -> `websockets==9.1`
- Python `3.10` -> `websockets==16.0`

## 5. 在 PFC IPython 中安装

如果你是在 PFC 控制台里直接安装 PyPI 版本，请使用主 README 中那段按版本分支的安装代码：

- PFC `6.0` / `7.0`：`pip.main(...)`
- PFC `9.0`：`pip._internal.cli.main.main(...)`

如果是“从源码安装”，更推荐使用上面第 4 步那种“终端 + 内嵌解释器”的方式，而不是在 PFC GUI 控制台里尝试驱动 editable install。

## 6. 验证环境

可以先在内嵌 Python 里检查 bridge 包和 `websockets`：

```powershell
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -c "import pfc_mcp_bridge, websockets; print(pfc_mcp_bridge.__version__); print(websockets.__version__)"
```

然后在 PFC 中启动 bridge，并从 MCP 客户端验证：

1. 在 PFC 中执行 `pfc_mcp_bridge.start()` 或 `%run .../start_bridge.py`
2. 重启 MCP 客户端会话
3. 调用 `pfc_list_tasks`

## 7. 推荐开发循环

对于大多数日常开发，推荐这样做：

1. 执行 `uv sync --group dev`
2. 用 `uv run --directory` 让 MCP 客户端指向本地源码
3. 在 PFC 中用 `%run .../pfc-mcp-bridge/start_bridge.py` 启动 bridge
4. 执行 `uv run pytest tests`
5. 修改后按需重启 MCP 客户端和 bridge

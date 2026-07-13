# Data Viewer

DataViewer 是一款桌面股票行情悬浮窗。它在桌面上以紧凑形式展示自选股价格和涨跌幅，并支持托盘菜单、全局快捷键、自选股管理及多种显示模式。

本仓库只包含开源客户端。行情服务端、数据源凭据、缓存与部署配置不包含在本仓库中。

## 功能

- 展示沪深股票价格和涨跌幅
- 在拼音、中文名称及精简价格模式之间切换
- 通过界面添加、删除和排序自选股
- 使用系统托盘控制窗口
- 使用全局快捷键显示或隐藏悬浮窗
- 支持 Windows 和 macOS 源码构建

## 环境准备

建议使用 Python 3.11 或更新的稳定版本。创建虚拟环境并安装依赖：

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 开发运行

从项目根目录进入客户端目录后启动：

```powershell
cd client
python main.py
```

首次运行需要阅读并接受风险免责声明。程序启动后默认驻留系统托盘；可通过托盘菜单管理自选股和显示模式。

默认快捷键为 `Ctrl+F3`。配置保存在 `config.json`；正常使用时建议通过界面修改，而不是手动编辑。

## 构建发行包

Windows：

```powershell
.\build-client.ps1
```

生成文件位于 `dist/`。

macOS：

```bash
chmod +x build-client-macos.sh
./build-client-macos.sh
```

macOS 构建必须在 macOS 上执行。未签名应用可能被系统安全机制拦截；公开分发时建议进行开发者签名和公证。

## 项目结构

```text
client/                  客户端源码、图标、默认配置及 PyInstaller 配置
build-client.ps1         Windows 构建脚本
build-client-macos.sh    macOS 构建脚本
requirements.txt         Python 依赖
SECURITY.md              安全问题报告方式
```

## 风险声明

软件展示的行情仅用于学习、研究和信息参考，不构成投资建议或交易依据。数据可能延迟、遗漏、错误或中断。证券市场具有风险，用户应独立核验信息并自行承担决策后果。

## 参与贡献

欢迎通过 Issue 报告问题或提出建议。提交代码前，请确保客户端能够通过 Python 语法编译，并且不要提交 Token、密钥、个人配置、构建产物或其他敏感信息。

## 许可证

本项目使用 Apache License 2.0，详见 [LICENSE](LICENSE)。

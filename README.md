# 客户跟进 / Desktop Customer Follow-up

一个轻量的 Windows 桌面客户跟进备忘工具：无边框、可贴边停靠、始终置顶，数据全部本地存储。
最初是个桌面备忘录，后来按客户跟进场景重做。

A lightweight Windows desktop app for tracking customer follow-ups. Frameless, edge-snapping,
always-on-top window with fully local storage. Built with PySide6 (Qt WebEngine) + a single HTML UI.

## 功能 Features

- **三种状态**：未跟进 / 今日已跟进 / 结束跟进
  - “今日已跟进”由「最后跟进时间是否在今天」推导，**次日自动回落为未跟进**，贴合每日跟进节奏
- **状态色**：未跟进=琥珀、今日已跟进=绿、结束跟进=灰
- **自动优先级排序**（未跟进页）：到期提醒 → 最久没碰 → 已排期未到期
- **下次跟进提醒**：到点高亮、排到最前；与“距上次跟进多久”是两个独立信号
- **跟进备注**：每次跟进可记一句“聊了什么 / 下一步”
- **变更日志**：每个操作追加写入 `activity.jsonl`（append-only），可在应用内查看 / 复制（用于写周报）
- **滚动备份**：每次保存自动保留最近 5 份 `memos.bak.N.json`
- **窗口**：无边框、贴左 / 贴右 / 自由、置顶切换，窗口状态记忆

## 数据位置 Data location

所有数据存在当前用户目录，**不随程序分发**：

```
%APPDATA%\DesktopMemo\桌面备忘录\
  ├─ memos.json            # 主数据
  ├─ activity.jsonl        # 变更日志
  ├─ memos.bak.1..5.json   # 滚动备份
  └─ window.json           # 窗口位置/大小
```

## 从源码运行 Run from source

```bash
pip install PySide6
python app.py
```

## 打包 Build

```bash
# 1) 打包成 onedir 可执行
pip install pyinstaller
pyinstaller --noconfirm --windowed --onedir --name "DesktopMemo" --add-data "index.html;." app.py

# 2)（可选）用 Inno Setup 编译安装程序
#    安装 Inno Setup 6 后：
ISCC installer.iss
```

下载已编译的安装程序见 [Releases](../../releases)。

> 安装程序未做代码签名，首次运行 Windows SmartScreen 会提示
> “Windows 已保护你的电脑” → 点 **更多信息 → 仍要运行** 即可。

## 技术说明 Notes

- UI 是单个 `index.html`，Qt 端 (`app.py`) 提供无边框窗口 + 持久化桥接
- 持久化走 `console.log` 打标签的方式传给 Python 写文件，避开 `file://` 下的 localStorage 限制
- 状态为**推导式**（由 `lastFollowUpAt` / `closed` 算出），不存死字符串，所以能自动按天滚动
- 日志条目**自包含**（快照客户名 + 状态），客户即使被改名/删除，历史日志仍可读

## License

MIT © [lanterner3054](https://github.com/lanterner3054)

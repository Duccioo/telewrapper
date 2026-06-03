# 🤖 TeleWrapper

> **Remote command monitoring made simple** — Execute any command and get real-time updates directly on Telegram with live system stats.

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Live Dashboard** | Single auto-updating Telegram message with command output |
| 🖥️ **System Monitoring** | Real-time CPU, RAM usage tracking |
| 🎮 **GPU Support** | NVIDIA GPU utilization & VRAM stats (via `pynvml`) |
| 🌐 **Multi-Host Ready** | Run on multiple machines with the same bot token |
| ⏱️ **Execution Timer** | Track how long your commands have been running |
| 🎛️ **Remote Control** | Terminate processes or close wrapper via inline buttons |
| 🖥️ **Cross-Platform** | Works on Windows, macOS, and Linux |
| 📈 **Progress Bar Support** | Smart handling of `tqdm` and `rich` progress bars, with proper terminal emulation |
| 💾 **Log Saving** | Use `--log` to automatically save the full command output locally and download it via Telegram |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/duccioo/telewrapper.git
cd telewrapper

# Install the package
pip install .
```

**Dependencies:** Automatically installed via pip
- `python-telegram-bot>=20.0`
- `psutil`
- `pynvml` (optional, for NVIDIA GPU stats)

---

## ⚙️ Configuration

### Option 1: Environment Variables (Recommended)

```bash
export TELEGRAM_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

### Option 2: Command Line Arguments

```bash
telewrapper --token "your_token" --chat_id "your_chat_id" "your_command"
```

### Option 3: Config File (YAML or INI)

Create a config file and pass it with `--config`:

**YAML format** (recommended):
```yaml
telegram:
  token: your_bot_token_here
  chat_id: your_chat_id_here

settings:
  update_interval: 5.0  # seconds between dashboard updates
```

**INI format** (legacy):
```ini
[Telegram]
token = your_bot_token_here
chat_id = your_chat_id_here

[Settings]
update_interval = 5.0
```

---

## 🚀 Usage

### Basic Usage

```bash
# Run any command
telewrapper "python train.py"

# Run a long-running script
telewrapper "python -u my_training_script.py --epochs 100"

# Test your bot connection
telewrapper --test
```

### What You'll See on Telegram

```
🖥 MacBook-Pro (PID: 12345)
⚙️ python train.py

Status: 🟢 Running
Time: 1:23:45
CPU: 45% | RAM: 62%
GPU 0: 87% | VRAM: 8.2/24.0GB (34%)

📜 Recent Log (Last 50):
┌──────────────────────────────
│ Epoch 15/100
│ Loss: 0.0234, Accuracy: 98.7%
│ Validation: 97.2%
│ ...
└──────────────────────────────

[🔄 Refresh] [🛑 Terminate Process]
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                 TeleWrapper                  │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐     ┌─────────────────┐   │
│  │   Command   │────▶│   Log Buffer    │   │
│  │   Process   │     │  (Last 50 lines)│   │
│  └─────────────┘     └────────┬────────┘   │
│                               │            │
│  ┌─────────────┐              │            │
│  │   System    │              │            │
│  │   Monitor   │──────────────┤            │
│  │ (CPU/RAM/GPU)              │            │
│  └─────────────┘              │            │
│                               ▼            │
│                    ┌─────────────────┐     │
│                    │    Telegram     │     │
│                    │    Dashboard    │     │
│                    │  (Auto-update)  │     │
│                    └─────────────────┘     │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📋 Command Line Options

| Option | Description |
|--------|-------------|
| `command` | The command to execute (wrap in quotes) |
| `--token` | Telegram Bot Token |
| `--chat_id` | Telegram Chat ID |
| `--config` | Path to configuration file |
| `--log` | Save full command output to a file and enable download button |
| `--test` | Run a connection test |

---

## 🔧 How to Get Your Telegram Credentials

### 1. Create a Bot Token
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Copy the token provided

### 2. Get Your Chat ID
1. Start a chat with your new bot
2. Send any message to the bot
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Look for `"chat":{"id":XXXXXXXX}` — that's your Chat ID

---

## 💡 Tips & Best Practices

- 🐍 Use `python -u` for unbuffered Python output
- 📝 The dashboard shows the **last 50 lines** of output
- ⏰ Dashboard updates every **5 seconds** (configurable via `update_interval`)
- 🖥️ GPU stats only appear if NVIDIA GPU is detected
- 🔄 Use the **Refresh** button for immediate updates
- 📈 Progress bars (tqdm, etc.) are automatically handled and display correctly

---

## 🖥️ Platform Support

| Platform | Terminal Emulation | Notes |
|----------|-------------------|-------|
| **Linux** | PTY (full) | Best support, native terminal emulation |
| **macOS** | PTY (full) | Native terminal emulation |
| **Windows** | PIPE | Subprocess with line-buffered output |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ for remote monitoring
</p>

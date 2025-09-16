# 🌍 Multilingual Translator Telegram Bot

A **Telegram bot** that translates text and voice messages between multiple languages.  
It uses **Speech Recognition, Google Translate, gTTS (Text-to-Speech)**, and **Pydub** to provide a complete translation assistant with both **text and audio outputs**.

---

## ✨ Features
- 🔤 **Text Translation** – Send any text in one language and get instant translation.
- 🎙 **Voice Translation** – Record and send voice messages, bot transcribes & translates.
- 🗣 **Text-to-Speech** – Translations are also returned as voice messages.
- 🌎 **Supports 100+ Languages** for both text & speech.
- 🔄 **Retry Mechanism for Voice Downloads** – More stable voice handling.
- 📖 **Language Auto-Detection** – Detects the source language automatically.
- 🎛 **Interactive Menus** – Choose mode (Text/Voice), source language, and target language with inline keyboards.
- 🛠 **Error Handling** – Graceful error handling with user-friendly messages.

---

## 🛠 Tech Stack
- **Python 3.12 / 3.13**
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) – Speech-to-Text
- [gTTS](https://pypi.org/project/gTTS/) – Text-to-Speech
- [Pydub](https://pypi.org/project/pydub/) – Audio conversion
- [Deep Translator](https://pypi.org/project/deep-translator/) – Translations
- [Detect Language](https://pypi.org/project/detectlanguage/) – Language detection
- [python-telegram-bot](https://python-telegram-bot.org/) – Telegram Bot API wrapper
- [FFmpeg](https://ffmpeg.org/) – Required for audio processing

---

## 📦 Installation

### 1️ Clone the repo
    ```bash
    git clone https://github.com/yourusername/translator-telegram-bot.git
    cd translator-telegram-bot

### Install dependencies
    ```bash
     SpeechRecognition
     gTTS
     pydub
     deep-translator
     detectlanguage
     python-telegram-bot

### Install FFmpeg

Windows: Download from FFmpeg.org
, extract, and add to PATH.

Linux:
   
    sudo apt-get install ffmpeg

🔑 Setup

Get a Telegram Bot Token from @BotFather

Replace the token inside main():
   ```bash
      .token("YOUR_TELEGRAM_BOT_TOKEN")

    Add your DetectLanguage API key
 in the code:

configuration.api_key = "YOUR_API_KEY"

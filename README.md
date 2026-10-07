<div align="center">

# 🤖 DailyCodeAgent Gemini

**Gemini AI bilan har kuni 7 tilda kod yarating va GitHub’ga avtomatik yuklang.**  
**Ежедневная генерация учебного кода на 7 языках и загрузка в GitHub.**  
**Generate educational code in 7 languages daily and upload it to GitHub.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini_AI-8E75B2?logo=google&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-API-181717?logo=github)

[O‘zbekcha](#ozbekcha) · [Русский](#русский) · [English](#english)

</div>

---

## O‘zbekcha

### Imkoniyatlari

Agent har kuni Gemini API yordamida PHP, Python, Java, JavaScript, C, C# va C++ tillarida bittadan kichik o‘quv dasturi yaratadi. Natijalar private GitHub repozitoriyga quyidagi tartibda yuklanadi:

```text
daily/YYYY-MM-DD/
├── php/main.php
├── python/main.py
├── java/Main.java
├── javascript/main.js
├── c/main.c
├── csharp/Program.cs
└── cpp/main.cpp
```

- Bir kunda qayta generatsiya va takroriy commit qilmaydi.
- Uzilishdan keyin cache orqali ishni davom ettiradi.
- Bir vaqtda ikki nusxa ishlashini bloklaydi.
- AI yaratgan kodni avtomatik bajarmaydi.
- Token va API kalitlarini GitHub’ga yuklamaydi.

### Talablar va kutubxonalar

- Windows 10/11
- Python 3.10 yoki yangiroq
- GitHub hisobi va personal access token
- Google AI Studio’dan Gemini API key
- Internet

Tashqi Python kutubxonasi kerak emas. Loyiha faqat standart kutubxonalardan foydalanadi, shu sababli `pip install` bajarilmaydi.

```powershell
python --version
```

### O‘rnatish va sozlash

```powershell
git clone https://github.com/USERNAME/daily-code-agent-gemini.git
cd daily-code-agent-gemini
Copy-Item credentials.example.txt credentials.txt
```

`credentials.txt` faylini to‘ldiring:

```text
GITHUB_USERNAME=github_username
GITHUB_TOKEN=github_token
GEMINI_API_KEY=gemini_api_key
COMMIT_EMAIL=github_email
GEMINI_MODEL=gemini-3.5-flash-lite
```

GitHub tokeni: **Settings → Developer settings → Personal access tokens → Fine-grained tokens**. Token private repo yaratish va repository contents yozish ruxsatlariga ega bo‘lishi kerak. GitHub parolini dasturga yozmang. Gemini kalitini Google AI Studio’dan oling.

### Ishga tushirish

`RUN.cmd` faylini ikki marta bosing yoki terminalda:

```powershell
python daily_code_agent.py
```

Birinchi ishga tushishda token egasi tekshiriladi, tasodifiy nomli private repo yaratiladi, uning manzili `repository.txt`ga saqlanadi va 7 ta kod GitHub’ga yuklanadi.

Har kuni 09:23 da avtomatik ishlatish:

```powershell
powershell -ExecutionPolicy Bypass -File .\SETUP.ps1
```

Kompyuter o‘chiq bo‘lsa, agent belgilangan vaqtda ishlamaydi; Windows uni keyingi imkoniyatda ishga tushiradi.

### Test

```powershell
python -m unittest -v test_agent.py
```

---

## Русский

### Возможности

DailyCodeAgent ежедневно создаёт небольшие учебные программы на PHP, Python, Java, JavaScript, C, C# и C++ через Gemini API и загружает их в приватный репозиторий GitHub.

- Не генерирует код и коммиты повторно в тот же день.
- Продолжает работу из cache после прерывания.
- Не позволяет запускать две копии одновременно.
- Не выполняет сгенерированный AI код.
- Не отправляет токены и ключи API в GitHub.

### Требования и зависимости

Нужны Windows 10/11, Python 3.10+, интернет, аккаунт GitHub, personal access token и Gemini API key. Сторонние библиотеки не нужны: проект использует только стандартную библиотеку Python, поэтому `pip install` не требуется.

### Установка

```powershell
git clone https://github.com/USERNAME/daily-code-agent-gemini.git
cd daily-code-agent-gemini
Copy-Item credentials.example.txt credentials.txt
```

Заполните `credentials.txt`:

```text
GITHUB_USERNAME=имя_пользователя
GITHUB_TOKEN=токен_github
GEMINI_API_KEY=ключ_gemini
COMMIT_EMAIL=email_github
GEMINI_MODEL=gemini-3.5-flash-lite
```

Fine-grained token создаётся в **GitHub Settings → Developer settings → Personal access tokens**. Ему нужны права на создание приватного репозитория и запись его содержимого. Ключ Gemini создаётся в Google AI Studio.

### Запуск и расписание

Дважды нажмите `RUN.cmd` или выполните:

```powershell
python daily_code_agent.py
```

Для ежедневного запуска в 09:23:

```powershell
powershell -ExecutionPolicy Bypass -File .\SETUP.ps1
```

Запуск тестов:

```powershell
python -m unittest -v test_agent.py
```

`credentials.txt`, журналы, cache и служебные файлы исключены через `.gitignore`.

---

## English

### Features

DailyCodeAgent uses the Gemini API every day to generate a small educational program in PHP, Python, Java, JavaScript, C, C#, and C++, then uploads the files to a private GitHub repository.

- Avoids duplicate generation and commits on the same day.
- Recovers from interruption using a local cache.
- Prevents two agent instances from running together.
- Never executes AI-generated source code automatically.
- Keeps tokens and API keys out of GitHub.

### Requirements and dependencies

You need Windows 10/11, Python 3.10+, internet access, a GitHub account, a personal access token, and a Gemini API key. No third-party Python packages are required; the project uses only the Python standard library, so there is no `pip install` step.

### Installation

```powershell
git clone https://github.com/USERNAME/daily-code-agent-gemini.git
cd daily-code-agent-gemini
Copy-Item credentials.example.txt credentials.txt
```

Fill in `credentials.txt`:

```text
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_token
GEMINI_API_KEY=your_gemini_api_key
COMMIT_EMAIL=your_github_email
GEMINI_MODEL=gemini-3.5-flash-lite
```

Create a fine-grained token under **GitHub Settings → Developer settings → Personal access tokens**. It needs permission to create a private repository and write repository contents. Create the Gemini API key in Google AI Studio.

### Run and schedule

Double-click `RUN.cmd`, or run:

```powershell
python daily_code_agent.py
```

Schedule it every day at 09:23 local time:

```powershell
powershell -ExecutionPolicy Bypass -File .\SETUP.ps1
```

Run the tests:

```powershell
python -m unittest -v test_agent.py
```

`credentials.txt`, logs, cache, and local service files are excluded through `.gitignore`.

---

<div align="center">

Made with Python, Gemini AI and the GitHub API.

</div>

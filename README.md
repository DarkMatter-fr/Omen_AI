# OMEN Jarvis Assistant (Beta v0.8) 🤖

A sleek, voice-activated desktop assistant powered by **Gemini 2.0** and **Python Eel**. Jarvis combines a modern web-based UI with powerful background automation to provide a high-performance AI experience.

> **⚠️ BETA PHASE NOTICE:** This project is currently in active development. You may encounter bugs, and features are subject to change. Feedback from beta testers is highly appreciated.

---

## ✨ Features
* **Voice Recognition:** Hands-free command processing.
* **AI Intelligence:** Powered by Google's latest Gemini 2.0 models.
* **Web Scraping:** Real-time information retrieval using `undetected-chromedriver`.
* **Modern UI:** A beautiful, responsive interface built with HTML/CSS and Eel.

---

## 🛠 Prerequisites

Before running Jarvis, ensure you have the following installed:
* **Python 3.12 or 3.13** (Recommended)
* **Google Chrome** (Required for the UI and Automation modules)
* **A Google Gemini API Key** (Get one for free at [Google AI Studio](https://aistudio.google.com/))

---

## 🚀 Installation & Setup

Follow these steps to get your local beta instance running:

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
cd YOUR_REPO_NAME
2. Install Required Libraries
Run the following command to install all necessary dependencies:

Bash
pip install eel google-genai undetected-chromedriver speechrecognition pyttsx3 python-dotenv
3. Configure Your API Key
For security reasons, the config.py file is excluded from this repository. You must create it manually in the root directory.

Create a file named config.py.

Paste the following code into the file and replace the placeholder with your actual key:

Python
# config.py
GEMINI_KEY = "YOUR_ACTUAL_API_KEY_HERE"
🖥️ How to Run
Once the libraries are installed and your config.py is ready, launch the assistant by running:

Bash
python main.py
🧪 Beta Testing Notes
Microphone: Ensure your default system microphone is active before launching.

Search: If a browser window pops up briefly during a search, do not close it manually; it will close itself once the data is retrieved.

UI: Use the circular orb to trigger the listening sequence.

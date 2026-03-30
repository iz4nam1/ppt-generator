# 🎯 PPT Generator — AI-Powered Presentation Builder

Generate professional PowerPoint presentations in seconds — from just a topic or an uploaded document. Powered by Google Gemini, Grok, and more.

---

## ✨ What It Does

PPT Generator takes either:
- **A topic** (e.g. "Climate Change", "Machine Learning Basics") — and generates a full, structured presentation from scratch
- **An uploaded document** (PDF, text, notes) — and converts it into clean, slide-ready content

The AI handles slide structure, titles, bullet points, and layout logic. You get a ready-to-use `.pptx` file you can open directly in PowerPoint or Google Slides.

---

## 🚀 Features

- 📝 **Topic-to-slides** — type any subject and get a complete presentation
- 📄 **Document-to-slides** — upload notes or a PDF and convert to slides automatically
- 🤖 **Multi-model AI support** — works with Google Gemini, Grok, and more
- 📊 **Real `.pptx` output** — not a web preview, an actual downloadable PowerPoint file
- 🌐 **Simple web interface** — HTML frontend, no complex setup needed
- ⚡ **Fast generation** — Python backend handles everything server-side

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python (Flask / FastAPI) |
| AI Models | Google Gemini, Grok |
| File Generation | python-pptx |

---

## 📁 Project Structure

```
ppt-generator/
├── backend/
│   ├── app.py              # Main server entry point
│   ├── generator.py        # AI prompt logic + slide builder
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # API keys template
│
└── frontend/
    └── index.html          # Web UI for topic input & file upload
```

---

## ⚙️ Setup & Installation

### 1. Clone the repo

```bash
git clone https://github.com/iz4nam1/ppt-generator.git
cd ppt-generator
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your API keys:

```
GEMINI_API_KEY=your_gemini_api_key_here
GROK_API_KEY=your_grok_api_key_here
```

Start the server:

```bash
python app.py
```

### 3. Frontend Setup

Just open `frontend/index.html` in your browser, or serve it with:

```bash
cd frontend
npx serve .
```

---

## 🧠 How It Works

1. User enters a **topic** or uploads a **document** via the web UI
2. The Python backend sends the input to the selected AI model (Gemini / Grok)
3. The AI returns structured slide content (titles, bullet points, sections)
4. `python-pptx` renders it into a properly formatted `.pptx` file
5. The file is returned to the user as a download

---

## 📦 Dependencies

```
python-pptx
flask
google-generativeai
requests
python-dotenv
```

Install all with:

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROK_API_KEY` | Grok (xAI) API key |

Get your keys:
- Gemini: https://aistudio.google.com/app/apikey
- Grok: https://console.x.ai

---

## 💡 Use Cases

- Students generating presentation drafts from cluster of codes
- Professionals turning reports into slide decks instantly
- Anyone who dreads making PowerPoints from scratch

---

## 🔮 Future Improvements

- [ ] Custom themes and color schemes
- [ ] Add charts and image generation per slide
- [ ] More AI model options (Claude, GPT-4o)
- [ ] One-click export to Google Slides
- [ ] Slide preview in browser before download

---

## 👤 Author

Built by [iz4nam1](https://github.com/iz4nam1) — solo project, AI-assisted development.

---

## 📄 License

MIT License — use freely, customize as needed.

# 🚢 Intelli-Credit Ark

**Intelli-Credit Ark** is an interactive, AI-powered credit analysis platform designed to automate the generation of institutional-grade credit memorandums. Featuring a retro "bank lobby" interface, the system uses a multi-agent pipeline to classify documents, extract financial metrics, research market sentiment, and synthesize a final lending recommendation.

## 🌟 Key Features

- **Interactive Bank Lobby:** A gamified UI where you control a character to submit documents for processing.
- **Multi-Agent Pipeline:** Built with **LangGraph**, orchestrating four specialized agents:
  - 🔍 **Classifier:** Automatically identifies document types (Annual Reports, Bank Statements, etc.).
  - 📊 **Extractor:** A RAG-based (Retrieval-Augmented Generation) agent that pulls key financials from PDFs.
  - 🌐 **Researcher:** Performs live web searches to gather recent market sentiment and news.
  - 📝 **Synthesizer:** Compiles all data into a professional SWOT analysis and credit memo.
- **Professional PDF Generation:** Download formal credit memos directly from the browser.
- **Local & Private:** Optimized for local inference using **Ollama** and **ChromaDB**.

## 🚀 How it Works

The system follows a structured "Assembly Line" workflow:
1. **Submission:** Upload a PDF (e.g., an Annual Report) at the reception desk.
2. **Analysis:** The document travels across the "conveyor belt" to different agent desks.
3. **Real-Time Updates:** Each agent provides live status updates via SSE (Server-Sent Events).
4. **Final Verdict:** Download a comprehensive PDF report with extracted metrics and a final lend/no-lend recommendation.

## 🛠️ Tech Stack

- **Frontend:** React, Vite, Vanilla CSS.
- **Backend:** Python (FastAPI), LangChain, LangGraph.
- **LLM Engine:** Ollama (Qwen 2.5).
- **Vector DB:** ChromaDB.
- **Documentation:** jsPDF for automated reports.

## 📸 Screenshots

*(Add your screenshots here)*

---

## 🏗️ Installation & Setup

### 1. Prerequisites
- **Ollama:** Install from [ollama.ai](https://ollama.ai) and pull the Qwen 2.5 model:
  ```bash
  ollama pull qwen2.5:latest
  ```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

Developed for high-speed, automated credit risk assessment.

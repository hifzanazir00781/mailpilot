# MailPilot — AI Email Operations Platform

A multi-tenant Generative AI platform that automates organizational email operations using LangGraph multi-agent orchestration, Google Gemini 3.6 Flash, and RAG (Retrieval Augmented Generation).

---

## 🎯 Features

- **Multi-Tenant Authentication** — Organization and Individual workspaces with row-level security
- **AI Email Classification** — Auto-categorizes emails (Billing, Technical Support, Sales, Spam, General) with 4 priority levels
- **Auto Ticket Generation** — Creates structured support tickets with unique IDs (TKT-XXXXXX)
- **RAG-Powered Reply Drafting** — Drafts professional replies using organization-specific knowledge base
- **Knowledge Base Management** — Upload PDF/TXT documents for AI-powered context retrieval
- **Intelligent Chatbot** — Multi-language support (English, Roman Urdu, Urdu) with scope guardrails
- **Real-Time Dashboard** — Ticket tracking with filters, color-coded priorities, status updates

---

## 🏗️ Architecture

User → Streamlit UI → LangGraph Pipeline → Gemini 3.6 Flash → SQLite + ChromaDB → Classifier → Ticket Generator → Reply Drafter

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **AI Framework:** LangGraph + LangChain
- **LLM:** Google Gemini 3.6 Flash
- **Embeddings:** Gemini gemini-embedding-001
- **Vector DB:** ChromaDB
- **Database:** SQLite (multi-tenant with row-level security)
- **Auth:** bcrypt + session tokens
- **Language:** Python 3.13

---

## 📦 Installation

1. Clone the repo: `git clone https://github.com/hifzanazir00781/mailpilot.git`
2. Navigate: `cd mailpilot`
3. Install dependencies: `pip install -r requirements.txt`
4. Create .env file: Add `GEMINI_API_KEY=your_api_key_here`
5. Initialize database: `python backend/db.py`
6. Run the app: `python -m streamlit run app.py`

---

## 🔑 Usage

1. **Register** as Organization (official email) or Individual (personal email)
2. **Login** with your credentials
3. **Dashboard** — view, filter, and manage AI-generated tickets
4. **Knowledge Base** — upload PDF/TXT documents to train AI replies
5. **Chatbot** — ask questions, create tickets, or draft replies
6. **Process Emails** — pipeline automatically classifies and generates tickets

---

## 📂 Project Structure

```
mailpilot/
├── app.py                    # Main entry (login/register)
├── agents/                   # AI agents
│   ├── classifier.py         # Email classification
│   ├── ticket_generator.py   # Ticket creation
│   ├── reply_drafter.py      # RAG-based reply drafting
│   ├── rag_agent.py          # Vector retrieval
│   ├── chatbot_agent.py      # Chatbot logic
│   ├── state.py              # LangGraph state
│   └── graph.py              # Orchestration pipeline
├── backend/                  # Backend logic
│   ├── db.py                 # Database
│   ├── auth.py               # Login/Register
│   ├── security.py           # Password hashing
│   └── vector_store.py       # ChromaDB setup
├── ui/pages/                 # Streamlit pages
│   ├── 1_Dashboard.py
│   ├── 2_Chatbot.py
│   └── 3_Knowledge_Base.py
└── integrations/
    └── email_ingest.py
```

## 📊 Dataset / Data Sources

No external dataset used. This project uses:
- **Google Gemini 3.6 Flash** — Pretrained LLM (no custom training)
- **Custom Demo Data** — Test emails and knowledge base documents (TXT/PDF) created for demonstration
- **Prompt Engineering Approach** — No fine-tuning required

Future work: Add real email datasets for fine-tuning domain-specific models.

---

## 🎓 Key Learnings

- Multi-agent orchestration with LangGraph
- RAG implementation with ChromaDB + Gemini embeddings
- Multi-tenant SaaS architecture (row-level security)
- Prompt engineering + structured LLM output
- Error handling with exponential backoff retry
- Hallucination control via RAG confidence threshold
- Language-aware chatbot with scope guardrails

---

## 🚀 Future Work

- Gmail/Outlook OAuth integration
- Spam/phishing detection agent
- Human-in-the-loop escalation workflow
- Cloud deployment (Streamlit Cloud + FastAPI)
- Multi-session chat with persistent context

---

## 👤 Author

**Hifza Nazir** — Generative AI Intern at ATS (Advanced Telecom Services)

- GitHub: @hifzanazir00781
- Project Repo: mailpilot

---

## 📄 License

MIT License

# 🤖 IntelliAssist – AI Personal Scheduling & Travel Assistant

IntelliAssist is an **AI-powered personal assistant** that helps users manage their calendar, meetings, and travel plans using natural language.  
It combines **LLM reasoning, RAG (Retrieval-Augmented Generation), MCP tools, and a Streamlit UI** to deliver a smart, context-aware assistant.

---

## 🚀 Features

### 📅 Smart Scheduling
- Book meetings using natural language  
- Detect conflicts automatically  
- Suggest rescheduling options  
- Weekend & working-hour validation  
- Urgent meeting handling  

### 🗓 Calendar Management
- View calendar for any date  
- Cancel meetings  
- Update existing events  
- Conflict detection  

### ✈ Travel Assistance
- Search flights between cities  
- Natural language date support (e.g., “next Tuesday”, “tomorrow”)  
- Integration with Amadeus Flight API  

### 🧠 Intelligent Reasoning
- Natural language understanding  
- Context retention  
- Multi-step reasoning  
- Tool-calling via LangChain Agents  

### 📚 RAG (Retrieval Augmented Generation)
- Uses policies, patterns, and preferences  
- Improves decision accuracy  
- Personalized assistant behavior  

### 🔗 MCP (Model Context Protocol)
- Middleware for tool execution  
- Async and secure tool communication  
- Scalable architecture  
- Decouples LLM from APIs  

### 🖥 Interactive UI
- Streamlit-based interface  
- Chat mode  
- Booking mode  
- Flight search mode  

### 🔔 Notifications
- Email notifications for urgent bookings and changes  

---

## 🏗️ Project Architecture

```bash
Personal-Assistant/
│
├── app/
│   ├── __init__.py
│   ├── agent.py                 # Main agent logic & tool orchestration
│   ├── availability.py          # Availability & conflict evaluation
│   ├── calendar_reader.py       # Google Calendar read/create/update
│   ├── executables.ipynb        # Testing & experimentation notebook
│   ├── requirements.txt         # Python dependencies
│   ├── state.py                 # Agent state management (confirmations, memory)
│   └── tools.py                 # Scheduling, notification & flight tools
│
├── assistant_mcp/
│   ├── __init__.py
│   ├── client.py                # MCP client for tool calls
│   └── server.py                # MCP server exposing tools over HTTP
│
├── data/
│   ├── patterns/
│   │   └── past_scheduling_patterns.md   # Historical scheduling behavior
│   ├── policies/
│   │   └── company_travel_policy.md      # Travel rules & constraints
│   └── preferences/
│       └── user_preferences.md          # User-specific preferences
│
├── rag/
│   ├── faiss_index/
│   │   ├── index.faiss        # Vector index
│   │   └── index.pkl          # Metadata store
│   ├── ingest.py              # Document ingestion pipeline
│   ├── retriever.py           # Context retrieval logic
│   ├── test_retriever.py      # Retriever tests
│   └── vector_store.py        # FAISS vector store management
│
├── ui.py                      # Streamlit user interface
├── .gitignore
└── README.md
```

---

## 🛠 Tech Stack

- Python  
- LangChain Agents  
- OpenAI / LLM  
- FAISS Vector Database  
- Google Calendar API  
- Amadeus Flight API  
- Streamlit  
- MCP (Model Context Protocol)  
- Resend Email API  
- Dateutil  

---

## 🔄 How It Works

1. **User Input** – Natural language query from UI  
2. **Agent Processing** – LLM decides whether to reason or call a tool  
3. **RAG Retrieval** – Policies, preferences, and patterns are fetched  
4. **Tool Execution** – Calendar / Flight / Notification tools are called using MCP  
5. **Context Memory** – Conversation and dates are remembered  
6. **Response Generation** – Assistant returns structured answer  

---

## 🧠 RAG Knowledge Sources

- Company travel policies  
- Past scheduling patterns  
- User preferences  
- Behavioral rules  

This enables **smarter decisions**, not just generic LLM replies.

---

## 🖥️ User Interface

Built using **Streamlit**, offering:

- Chat mode  
- Meeting booking form  
- Flight search form  

---

## ⚙️ Setup Instructions

### 1. Clone Repository
```bash
git clone https://github.com/dhanyavasantha/Personal-assistant.git
```

### 2. Install Dependencies
```bash
pip install -r app/requirements.txt
```

### 3. Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=
AMADEUS_API_KEY=
AMADEUS_API_SECRET=
RESEND_API_KEY=
RESEND_FROM_EMAIL=
RESEND_TO_EMAIL=
```

### 4. Run UI
```bash
streamlit run ui.py
```

---

## 📌 Example Queries

- “Show my calendar for today”  
- “Book a meeting tomorrow at 10 AM”  
- “Book a meeting at 10 AM on Jan 23, 2026”  
- “Cancel meeting from 11 to 12”  
- “Search flights from NYC to IAD next Tuesday”  

---

## 🔮 Future Improvements

- Multi-user authentication  
- Flight booking  
- Hotel booking

---

## 👩‍💻 Author

**Dhanya Sri Vasantha**
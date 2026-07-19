# Alaska: AI Chat Assistant

Welcome to **Alaska**, a powerful, full-stack AI chatbot application built with a modern Retrieval-Augmented Generation (RAG) architecture. Designed to be your friendly and knowledgeable assistant, Alaska can process documents, analyze media, and hold contextual conversations effortlessly.

---

## 1. Project Overview

Alaska is designed from the ground up to provide a seamless chat experience powered by Google's latest **Gemini 3.5 Flash** model. It features a sleek, dark-themed UI built with React and a robust, high-performance backend powered by FastAPI. 

Unlike traditional chatbots, Alaska features a custom-built RAG pipeline. This means you can upload your own PDFs, Word documents, and text files, and Alaska will chunk, embed, and search through them using **ChromaDB** to answer your questions accurately based on your own data.

---

## 2. Features of Alaska

- **Conversational Memory:** Alaska remembers your chat history, neatly organized in a sidebar.
- **Document & Media Uploads:** Upload PDFs, DOCX, TXT, images, audio, and video directly into the chat.
- **Local RAG Pipeline:** Fully customized Python RAG system without relying on heavy frameworks like LangChain.
- **Search History Panel:** Quickly look up past queries and see exactly what document chunks the AI retrieved.
- **Fast & Responsive UI:** Built with Vite and React for lightning-fast loading and smooth micro-animations.
- **Session Management:** Isolated conversations with the ability to create, switch between, and permanently delete past chats.

---

## 3. Installation Steps

To run Alaska locally on your machine, follow these steps:

### Prerequisites
- **Python 3.11+** installed on your system.
- **Node.js 18+** installed on your system.
- A free **Google Gemini API Key** (get one at [Google AI Studio](https://aistudio.google.com/)).

### Clone the Repository
```bash
git clone https://github.com/AritraRoy889/Alaska-AI-Chat-Assistant-By-Aritra-Roy-.git
cd Alaska-AI-Chat-Assistant-By-Aritra-Roy-
```

---

## 4. Required Dependencies

Alaska is divided into two parts: Frontend and Backend.

**Backend Dependencies (`backend/requirements.txt`):**
- `fastapi` & `uvicorn` (Web server)
- `google-genai` (Official Google Gemini SDK)
- `chromadb` (Vector database for RAG)
- `sqlalchemy` (SQLite database ORM)
- `PyPDF2`, `pdfplumber`, `python-docx` (Document parsing)

**Frontend Dependencies (`frontend/package.json`):**
- `react` & `react-dom` (UI Library)
- `react-router-dom` (Routing)
- `vite` (Build tool & Dev server)

---

## 5. How to Run the Project

You will need to run the backend and frontend in two separate terminal windows.

### Step A: Start the Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate
   
   # On Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables:
   - Copy the `.env.example` file and rename it to `.env`.
   - Open `.env` and paste your Gemini API key:
     ```env
     GEMINI_API_KEY=your_actual_api_key_here
     GEMINI_CHAT_MODEL=gemini-3.5-flash
     ```
5. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

*(Note: Your local databases and `.env` files are protected by `.gitignore` and will never be pushed to GitHub.)*

### Step B: Start the Frontend
1. Open a **new terminal** and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the Node modules:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser and go to: **http://localhost:5173**

---

## 6. Sample Screenshots & Demo

Here is a quick look at Alaska in action! 

### Welcome to Alaska
The sleek, animated landing page that greets you when you first launch the app.
![Landing Page](assets/screenshot-1.png)

### Secure Authentication
A clean and modern login/signup interface to keep your chat sessions secure.
![Login Page](assets/screenshot-2.png)
![Create Account](assets/screenshot-3.png)

### The Chat Interface
The main dashboard where you can talk to Alaska, manage your conversation history, search through past RAG queries, and upload your files.
![Chat Interface](assets/screenshot-4.png)

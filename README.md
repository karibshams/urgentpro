Got it ✅
I’ll update the README so it clearly states that both the **OpenAI API key** and **model name** must be stored in `.env`.

Here’s the revised version:

---

````markdown
# Chatbot Application

This repository contains a chatbot application built with Python and Streamlit.  
It is structured with:
- `app.py` → **Main entry point** to run the chatbot.
- `chatbot_setup.py` → Chatbot initialization and configuration.
- `main.py` → Test file (not required for production).
- `.devcontainer` → Development container configuration (optional).
- `requirements.txt` → Python dependencies list.

---

## 📦 1. Clone the Repository
```bash
git clone <your-repo-url>
cd <your-repo-folder>
````

---

## 🐍 2. Create & Activate Virtual Environment

### **Windows (PowerShell)**

```bash
python -m venv venv
venv\Scripts\activate
```

### **Mac/Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 📥 3. Install Dependencies

Make sure your virtual environment is activated before running this:

```bash
pip install -r requirements.txt
```

---

## 🔑 4. Create `.env` File

Store your **OpenAI API Key** and **Model Name** inside a `.env` file in the project root:

Example `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1
```

> ⚠️ Never share your `.env` file publicly.

---

## ▶️ 5. Run the Application

The chatbot runs using **Streamlit**:

```bash
streamlit run app.py
```

---

## 🛠 6. Development Notes

* **Main File:** Use `app.py` to run the chatbot.
* **Chatbot Setup:** `chatbot_setup.py` handles the configuration logic.
* **Testing:** `main.py` is for local testing only; you can ignore it for production.
* **Environment Variables:** `.env` must contain both the API key and model name.

---

## 📊 7. Project Structure

```
.
├── .devcontainer/        # Dev container setup (optional)
├── .gitignore            # Git ignore rules
├── app.py                # Main Streamlit app
├── chatbot_setup.py      # Chatbot configuration
├── main.py               # Test file (optional)
├── requirements.txt      # Python dependencies
├── venv/                 # Virtual environment (not tracked by Git)
└── .env                  # Environment variables
```

---

## 💡 8. Visualization

Once you run:

```bash
streamlit run app.py
```

* The chatbot UI will open in your **default browser**.
* You can interact with it in real time.
* All backend logic comes from `chatbot_setup.py`.

---

## 📞 Support

For any issues or setup help, please contact the developer or open a GitHub issue.

```

---

If you want, I can also add a **diagram showing how `app.py` calls `chatbot_setup.py` and reads `.env`** so the client can see the flow visually. That would make the README even clearer.
```

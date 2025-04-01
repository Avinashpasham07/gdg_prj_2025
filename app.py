import requests
import time
import sqlite3
import base64
import io
import matplotlib.pyplot as plt
import yfinance as yf
from deep_translator import GoogleTranslator
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ✅ Replace with your Hugging Face API Key
HUGGINGFACE_API_KEY = "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"
HF_MODEL = "facebook/blenderbot-400M-distill"

# ✅ Initialize Database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, 
                    name TEXT, 
                    income REAL, 
                    expenses REAL, 
                    risk_level TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ✅ Function to Translate Text
def translate_text(text, target_language="te"):
    return GoogleTranslator(source='auto', target=target_language).translate(text)

# ✅ Home Route
@app.route('/')
def home():
    return render_template("index.html")

# ✅ Chatbot Page Route
@app.route('/chatbot')
def chatbot_page():
    return render_template("chat.html")

# ✅ Financial Analysis Route
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json  # Get JSON data from request

        # ✅ Safely Get Values with Defaults
        name = data.get('name', 'User')
        income = float(data.get('income', 0))
        expenses = float(data.get('expenses', 0))
        risk_level = data.get('risk_level', 'medium')
        lang = data.get('lang', 'en')

        savings = income - expenses
        overspending = expenses > income  # Check if overspending

        # ✅ Store Data in DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name, income, expenses, risk_level) VALUES (?, ?, ?, ?)", 
                  (name, income, expenses, risk_level))
        conn.commit()
        conn.close()

        # ✅ AI Financial Advice
        advice = f"Hello {name}, based on your income of ₹{income:,.2f}, expenses of ₹{expenses:,.2f}, and your risk preference ({risk_level} level), you have savings of ₹{savings:,.2f}. " \
                 f"{'Be cautious, as you are overspending!' if overspending else 'Great job managing your finances!'} " \
                 f"You should focus on {'safe investments like fixed deposits and bonds' if risk_level.lower() == 'low' else 'a balanced mix of mutual funds and stocks' if risk_level.lower() == 'medium' else 'high-growth opportunities like startups and cryptocurrencies'}."

        # ✅ Translate Advice if Needed
        translated_advice = translate_text(advice, lang) if lang != 'en' else advice

        return jsonify({
            "name": name,
            "income": income,
            "expenses": expenses,
            "risk_level": risk_level,
            "savings": savings,
            "overspending_alert": overspending,
            "advice": translated_advice
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error in case of failure

# ✅ Function to Fetch AI Response with Retry Mechanism
def fetch_ai_response(user_message):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"inputs": user_message, "parameters": {"max_length": 150}}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{HF_MODEL}", 
                json=payload, 
                headers=headers, 
                timeout=10
            )

            response_data = response.json()
            if response.status_code == 200:
                if isinstance(response_data, list) and len(response_data) > 0:
                    return response_data[0].get("generated_text", "Error: No response generated.")
                elif isinstance(response_data, dict) and "generated_text" in response_data:
                    return response_data["generated_text"]
                else:
                    return "Unexpected API response format."

            elif response.status_code == 503:
                print(f"Attempt {attempt + 1}: AI is busy, retrying in 5 seconds...")
                time.sleep(5)

            else:
                return f"Error {response.status_code}: {response.text}"

        except requests.exceptions.Timeout:
            print("Request timed out. Retrying...")
            time.sleep(5)

    return "AI is currently busy. Please try again later."

# ✅ Chatbot Route using Hugging Face API
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message")
    bot_reply = fetch_ai_response(user_message)
    return jsonify({"response": bot_reply})

if __name__ == '__main__':
    app.run(debug=True)

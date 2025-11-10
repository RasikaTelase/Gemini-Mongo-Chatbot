import os
import google.generativeai as genai
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import certifi

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ✅ MongoDB connection (secure SSL)
client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
db = client["gemini_db"]
collection = db["chat_history"]

# ✅ Gemini model function
def get_gemini_response(prompt):
    model = genai.GenerativeModel("gemini-1.5-flash")  # Make sure SDK is updated
    response = model.generate_content(prompt)
    return response.text

# ✅ Get user input
user_prompt = input("Enter your question for Gemini: ")

# ✅ Get AI response
ai_response = get_gemini_response(user_prompt)

# ✅ Prepare data for MongoDB
data = {
    "prompt": user_prompt,
    "response": ai_response,
    "timestamp": datetime.now()
}

# ✅ Save to MongoDB
try:
    collection.insert_one(data)
    print("\n✅ Data saved to MongoDB successfully!")
except Exception as e:
    print("❌ MongoDB insert error:", e)

# ✅ Display Gemini's response
print("\n🤖 Gemini Response:")
print(ai_response)

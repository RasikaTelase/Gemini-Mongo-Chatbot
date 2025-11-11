
import streamlit as st
from google import genai
from pymongo import MongoClient
from datetime import datetime

# -------------------- CONFIG --------------------
# NOTE: Replace with your actual keys/URIs
GEMINI_API_KEY = "AIzaSyDKRuaMZFzdWJhhjPqVLjRXOvKxlk1tkyI"
MONGO_URI = "mongodb+srv://riteshdeshmukh8459_db_user:2323@cluster0.mretvqm.mongodb.net/"

# Configure Gemini
# genai.configure(api_key=GEMINI_API_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

# Connect MongoDB
try:
    client = MongoClient(MONGO_URI)
    # Database for chat history
    chat_db = client["chatbot_db"]
    chats_collection = chat_db["chats"]

    # === 🚨 CRITICAL: UPDATE THESE DATABASE/COLLECTION NAMES ===
    # Based on your Compass image:
    data_db_name = "student_data" # <-- VERIFY your Database Name
    collection_name = "student" # <-- VERIFY your Collection Name
    
    # Connect to the database and collection containing the student records
    data_db = client[data_db_name] 
    student_collection = data_db[collection_name] 
    # ==========================================================

    mongo_status = True
except Exception as e:
    mongo_status = False
    st.error(f"MongoDB connection error: {e}")

# -------------------- RAG FUNCTION (Database Retrieval) --------------------

def get_mongo_context(user_query):
    """Searches the student collection for relevant data based on the user's query."""
    
    # Simple keyword extraction to find a student name (Alice, Bob, Charlie)
    query_lower = user_query.lower()
    name_search = None
    
    # You can expand this logic to check more names or use a more advanced search
    if "alice" in query_lower:
        name_search = "Alice"
    elif "bob" in query_lower:
        name_search = "Bob"
    elif "charlie" in query_lower:
        name_search = "Charlie"
    
    if name_search:
        try:
            # Find the document by name
            student_doc = student_collection.find_one({"name": name_search})
            
            if student_doc:
                # Remove MongoDB's ObjectId for cleaner context
                student_doc.pop('_id', None) 
                # Format the data into a string for Gemini
                context_string = f"Student Record: {student_doc}"
                return context_string
        except Exception as e:
            st.warning(f"Error accessing student data: {e}. Answering with general knowledge.")
            return None
            
    return None # Return None if no relevant student name is found

# -------------------- STREAMLIT UI --------------------
st.set_page_config(page_title="Gemini + MongoDB Chatbot", layout="centered")
st.title("💬 Gemini + MongoDB Chatbot")

if mongo_status:
    st.success(f"✅ Connected to MongoDB. RAG enabled for '{data_db_name}.{collection_name}'.")
else:
    st.error("❌ MongoDB not connected")

# -------------------- LOGIN / ROLE SELECTION --------------------
st.sidebar.header("User Login / Role")
username = st.sidebar.text_input("Enter Username")
role = st.sidebar.selectbox("Select Role", ["User", "Admin"])

if not username:
    st.warning("Please enter your username to start chatting.")
    st.stop()

st.sidebar.info(f"Logged in as: **{username} ({role})**")

# -------------------- CHAT INTERFACE (MODIFIED FOR RAG) --------------------
st.subheader("Ask something to Gemini 🤖 (Database Aware)")

user_input = st.text_input("Your question:")

if st.button("Ask Gemini"):
    if user_input:
        try:
            # --- RAG LOGIC START ---
            mongo_context = get_mongo_context(user_input)
            
            if mongo_context:
                st.info("🔍 Data found! Using RAG to answer from MongoDB context.")
                
                # System Instruction: Tells Gemini to use ONLY the provided data
                system_instruction = (
                    "You are an AI trained to answer questions about student data. "
                    "Answer the user's question ONLY based on the CONTEXT provided below. "
                    "If the specific answer is not in the context, state 'I cannot find that information in the student records'."
                )
                
                # Full Prompt: Combines the context and the user question
                full_prompt = f"CONTEXT: {mongo_context}\n\nQUESTION: {user_input}"
                
                # Initialize model with system instruction
                model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
                response = model.generate_content(full_prompt)
            
            else:
                # Fallback: Use general knowledge if no relevant student data is found
                st.info("🌍 No specific data found. Answering with Gemini's general knowledge.")
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(user_input)

            # --- RAG LOGIC END ---

            if response and response.text:
                answer = response.text
                st.markdown(f"**Gemini:** {answer}")

                # Save chat with metadata (to the 'chats' collection)
                chat_data = {
                    "username": username,
                    "role": role,
                    "question": user_input,
                    "answer": answer,
                    "timestamp": datetime.now()
                }
                chats_collection.insert_one(chat_data)
            else:
                st.warning("⚠️ Gemini did not return any answer.")
        except Exception as e:
            st.error(f"Gemini API Error: {e}")
    else:
        st.warning("Please enter a question first.")

# -------------------- ROLE-WISE CHAT HISTORY --------------------
st.markdown("---")
st.subheader("🕓 Chat History")

if role == "Admin":
    st.info("Viewing all users' chats (Admin access)")
    all_chats = chats_collection.find().sort("timestamp", -1)
else:
    st.info("Viewing only your chats")
    all_chats = chats_collection.find({"username": username}).sort("timestamp", -1)

for chat in all_chats:
    st.markdown(f"""
    **👤 {chat['username']}** ({chat['role']})  
    ❓ **Q:** {chat['question']}  
    💬 **A:** {chat['answer']}  
    🕒 {chat['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
    ---
    """)

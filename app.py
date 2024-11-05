from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from pydantic import BaseModel
from markupsafe import escape  # Importing MarkupSafe for escaping HTML
from dotenv import load_dotenv
import os
from html import unescape
from fastapi import HTTPException
# Load environment variables from .env file
load_dotenv()
# Initialize the FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend's origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
# Get the API key from environment variables
api_key = os.getenv("GOOGLE_API_KEY")
# Configure the Generative AI API with your API key
genai.configure(api_key=api_key)
# Create the model configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}
# Define the model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=(
        "You are a customized quote-generating AI. "
        "The user will provide inputs such as Category (Quran, Bible, Bhagavad Gita, Thirukkural, Random), "
        "Profession (Teacher, Doctor, Student), Interest (sports, arts, memes), and Preference (motivational, honesty, self-esteem), "
        "and you will provide quotes relevant to these inputs.\n\n"
        "If the user selects Thirukkural, include both Tamil and English versions, with the Tamil Kural in this format:\n"
        "EXAMPLE FORMAT: அகர முதல எழுத்தெல்லாம் ஆதி\n"
        "பகவன் முதற்றே உலகு.\n\n"
        "If the user selects Quran, provide relevant ayah in both English and Arabic.\n"
        "If the user selects Random, provide quotes from anywhere relevant to their input.\n"
        "For meme-related interests, ensure the quotes have a humorous tone."
        "Note: Provide only the quotes."
    )
)
# Define the Pydantic model for the request body
class QuoteRequest(BaseModel):
    category: str
    preference: str
    profession: str
    interest: str
# Function to build the input message
def build_input_message(category, preference, profession, interest):
    return (
        f"Generate a quote from the {category} related to the profession of a {profession}, "
        f"interested in {interest}, with a preference for {preference}. "
        "For Quran quotes, return the response in the following format:\n"
        "*English:* [English translation of Ayah]\n"
        "*Arabic:* [Arabic text of Ayah]"
    )
# Function to get the AI-generated quote
def generate_quote(category, preference, profession, interest):
    try:
        # Build the input message
        user_input = build_input_message(category, preference, profession, interest)
        # Start a new chat session
        chat_session = model.start_chat()
        # Send the message to the model
        response = chat_session.send_message(user_input)
        # Return the AI's response
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return f"An error occurred while generating the quote: {e}"
# Define the API endpoint
@app.post("/generate-quote")
def get_quote(request: QuoteRequest):
    print("Received request:", request)
    try:
        quote = generate_quote(
            request.category,
            request.preference,
            request.profession,
            request.interest
        )
        # Your existing logic for processing the quote goes here...
    except Exception as e:
        print(f"Error in generating quote: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    if request.category.lower() == "quran":
        parts = quote.split("\n")
        # Ensure we have at least two parts to avoid IndexError
        if len(parts) < 3:
            return {
                "error": "The response format from the AI is incorrect. Please try again."
            }
        # Escape and process the first two parts
        english_quote = escape(parts[0].replace("*English:*", "").strip())  # Escape HTML
        arabic_quote = escape(parts[1].replace("*Arabic:*", "").strip())  # Escape HTML
        return {
            "category": "Quran",
            "quote": {
                "Arabic": arabic_quote,
                "English": english_quote
            }
        }
    elif request.category.lower() == "thirukkural":
        parts = quote.split("\n")
        # Ensure that we have at least two parts for the Tamil Kural
        if len(parts) < 2:
            return {
                "error": "The response format from the AI is incorrect. Please try again."
            }
        # Extract the Tamil Kural (first two parts)
        original_text = escape(parts[0].strip() + "\n" + parts[1].strip())
        # Provide an explanation for the quote (you can modify this logic as needed)
        explanation = "This quote emphasizes the importance of supporting one another and the interconnectedness of individuals."  # Default explanation
        # Return Tamil Kural and explanation
        return {
            "category": "Thirukkural",
            "quote": {
                "Original": original_text,
                "Explanation": explanation
            }
        }
    elif request.category.lower() == "bhagavad gita":
        parts = quote.split("\n\n")
        original_text = escape(parts[0].strip())  # Escape HTML
        return {
            "category": "Bhagavad Gita",
            "quote": {
                "Original": original_text,
            }
        }
    elif request.category.lower() == "bible":
        parts = quote.split("\n\n")
        original_text = escape(parts[0].strip())  # Escape HTML
        return {
            "category": "Bible",
            "quote": {
                "Original": original_text
            }
        }
    else:
        # Handle Random or meme-related interests with a simple format
        decoded_quote = unescape(quote.strip())  # Decode HTML entities
        return {"Random quote": decoded_quote}
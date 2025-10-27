import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
log = logging.getLogger("ai_service")
class AIService:
    def __init__(self):
        api_key = os.getenv("GITHUB_TOKEN")
        if not api_key:
            log.warning("GITHUB_TOKEN for OpenAI not set - AI service will return mock responses")
            # log.warning("OPENAI_API_KEY not set - AI service will return mock responses")
            self.client = None
        else:
            log.info(f"GITHUB_TOKEN ASSIGNED")
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://models.github.ai/inference",     
            )

    def generate_response(self, user_text: str) -> str:
        """Generate AI response using ChatGPT"""
        log.info(f"Generating AI response for user text")

        # Ensure user_text is not empty
        if not user_text or not user_text.strip():
            return "I received an empty message. Please provide a question or request for me to help with."

        # If no OpenAI client, return mock response
        if not self.client:
            log.info("Returning mock response (no OpenAI API key)")
            return f"Mock AI Response: You asked about '{user_text.strip()}'. This is a test response since no OpenAI API key is configured."

        try:
            # Load system role text from file
            # Get the absolute path of the directory where this script is located
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, "ai_assistant_role.txt")
            with open(file_path, "r", encoding="utf-8") as f:
                system_role = f.read()

            # Create system role and user message
            #system_role = "You are a helpful assistant that provides clear, accurate, and useful responses to user questions and requests."
            user_message = f"Please help me with the following: {user_text.strip()}"

            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": user_message}
                ],
                # model="gpt-3.5-turbo",
                # max_tokens=500,
                # temperature=0.7
                model="openai/gpt-4o-mini",
                temperature=1,
                max_tokens=4096,
                top_p=1,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            log.info(f"AI response generated successfully")
            return result

        except Exception as e:
            log.error(f"Error calling OpenAI API: {e}")
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
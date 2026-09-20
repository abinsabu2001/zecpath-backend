import time

from decouple import config


class AIBridgeServiceError(Exception):
    """Raised when an AI or voice service operation fails."""


class AIBridgeService:
    """
    Central service for AI and Voice integrations.
    """

    def get_api_key(self):
        return config("OPENAI_API_KEY", default="")

    def text_to_speech(self, text):
        return {
            "status": "success",
            "message": f"Text converted to speech: {text}",
        }

    def speech_to_text(self, audio_file):
        return {
            "status": "success",
            "message": "Speech converted to text",
            "text": "Sample converted text",
        }

    def trigger_voice_call(self, phone_number):
        """
        Simulates a voice call with retry and error handling.
        """
        retries = 3

        for attempt in range(retries):
            try:
                api_key = self.get_api_key()

                if not api_key:
                    raise AIBridgeServiceError(
                        "OpenAI API key not found"
                    )

                return {
                    "status": "success",
                    "message": f"Voice call triggered to {phone_number}",
                    "attempt": attempt + 1,
                }

            except AIBridgeServiceError as e:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue

                return {
                    "status": "failed",
                    "message": str(e),
                }
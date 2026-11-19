import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class GroqJSONClient:

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY")

        self.model = os.getenv("GROQ_MODEL")

        self.client = None

        if self.api_key and self.model:

            self.client = Groq(
                api_key=self.api_key
            )

    @property
    def available(self):

        return self.client is not None

    def generate_json(
        self,
        system_prompt,
        user_data
    ):

        if not self.available:
            return None

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[

                {
                    "role": "system",
                    "content": system_prompt
                },

                {
                    "role": "user",
                    "content": json.dumps(user_data)
                }

            ],

            response_format={
                "type": "json_object"
            },

            temperature=0.2,

            max_completion_tokens=1500

        )

        content = response.choices[0].message.content

        return json.loads(content)
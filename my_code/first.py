import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')

openai = OpenAI()


messages = [{"role": "user", "content": "Write some relevant business idea"}]

# Then make the first call:

response = openai.chat.completions.create(
    model="gpt-4.1-mini",
    messages=messages
)

# Then read the business idea:

business_idea = response.choices[0].message.content

print(business_idea)

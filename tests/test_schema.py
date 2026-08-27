import os
from google import genai
from google.genai import types
from pydantic import BaseModel

class Dummy(BaseModel):
    a: int

client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
res = client.models.generate_content(
    model='models/gemini-3.6-flash',
    contents='give me an int',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=Dummy
    )
)
print(res.text)



import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

models = client.models.list()
for m in models.data:
    print(m.id)
from google import genai

client = genai.Client(
    api_key="YOUR API KEY"
)

try:
    response = client.models.generate_content(
        model="models/gemini-3-flash-preview",
        contents="Say Hello"
    )

    print("SUCCESS")
    print(response.text)

except Exception as e:
    print("ERROR")
    print(type(e))
    print(e)
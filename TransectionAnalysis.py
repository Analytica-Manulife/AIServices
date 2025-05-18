import os

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

def generate_weekly_spending_story(transaction_json: dict) -> str:
    """
    Analyzes a user's transaction JSON and generates a creative weekly story.

    Args:
        transaction_json (dict): A dictionary representing user transactions over the week.

    Returns:
        str: A creative story summarizing the user's week based on their spending.
    """
    endpoint = os.getenv("WEEKLY_STORY_OPENAI_ENDPOINT")
    deployment = os.getenv("WEEKLY_STORY_OPENAI_DEPLOYMENT")
    subscription_key = os.getenv("WEEKLY_STORY_OPENAI_KEY")

    # Initialize Azure OpenAI client with key-based authentication
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2025-01-01-preview",
    )

    # Prepare the chat prompt
    messages = [
        {
            "role": "system",
            "content": "You are a creative AI that turns transaction data into a fun, engaging weekly story of a user's life."
        },
        {
            "role": "user",
            "content": f"Here are my weekly transactions in JSON format:\n{transaction_json}\nCan you tell me a story about my week based on these?"
        }
    ]

    # Generate the completion
    completion = client.chat.completions.create(
        model=deployment,
        messages=messages,
        max_tokens=800,
        temperature=1,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )

    return completion.choices[0].message.content



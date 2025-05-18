from openai import AzureOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

def suggest_stock_to_buy(user_portfolio_json: dict, market_data_json: dict) -> str:
    """
    Suggests a new stock to buy based on the user's portfolio and current market data.

    Args:
        user_portfolio_json (dict): Dictionary representing the user's current stock holdings.
        market_data_json (dict): Dictionary representing current stock market data.

    Returns:
        str: A thoughtful recommendation of a stock to buy with reasons.
    """
    endpoint = os.getenv("STOCK_ADVISOR_OPENAI_ENDPOINT")
    deployment = os.getenv("STOCK_ADVISOR_OPENAI_DEPLOYMENT")
    subscription_key = os.getenv("STOCK_ADVISOR_OPENAI_KEY")
    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2025-01-01-preview",
    )

    # Prompt structure
    messages = [
        {
            "role": "system",
            "content": "You are a financial assistant AI that analyzes user portfolios and market trends to recommend stocks."
        },
        {
            "role": "user",
            "content": (
                f"Here is the user's current stock portfolio:\n{user_portfolio_json}\n\n"
                f"Here is the current market data:\n{market_data_json}\n\n"
                f"Based on this information, suggest one new stock the user should consider buying. "
                f"Explain your reasoning briefly in simple terms."
            )
        }
    ]

    # Get recommendation
    completion = client.chat.completions.create(
        model=deployment,
        messages=messages,
        max_tokens=500,
        temperature=0.8,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )

    return completion.choices[0].message.content
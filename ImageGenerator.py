import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def generate_magazine_images_from_story(story: str) -> list:
    """
    Splits a story into 4 sections and generates a vivid DALL·E 3 image for each section
    using Azure OpenAI. Endpoint and keys are set inside the function.

    Args:
        story (str): The full story text.

    Returns:
        List[str]: List of image URLs corresponding to each section.
    """
    # Configuration (hardcoded or from env vars)

    endpoint = os.getenv("MAGAZINE_IMAGE_OPENAI_ENDPOINT")
    api_version = os.getenv("MAGAZINE_IMAGE_OPENAI_API_VERSION", "2024-04-01-preview")
    deployment = os.getenv("MAGAZINE_IMAGE_OPENAI_DEPLOYMENT")
    api_key = os.getenv("MAGAZINE_IMAGE_OPENAI_KEY")



    # Initialize Azure OpenAI client
    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )

    # Create visual prompt with Ghibli + magazine theme
    visual_prompt = (
        f"Studio Ghibli-style magazine cover illustration inspired by the following story: {story} "
        "— include dreamy backgrounds, cinematic framing, expressive characters, and whimsical details."
    )

    # Generate the image
    result = client.images.generate(
        model=deployment,
        prompt=visual_prompt,
        n=1,
        style="vivid",
        quality="standard",
    )

    # Extract and return the image URL
    image_url = json.loads(result.model_dump_json())['data'][0]['url']
    return image_url

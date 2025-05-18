import csv
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple
import requests
import time

from dotenv import load_dotenv

load_dotenv()


class LLMNewsParser:
    def __init__(self, api_key=None, model_provider='openai'):
        """
        Initialize the LLM News Parser

        Args:
            api_key: API key for the LLM service
            model_provider: 'openai', 'anthropic', 'ollama', or 'huggingface'
        """
        self.api_key = api_key
        self.model_provider = model_provider.lower()
        self.output_dir = 'company_news'
        os.makedirs(self.output_dir, exist_ok=True)

        # Configure API endpoints and models based on provider
        self.setup_llm_config()

    def setup_llm_config(self):
        """Setup configuration for different LLM providers"""
        if self.model_provider == 'openai':
            self.api_url = "https://api.openai.com/v1/chat/completions"
            self.model_name = "gpt-3.5-turbo"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        elif self.model_provider == 'anthropic':
            self.api_url = "https://api.anthropic.com/v1/messages"
            self.model_name = "claude-3-haiku-20240307"
            self.headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        elif self.model_provider == 'ollama':
            self.api_url = "http://localhost:11434/api/generate"
            self.model_name = "llama2"  # or any model you have installed
            self.headers = {"Content-Type": "application/json"}
        elif self.model_provider == 'huggingface':
            self.api_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

    def call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call the LLM API with retry logic"""
        for attempt in range(max_retries):
            try:
                if self.model_provider == 'openai':
                    payload = {
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 1000
                    }
                elif self.model_provider == 'anthropic':
                    payload = {
                        "model": self.model_name,
                        "max_tokens": 1000,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                elif self.model_provider == 'ollama':
                    payload = {
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    }
                else:  # huggingface
                    payload = {
                        "inputs": prompt,
                        "parameters": {"max_new_tokens": 1000, "temperature": 0.1}
                    }

                response = requests.post(self.api_url, headers=self.headers, json=payload)
                response.raise_for_status()

                # Parse response based on provider
                if self.model_provider == 'openai':
                    return response.json()['choices'][0]['message']['content']
                elif self.model_provider == 'anthropic':
                    return response.json()['content'][0]['text']
                elif self.model_provider == 'ollama':
                    return response.json()['response']
                else:  # huggingface
                    return response.json()[0]['generated_text']

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None

        return None

    def analyze_news_with_llm(self, headline: str, description: str) -> Dict:
        """Use LLM to extract companies, tickers, and sentiment from news"""

        prompt = f"""
Analyze this financial news and extract information in JSON format:

Headline: {headline}
Description: {description}

Please provide a JSON response with:
1. "companies": List of company names mentioned (full company names, not abbreviations)
2. "tickers": List of stock ticker symbols for the companies (if publicly traded, use actual tickers like AAPL, GOOGL, etc.)
3. "sentiment": Overall sentiment ("positive", "negative", or "neutral")
4. "sentiment_score": Numerical score from -1 (very negative) to +1 (very positive)
5. "key_themes": List of main themes/topics in the news
6. "confidence": Confidence level in the analysis (0-1)

Guidelines:
- Use official company names (e.g., "Apple Inc." not "Apple")
- Use correct stock tickers (e.g., "META" for Facebook/Meta, "GOOGL" for Google/Alphabet)
- If company is private or not publicly traded, use "PRIVATE" as ticker
- Be accurate with sentiment analysis considering business impact
- If unsure about a ticker, use "UNKNOWN"

Return only valid JSON, no additional text.
"""

        response = self.call_llm(prompt)

        if not response:
            return {
                "companies": [],
                "tickers": [],
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "key_themes": [],
                "confidence": 0.0
            }

        try:
            # Clean the response to extract JSON
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:-3]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:-3]

            analysis = json.loads(cleaned_response)

            # Validate and clean the analysis
            analysis["companies"] = analysis.get("companies", [])
            analysis["tickers"] = analysis.get("tickers", [])
            analysis["sentiment"] = analysis.get("sentiment", "neutral")
            analysis["sentiment_score"] = float(analysis.get("sentiment_score", 0.0))
            analysis["key_themes"] = analysis.get("key_themes", [])
            analysis["confidence"] = float(analysis.get("confidence", 0.5))

            return analysis

        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response}")
            return {
                "companies": [],
                "tickers": [],
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "key_themes": [],
                "confidence": 0.0
            }

    def load_existing_data(self, ticker: str) -> List[Dict]:
        """Load existing JSON data for a ticker"""
        filename = os.path.join(self.output_dir, f"{ticker}.json")
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_ticker_data(self, ticker: str, data: List[Dict]):
        """Save data to ticker's JSON file"""
        filename = os.path.join(self.output_dir, f"{ticker}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def parse_csv_file(self, csv_file_path: str):
        """Parse the CSV file and create JSON files for each company ticker"""
        processed_count = 0
        successful_analyses = 0

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            # Auto-detect CSV format
            sample = file.read(1024)
            file.seek(0)

            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(file, delimiter=delimiter)

            for row in reader:
                headline = row.get('Headlines', '') or row.get('Headline', '')
                time_str = row.get('Time', '') or row.get('Date', '')
                description = row.get('Description', '') or row.get('Content', '')

                if not headline and not description:
                    continue

                print(f"Processing: {headline[:50]}...")

                # Analyze with LLM
                analysis = self.analyze_news_with_llm(headline, description)

                if analysis["confidence"] > 0.3:  # Only process if confidence is reasonable
                    successful_analyses += 1

                    # Process each ticker found
                    for i, ticker in enumerate(analysis["tickers"]):
                        if ticker in ["UNKNOWN", ""]:
                            continue

                        company_name = analysis["companies"][i] if i < len(analysis["companies"]) else "Unknown"

                        # Create news entry
                        news_entry = {
                            'timestamp': time_str,
                            'headline': headline,
                            'description': description,
                            'company_name': company_name,
                            'ticker': ticker,
                            'sentiment': analysis["sentiment"],
                            'sentiment_score': analysis["sentiment_score"],
                            'key_themes': analysis["key_themes"],
                            'confidence': analysis["confidence"],
                            'full_text': f"{headline} {description}".strip(),
                            'processed_date': datetime.now().isoformat()
                        }

                        # Load existing data and check for duplicates
                        existing_data = self.load_existing_data(ticker)

                        duplicate = False
                        for existing_entry in existing_data:
                            if (existing_entry.get('headline') == headline and
                                    existing_entry.get('timestamp') == time_str):
                                duplicate = True
                                break

                        if not duplicate:
                            existing_data.append(news_entry)
                            self.save_ticker_data(ticker, existing_data)
                            print(f"  → Added to {ticker} ({company_name}): {analysis['sentiment']} sentiment")

                processed_count += 1
                if processed_count % 5 == 0:
                    print(f"Progress: {processed_count} rows processed, {successful_analyses} successful analyses")

                # Add small delay to respect API rate limits
                time.sleep(0.5)

        print(f"\nCompleted processing {processed_count} rows")
        print(f"Successful analyses: {successful_analyses}")
        self.print_summary()

    def print_summary(self):
        """Print summary of created files"""
        print(f"\nSummary of created files in '{self.output_dir}' directory:")
        total_items = 0

        for filename in sorted(os.listdir(self.output_dir)):
            if filename.endswith('.json'):
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    ticker = filename[:-5]
                    count = len(data)
                    total_items += count

                    # Calculate sentiment distribution
                    sentiments = [item['sentiment'] for item in data]
                    pos = sentiments.count('positive')
                    neg = sentiments.count('negative')
                    neu = sentiments.count('neutral')

                    print(f"{ticker}: {count} items (P:{pos}, N:{neg}, Neu:{neu})")

        print(f"\nTotal news items processed: {total_items}")


# Usage examples for different LLM providers

def main():
    """Main function with examples for different LLM providers"""

    # Option 1: OpenAI
    api_key = os.getenv("NEWS_ANALYZER_KEY")
    parser = LLMNewsParser(api_key=api_key, model_provider="openai")

    # Option 2: Anthropic Claude
    # parser = LLMNewsParser(api_key="your-anthropic-api-key", model_provider="anthropic")

    # Option 3: Local Ollama (free, runs locally)
    # parser = LLMNewsParser(model_provider="ollama")

    # Option 4: Hugging Face
    # parser = LLMNewsParser(api_key="your-hf-token", model_provider="huggingface")

    # Parse your CSV file
    csv_file_path = "news.csv"  # Replace with your CSV file path

    try:
        parser.parse_csv_file(csv_file_path)
        print("\nProcessing completed successfully!")
        print(f"JSON files created in the '{parser.output_dir}' directory")
    except FileNotFoundError:
        print(f"Error: Could not find the CSV file '{csv_file_path}'")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


# Utility functions for analysis
def analyze_ticker_trends(ticker: str, output_dir: str = 'company_news'):
    """Advanced analysis of ticker sentiment trends"""
    filename = os.path.join(output_dir, f"{ticker}.json")
    if not os.path.exists(filename):
        print(f"No data found for ticker {ticker}")
        return

    with open(filename, 'r') as f:
        data = json.load(f)

    if not data:
        return

    # Sort by date and analyze trends
    sentiments = [item['sentiment_score'] for item in data]
    themes = []
    for item in data:
        themes.extend(item.get('key_themes', []))

    # Count theme frequency
    theme_counts = {}
    for theme in themes:
        theme_counts[theme] = theme_counts.get(theme, 0) + 1

    print(f"\nAdvanced Analysis for {ticker}:")
    print(f"Total articles: {len(data)}")
    print(f"Average sentiment score: {sum(sentiments) / len(sentiments):.3f}")
    print(f"Sentiment range: {min(sentiments):.3f} to {max(sentiments):.3f}")
    print("\nTop themes:")
    for theme, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {theme}: {count} mentions")


if __name__ == "__main__":
    main()
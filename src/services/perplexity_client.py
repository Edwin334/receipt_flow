import requests
import json
import re
import traceback
from src.config import PERPLEXITY_API_KEY

# --- Perplexity API Call (Refactored) ---
def get_online_grocery_price_perplexity(item_name: str) -> dict:
    """
    Uses Perplexity API to find the price and URL of an item at major online grocery retailers.
    Returns a dictionary with status, price, details, and URL.
    """
    if not PERPLEXITY_API_KEY:
        return {'status': 'error', 'details': "Perplexity API Key not configured.", 'url': None}

    cleaned_item_name = item_name.replace('^', '').strip()
    print(f"Checking online grocery price for '{cleaned_item_name}' via Perplexity...")
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {PERPLEXITY_API_KEY}"
    }
    payload = {
        "model": "sonar-pro",
        "messages": [
             {
                "role": "system",
                "content": ("You are an AI assistant that finds product prices and links at major online retailers. "
                            "Given an item name, find the most likely matching product currently available for online purchase from retailers like Amazon, Walmart, Target, Chewy, etc. "
                            "Respond in JSON format with price, retailer, and a direct link to the product. "
                            "Your response should be structured as: "
                            "```json\n{\"price\": \"$XX.XX\", \"retailer\": \"Store Name\", \"url\": \"https://direct-product-link.com\"}\n```\n"
                            "If multiple prices or variations exist, respond with: "
                            "```json\n{\"price\": \"Price Varies\", \"retailer\": \"Multiple\", \"url\": \"https://best-match-link.com\"}\n```\n"
                            "If the exact item is not found after checking common retailers, respond with: "
                            "```json\n{\"price\": \"Not Found\", \"retailer\": \"N/A\", \"url\": null}\n```\n"
                            "Always provide a valid JSON response.")
            },
            {
                "role": "user",
                "content": f"Find the online price and direct link for: {cleaned_item_name}"
            }
        ],
        "temperature": 0.1,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        result = response.json()

        if result.get('choices') and result['choices'][0].get('message') and result['choices'][0]['message'].get('content'):
            content = result['choices'][0]['message']['content'].strip()
            print(f"Perplexity Result for '{cleaned_item_name}': {content}")

            if not content:
                return {'status': 'error', 'details': "Perplexity returned empty response.", 'url': None}

            # Extract JSON from response (could be wrapped in ```json blocks)
            try:
                # Try to find JSON block
                json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
                if json_match:
                    # Extract JSON from code block
                    json_str = json_match.group(1)
                else:
                    # Try to extract bare JSON
                    json_match = re.search(r'({.*})', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # No JSON found, use the whole content
                        json_str = content

                # Parse the JSON data
                data = json.loads(json_str)
                
                # Extract price, retailer, and URL
                price_str = data.get('price', 'N/A')
                retailer = data.get('retailer', 'Unknown')
                product_url = data.get('url')
                
                # Format details string
                if price_str == "Not Found":
                    details = "Not Found via Online Retailers"
                    return {'status': 'not_found', 'details': details, 'url': None}
                elif price_str == "Price Varies":
                    details = "Price Varies"
                    return {'status': 'varies', 'details': details, 'url': product_url}
                else:
                    # Normal case with price and retailer
                    details = f"{price_str} at {retailer}"
                    
                    # Try to parse price
                    price_match = re.search(r'\$?(\d+\.\d{2})', price_str)
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                            return {'status': 'found', 'price': price, 'details': details, 'url': product_url}
                        except ValueError:
                            pass
                    
                    # If we couldn't parse the price, still return the details
                    return {'status': 'found', 'price': None, 'details': details, 'url': product_url}
                
            except json.JSONDecodeError as json_err:
                print(f"🔴 ERROR parsing JSON from Perplexity response: {json_err}")
                print(f"Raw content: {content}")
                # Try to extract price using regex as fallback
                price_match = re.search(r'\$(\d+\.\d{2})\s+at\s+(\w+)', content)
                if price_match:
                    price = float(price_match.group(1))
                    retailer = price_match.group(2)
                    # Look for URLs in the response
                    url_match = re.search(r'https?://[^\s"\']+', content)
                    product_url = url_match.group(0) if url_match else None
                    details = f"${price} at {retailer}"
                    return {'status': 'found', 'price': price, 'details': details, 'url': product_url}
                elif "Not Found" in content:
                    return {'status': 'not_found', 'details': "Not Found via Online Retailers", 'url': None}
                elif "Price Varies" in content:
                    return {'status': 'varies', 'details': "Price Varies", 'url': None}
                else:
                    return {'status': 'error', 'details': f"Could not parse price from: {content}", 'url': None}
        else:
             print(f"Error: Unexpected Perplexity API response structure: {result}")
             return {'status': 'error', 'details': "Could not parse Perplexity response.", 'url': None}

    except requests.exceptions.RequestException as req_err:
        print(f"🔴 ERROR calling Perplexity API: {req_err}")
        return {'status': 'error', 'details': f"Error connecting to Perplexity API: {req_err}", 'url': None}
    except Exception as e:
        print(f"🔴 UNEXPECTED ERROR during Perplexity call: {e}")
        traceback.print_exc()
        return {'status': 'error', 'details': f"Unexpected error checking price: {e}", 'url': None} 
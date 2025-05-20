import PIL.Image
import json
import datetime
import random
import google.generativeai as genai
from src.config import GOOGLE_API_KEY, GEMINI_CLIENT_INITIALIZED

# --- Mock Gemini API Call ---
def mock_gemini_vision_processor(image: PIL.Image.Image):
    """
    Simulates a call to Gemini Vision API.
    Returns data with days until expiry instead of absolute dates.
    """
    print("Simulating Gemini Vision call...")
    # Simulate some processing time
    import time
    time.sleep(1.5)

    # Mocked data with days_until_expiry instead of predicted_expiry
    # More realistic shelf life estimates for common grocery items
    mock_items = [
        {"item": "Organic Milk", "days_until_expiry": random.randint(7, 14), "price_paid": f"${random.uniform(3.50, 5.99):.2f}"},
        {"item": "Artisan Bread", "days_until_expiry": random.randint(2, 5), "price_paid": f"${random.uniform(3.99, 6.99):.2f}"},
        {"item": "Avocado", "days_until_expiry": random.randint(2, 4), "price_paid": f"${random.uniform(1.25, 2.50):.2f}"},
        {"item": "Free-Range Eggs", "days_until_expiry": random.randint(14, 28), "price_paid": f"${random.uniform(3.99, 6.99):.2f}"},
        {"item": "Fresh Spinach", "days_until_expiry": random.randint(3, 7), "price_paid": f"${random.uniform(2.50, 4.99):.2f}"},
    ]
    
    # Convert days_until_expiry to actual dates
    today = datetime.date.today()
    for item in mock_items:
        days = item.pop("days_until_expiry")  # Remove days_until_expiry
        # Calculate actual expiry date based on today + days
        expiry_date = today + datetime.timedelta(days=days)
        item["predicted_expiry"] = expiry_date.isoformat()  # Keep predicted_expiry for consistency

    mock_total = f"${random.uniform(20, 75):.2f}"
    print(f"Mocked response: {len(mock_items)} items, Total: {mock_total}")
    return mock_items, mock_total

# --- Actual Gemini API Call ---
def call_gemini_vision_api(image: PIL.Image.Image):
    """
    Calls the Gemini Vision API to process the receipt.
    Now asks for days_until_expiry instead of absolute dates.
    """
    if not GOOGLE_API_KEY or not GEMINI_CLIENT_INITIALIZED:
        print("Error: Cannot call Gemini API without API key or if initialization failed.")
        raise ValueError("Google API Key not configured or client initialization failed.")

    print(f"Attempting Gemini API call with model gemini-2.0-flash...")
    # Model should be initialized if genai.configure was successful
    model = genai.GenerativeModel('gemini-2.0-flash')


    # Construct the prompt for the model - ask for days until expiry
    prompt = [
        "Analyze the following receipt image.",
        image,
        """Extract the purchased items, estimate how many days until each item would typically expire (based on common food storage knowledge), and extract the price paid for each item. Also determine the final total amount.

        For perishable foods, be realistic about shelf life. For example:
        - Fresh fruits like berries: 3-7 days
        - Fresh vegetables like spinach: 5-7 days
        - Bread: 3-5 days
        - Milk: 7-14 days
        - Eggs: 21-28 days
        - Cheese: 14-21 days
        - Fresh meat/fish: 1-3 days
        
        Respond ONLY with a valid JSON object containing two keys: 'items' and 'total'.
        The 'items' key should have a list of objects, where each object has:
         - 'item' key (string)
         - 'days_until_expiry' key (integer number of days) 
         - 'price_paid' key (string, e.g., "$3.50" or "3.50")
        
        The 'total' key should have the final total amount as a string (e.g., "$77.77").
        
        Example JSON format: 
        {"items": [{"item": "Milk", "days_until_expiry": 10, "price_paid": "$3.99"}, {"item": "Bread", "days_until_expiry": 5, "price_paid": "$2.50"}], "total": "$25.50"}"""
    ]

    try:
        # Generate content
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        print(f"Raw Gemini Response Text:\n{cleaned_text}")
        data = json.loads(cleaned_text)

        # Validate and extract data
        items = data.get('items', [])
        total = data.get('total', 'N/A')

        # --- Enhanced Validation & Conversion --- 
        validated_items = []
        today = datetime.date.today()  # Get current date

        if not isinstance(items, list):
            print("Warning: Gemini response 'items' is not a list.")
        else:
            for i, item in enumerate(items):
                if isinstance(item, dict) and 'item' in item and 'days_until_expiry' in item and 'price_paid' in item:
                    # Make a new copy of the item
                    validated_item = item.copy()
                    
                    # Calculate and add predicted expiry date based on days_until_expiry
                    try:
                        days = int(item['days_until_expiry'])
                        expiry_date = today + datetime.timedelta(days=days)
                        validated_item['predicted_expiry'] = expiry_date.isoformat()
                    except (ValueError, TypeError):
                        # If days_until_expiry is not a valid integer, use a default
                        print(f"Warning: Invalid days_until_expiry value for item {item['item']}: {item['days_until_expiry']}")
                        validated_item['predicted_expiry'] = (today + datetime.timedelta(days=7)).isoformat()  # Default 7 days
                    
                    validated_items.append(validated_item)
                else:
                    print(f"Warning: Invalid item structure at index {i}: {item}")

        print(f"Successfully parsed Gemini response: {len(validated_items)} validated items, Total: {total}")
        return validated_items, total

    except json.JSONDecodeError as json_err:
        print(f"🔴 ERROR decoding Gemini JSON response: {json_err}")
        print(f"   Response text was: {cleaned_text}")
        return [], f"Error: Invalid JSON response from AI ({json_err})"
    except Exception as e:
        print(f"🔴 ERROR calling Gemini API: {e}")
        return [], f"Error: AI API call failed ({e})" 
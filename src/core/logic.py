import pandas as pd
import datetime
import tempfile
import PIL.Image
import gradio as gr
import random # For mock data price if needed
import re # For price parsing in logic
import traceback

from src.config import GOOGLE_API_KEY
from src.services.gemini_client import call_gemini_vision_api, mock_gemini_vision_processor
from src.services.perplexity_client import get_online_grocery_price_perplexity
from src.core.utils import parse_price, format_comparison_summary

# --- Core Application Logic ---
def process_receipt(receipt_image: PIL.Image.Image, current_inventory_state: list):
    """
    Processes the uploaded receipt image and adds to running inventory.
    Now tracks both individual receipt totals and cumulative totals.
    """
    if receipt_image is None:
        return pd.DataFrame(columns=["Item", "Price Paid", "Predicted Expiry Date"]), "⚠️ Upload receipt first", None, current_inventory_state, ""

    comparison_summary = "" # Initialize summary string
    if current_inventory_state is None: current_inventory_state = []

    # Get timestamp for this receipt batch - to identify items from this receipt
    receipt_timestamp = datetime.datetime.now().isoformat()
    
    try:
        # --- Call Gemini API ---
        if GOOGLE_API_KEY: # Check if key is loaded, not if client initialized
            print("Using real Gemini API call.")
            new_items_data, latest_total_amount = call_gemini_vision_api(receipt_image)
        else:
            print("API Key not found. Using mock Gemini call as fallback.")
            new_items_data, latest_total_amount = mock_gemini_vision_processor(receipt_image)
            # Ensure mock data has price_paid, as it's crucial for later logic
            if not all('price_paid' in item for item in new_items_data):
                for item in new_items_data:
                    item['price_paid'] = f"${random.uniform(1, 15):.2f}"

        # --- Handle Gemini Errors --- 
        if not new_items_data and isinstance(latest_total_amount, str) and "Error:" in latest_total_amount:
            # If Gemini returned an error message, propagate it
            return pd.DataFrame(current_inventory_state or [], columns=["Item", "Price Paid", "Predicted Expiry Date"]), latest_total_amount, None, current_inventory_state, ""
        elif not new_items_data:
            error_message = "No items found in receipt."
            return pd.DataFrame(current_inventory_state or [], columns=["Item", "Price Paid", "Predicted Expiry Date"]), error_message, None, current_inventory_state, ""

        # --- Track current receipt vs previous receipt items ---
        # Tag each new item with a timestamp to identify this batch
        for item in new_items_data:
            item['receipt_timestamp'] = receipt_timestamp

        # --- Perform Batch Perplexity Price Check & Calculate Totals --- 
        current_receipt_total = 0.0
        current_online_total = 0.0
        current_found_count = 0
        current_assumed_count = 0
        
        all_receipts_total = 0.0
        all_online_total = 0.0
        all_found_count = 0
        all_assumed_count = 0
        
        current_receipt_results = []
        all_receipts_results = []
        
        if new_items_data:
            print(f"Starting batch Perplexity check for {len(new_items_data)} items in current receipt...")
            
            for item_dict in new_items_data:
                item_name = item_dict.get('item', 'Unknown Item')
                price_paid_str = item_dict.get('price_paid', 'N/A')
                
                price_paid_float = parse_price(price_paid_str)
                if price_paid_float is not None:
                    current_receipt_total += price_paid_float
                
                online_info = get_online_grocery_price_perplexity(item_name)
                product_url = online_info.get('url')
                online_details = online_info.get('details', "Error fetching price")

                if online_info['status'] == 'found' and online_info.get('price') is not None:
                    current_online_total += online_info['price']
                    current_found_count += 1
                    # Store actual online price for later cumulative calculation
                    item_dict['online_price'] = online_info['price'] 
                    item_dict['is_assumed_price'] = False
                elif price_paid_float is not None: # Assumed or not found - use receipt price for online if available
                    current_online_total += price_paid_float
                    current_assumed_count += 1
                    online_details = f"Assumed same as receipt (${price_paid_float:.2f})"
                    item_dict['online_price'] = price_paid_float
                    item_dict['is_assumed_price'] = True
                else: # Price paid is also not available, can't assume
                    item_dict['online_price'] = None
                    item_dict['is_assumed_price'] = False
                    # online_details would be from get_online_grocery_price_perplexity e.g. "Not Found" or error

                item_dict['online_details'] = online_details
                item_dict['url'] = product_url
                
                current_receipt_results.append({
                    'item': item_name,
                    'price_paid': price_paid_str,
                    'online_details': online_details,
                    'url': product_url,
                    'receipt_timestamp': receipt_timestamp
                })
            
            # --- Combine Inventories & Calculate Cumulative Totals ---
            # Start with current receipt values for cumulative totals
            all_receipts_total = current_receipt_total
            all_online_total = current_online_total
            all_found_count = current_found_count
            all_assumed_count = current_assumed_count
            all_receipts_results = list(current_receipt_results) 

            # Add previous receipts' data (if any)
            if current_inventory_state:
                print("Calculating cumulative totals including previous receipts...")
                existing_items_from_previous_receipts = [item for item in current_inventory_state 
                                                         if item.get('receipt_timestamp', '') != receipt_timestamp]
                
                for item in existing_items_from_previous_receipts:
                    price_paid_str = item.get('price_paid', 'N/A')
                    price_paid_float = parse_price(price_paid_str)
                    if price_paid_float is not None:
                        all_receipts_total += price_paid_float
                    
                    # Use stored online price information if available
                    if 'online_price' in item and item['online_price'] is not None:
                        all_online_total += item['online_price']
                        if item.get('is_assumed_price', False):
                            all_assumed_count +=1
                        else:
                            all_found_count += 1 
                    elif price_paid_float is not None: # Fallback if online_price wasn't stored but paid is
                        all_online_total += price_paid_float # Assume same as receipt price
                        all_assumed_count += 1

                    all_receipts_results.append({
                        'item': item.get('item', 'Unknown'),
                        'price_paid': price_paid_str,
                        'online_details': item.get('online_details', 'N/A'),
                        'url': item.get('url'),
                        'receipt_timestamp': item.get('receipt_timestamp', '')
                    })
            
            comparison_summary = format_comparison_summary(
                current_receipt_results, latest_total_amount, 
                current_receipt_total, current_online_total, 
                current_found_count, current_assumed_count,
                all_receipts_results, all_receipts_total, all_online_total, 
                all_found_count, all_assumed_count
            )

        # Add new items (now with online price info) to the inventory state
        current_inventory_state.extend(new_items_data)

        # --- Prepare DataFrame Output --- 
        COLUMNS_ORDER = ["Item", "Price Paid", "Predicted Expiry Date"]
        if not current_inventory_state:
            full_df = pd.DataFrame(columns=COLUMNS_ORDER)
        else:
            # Ensure all items in current_inventory_state are dicts
            # This can happen if an error object was accidentally added
            valid_inventory_items = [item for item in current_inventory_state if isinstance(item, dict)]
            full_df = pd.DataFrame(valid_inventory_items) 
            
            # Basic schema enforcement
            if 'item' not in full_df.columns: full_df['item'] = "Unknown Item"
            if 'price_paid' not in full_df.columns: full_df['price_paid'] = "N/A"
            if 'predicted_expiry' not in full_df.columns: full_df['predicted_expiry'] = "N/A"
            
            full_df.rename(columns={"item": "Item", "price_paid": "Price Paid", "predicted_expiry": "Predicted Expiry Date"}, inplace=True)
            # Ensure only desired columns are present and in order
            full_df = full_df[COLUMNS_ORDER]

        # --- Create CSV --- 
        temp_file_path = None
        if not full_df.empty:
            try:
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', encoding='utf-8') as temp_f:
                    full_df.to_csv(temp_f.name, index=False)
                    temp_file_path = temp_f.name
            except Exception as csv_e:
                print(f"Error creating temporary CSV: {csv_e}")

        file_output = gr.File(value=temp_file_path, label="CSV") if temp_file_path else None
        return full_df, latest_total_amount, file_output, current_inventory_state, comparison_summary

    except Exception as e:
        error_message = f"❌ An unexpected error occurred in processing: {e}"
        print(f"Error processing receipt: {e}")
        traceback.print_exc()
        # Ensure current_inventory_state is a list of dicts before creating DataFrame
        valid_inventory_items = [item for item in (current_inventory_state or []) if isinstance(item, dict)]
        df = pd.DataFrame(valid_inventory_items, columns=["Item", "Price Paid", "Predicted Expiry Date"])
        if df.empty and not valid_inventory_items: # If state was empty or malformed
             df = pd.DataFrame(columns=["Item", "Price Paid", "Predicted Expiry Date"]) 
        return df, error_message, None, current_inventory_state, comparison_summary # Return summary even on error

# --- Function to Clear State ---
def clear_inventory():
    """Resets the inventory state and related outputs."""
    print("Clearing inventory...")
    empty_df = pd.DataFrame(columns=["Item", "Price Paid", "Predicted Expiry Date"])
    return [], empty_df, None, "Cleared", ""

# --- Function to Prepare for Next Receipt ---
def prepare_for_next_receipt(inventory_state):
    """Clears the receipt input and comparison areas but keeps the inventory data."""
    print("Preparing for next receipt...")
    
    if not inventory_state: # inventory_state should be a list
        inventory_df = pd.DataFrame(columns=["Item", "Price Paid", "Predicted Expiry Date"])
    else:
        # Ensure all items in inventory_state are dicts for DataFrame creation
        valid_inventory_items = [item for item in inventory_state if isinstance(item, dict)]
        inventory_df = pd.DataFrame(valid_inventory_items) 
        if 'item' in inventory_df.columns: # Check if rename is needed
            inventory_df.rename(columns={"item": "Item", "price_paid": "Price Paid", "predicted_expiry": "Predicted Expiry Date"}, inplace=True)
        # Ensure correct columns if df is not empty, otherwise create empty with correct columns
        expected_cols = ["Item", "Price Paid", "Predicted Expiry Date"]
        if not inventory_df.empty:
            for col in expected_cols:
                if col not in inventory_df.columns:
                    inventory_df[col] = "N/A"
            inventory_df = inventory_df[expected_cols]
        else:
            inventory_df = pd.DataFrame(columns=expected_cols)
    
    # Return None for image, keep state, current df, clear total, keep download, clear comparison
    return None, inventory_state, inventory_df, "", None, "" 
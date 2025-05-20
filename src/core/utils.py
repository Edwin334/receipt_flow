import re

# --- Utility to Parse Price String --- 
def parse_price(price_str: str) -> float | None:
    """Attempts to extract a float price from a string like '$3.99' or '4.50'."""
    if not isinstance(price_str, str):
        return None
    try:
        # Remove currency symbols and commas
        cleaned_price = price_str.replace('$', '').replace(',', '').strip()
        return float(cleaned_price)
    except (ValueError, TypeError):
        return None

# --- Format Comparison Summary (Updated for cumulative comparisons) ---
def format_comparison_summary(
    current_items, current_receipt_total_str, current_receipt_paid, current_online_total, 
    current_found_count, current_assumed_count,
    all_items, all_receipts_paid, all_online_total,
    all_found_count, all_assumed_count
):
    """Creates a comparison summary showing both current receipt and cumulative totals."""
    
    # Calculate differences
    current_diff = current_receipt_paid - current_online_total
    current_diff_status = 'cheaper online' if current_diff > 0 else 'cheaper in store' if current_diff < 0 else 'same price'
    
    all_diff = all_receipts_paid - all_online_total
    all_diff_status = 'cheaper online' if all_diff > 0 else 'cheaper in store' if all_diff < 0 else 'same price'
    
    # Start with a clean HTML structure
    html = f"""
    <div style="font-size: 0.9rem; line-height: 1.3;">
        <div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #eee;">
            <div style="font-weight: 600; font-size: 1rem; margin-bottom: 8px; color: var(--primary-color);">Latest Receipt</div>
            <div style="margin-bottom: 6px; display: flex; justify-content: space-between;">
                <span><b>Receipt Total:</b></span> 
                <span>${current_receipt_paid:.2f}</span>
            </div>"""
    
    # Add current receipt online comparison if available
    if current_found_count > 0 or current_assumed_count > 0:
        current_total_compared = current_found_count + current_assumed_count
        
        # Add assumption note for current receipt if needed
        current_assumption_note = ""
        if current_assumed_count > 0:
            current_assumption_note = f"<span style='font-size: 0.7rem; color: #666;'> (includes {current_assumed_count} items assumed same price)</span>"
        
        html += f"""
        <div style="margin-bottom: 6px; display: flex; justify-content: space-between;">
            <span><b>Online Total:</b> <span style="color: #666; font-size: 0.8rem;">({current_total_compared}/{len(current_items)} items)</span> {current_assumption_note}</span>
            <span>${current_online_total:.2f}</span>
        </div>
        <div style="margin-bottom: 10px; display: flex; justify-content: space-between; border-top: 1px solid #eee; padding-top: 6px;">
            <span><b>Difference:</b></span>
            <span style="color: {'green' if current_diff > 0 else 'red' if current_diff < 0 else 'black'}">
                ${abs(current_diff):.2f} {current_diff_status}
            </span>
        </div>"""
    else:
        html += """
        <div style="margin-bottom: 10px;">
            <span><b>Online Total:</b></span> <span>N/A (No items found)</span>
        </div>"""
    
    # Add cumulative section if we have multiple receipts (detected by checking if all_receipts_paid > current_receipt_paid)
    if len(all_items) > len(current_items) or abs(all_receipts_paid - current_receipt_paid) > 0.01:
        html += f"""
        </div>
        <div style="margin-bottom: 16px; padding: 12px; background-color: var(--bg-light); border-radius: 8px;">
            <div style="font-weight: 600; font-size: 1rem; margin-bottom: 8px; color: var(--primary-color);">All Receipts (Cumulative)</div>
            <div style="margin-bottom: 6px; display: flex; justify-content: space-between;">
                <span><b>Total Paid:</b></span>
                <span>${all_receipts_paid:.2f}</span>
            </div>"""
            
        if all_found_count > 0 or all_assumed_count > 0:
            all_total_compared = all_found_count + all_assumed_count
            
            # Add assumption note for all receipts if needed
            all_assumption_note = ""
            if all_assumed_count > 0:
                all_assumption_note = f"<span style='font-size: 0.7rem; color: #666;'> (includes {all_assumed_count} items assumed same price)</span>"
            
            html += f"""
            <div style="margin-bottom: 6px; display: flex; justify-content: space-between;">
                <span><b>Online Total:</b> <span style="color: #666; font-size: 0.8rem;">({all_total_compared}/{len(all_items)} items)</span> {all_assumption_note}</span>
                <span>${all_online_total:.2f}</span>
            </div>
            <div style="margin-bottom: 10px; display: flex; justify-content: space-between; border-top: 1px solid #eee; padding-top: 6px;">
                <span><b>Total Savings:</b></span>
                <span style="color: {'green' if all_diff > 0 else 'red' if all_diff < 0 else 'black'}">
                    ${abs(all_diff):.2f} {all_diff_status}
                </span>
            </div>"""
        else:
            html += """
            <div style="margin-bottom: 10px;">
                <span><b>Online Total:</b></span> <span>N/A (No items found)</span>
            </div>"""
        html += "</div>"
    else:
        html += "</div>"
    
    # Format the items section (item details from current receipt)
    if current_items:
        html += f"""
        <div style="margin-top: 10px;">
            <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 8px; color: var(--primary-color);">
                Current Receipt Items ({len(current_items)})
            </div>
        """
        
        for i, result in enumerate(current_items):
            item_name = result.get('item', 'Unknown')
            price_paid = result.get('price_paid', 'N/A')
            online_details = result.get('online_details', 'Not found')
            product_url = result.get('url')
            
            # Style by comparison status
            status_color = ""
            if "Not Found" in online_details:
                status_color = "#999" # Gray for not found
            elif "Assumed same" in online_details:
                status_color = "#666" # Darker gray for assumed
            
            # Create item name cell - add link if URL exists
            if product_url:
                item_cell = f"""<div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 50%;">
                    <a href="{product_url}" target="_blank" style="color: var(--primary-color); text-decoration: none;">
                        {item_name} <span style="font-size: 0.6rem;">🔗</span>
                    </a>
                </div>"""
            else:
                item_cell = f"""<div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 50%;">
                    {item_name}
                </div>"""
            
            html += f"""
            <div style="margin: 4px 0; padding: 2px 0; display: flex; justify-content: space-between; border-bottom: 1px dotted #eee;">
                {item_cell}
                <div>
                    <span style="margin-right: 8px;">{price_paid}</span>
                    <span style="color: {status_color}">{online_details}</span>
                </div>
            </div>"""
        
        html += "</div>"
    
    html += "</div>" # Close the outer container
    return html 
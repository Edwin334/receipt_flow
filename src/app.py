import gradio as gr
import pandas as pd

# Initialize config (loads .env, configures AI SDKs)
# This needs to be done early, before other modules try to use API keys or SDKs.
import src.config 

from src.core.logic import process_receipt, clear_inventory, prepare_for_next_receipt

# --- Gradio Interface (Completely Redesigned) ---

title = "Receipt Flow"
description = "Track inventory & compare prices online"

# Define custom CSS for a more polished, modern design
custom_css = """
:root {
  --primary-color: #6366f1;
  --primary-light: #818cf8;
  --secondary-color: #f59e0b;
  --accent-color: #10b981;
  --text-color: #374151;
  --bg-light: #f9fafb;
  --border-color: #e5e7eb;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --radius: 8px;
}

.gradio-container {max-width: 800px !important; margin: 0 auto !important;}

/* Modern Card Elements */
.card {
  background-color: white;
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 12px 16px !important;
  margin-bottom: 12px !important;
  border: 1px solid var(--border-color);
}

.card-header {
  font-weight: 600;
  font-size: 0.85rem !important;
  color: var(--text-color);
  margin-bottom: 10px !important;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

/* Typography */
.compact-text {font-size: 0.75rem !important; padding: 3px !important; color: var(--text-color);}
.small-text {font-size: 0.65rem !important; color: var(--text-color);}
.tiny-text {font-size: 0.6rem !important; color: var(--text-color);}

/* Layout */
.compact-group {gap: 5px !important; padding: 0 !important; margin-bottom: 10px !important;}
.compact-interface {gap: 8px !important;}
.compact-block {padding: 0 !important;}
.spacer {margin-top: 12px !important;}

/* Components */
.compact-button {
  height: 36px !important; 
  min-height: 36px !important; 
  font-size: 0.8rem !important; 
  padding: 0 16px !important;
  border-radius: var(--radius) !important;
  transition: all 0.2s !important;
}
.primary-button {
  background-color: var(--primary-color) !important;
  color: white !important;
}
.primary-button:hover {
  background-color: var(--primary-light) !important;
}

.compact-textbox textarea {
  padding: 8px 12px !important; 
  font-size: 0.8rem !important; 
  min-height: 20px !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border-color) !important;
}

/* Table */
.compact-dataframe {border-radius: var(--radius) !important; overflow: hidden !important;}
.compact-dataframe table {font-size: 0.75rem !important; width: 100% !important;}
.compact-dataframe th {
  background-color: var(--bg-light) !important;
  font-weight: 600 !important;
  padding: 8px !important;
  text-align: left !important;
}
.compact-dataframe td {padding: 6px 8px !important; border-bottom: 1px solid var(--border-color) !important;}

.compact-file {padding: 8px !important; border-radius: var(--radius) !important;}

/* Upload Area */
.upload-area {
  border: 2px dashed var(--border-color) !important;
  border-radius: var(--radius) !important;
  background-color: var(--bg-light) !important;
  transition: all 0.2s !important;
  height: 180px !important;
}
.upload-area:hover {
  border-color: var(--primary-color) !important;
}

/* Misc */
.center-text {text-align: center;}
h1 {
  font-size: 1.4rem !important; 
  margin: 12px 0 4px 0 !important;
  color: var(--text-color);
  font-weight: 600 !important;
}
.app-tagline {
  color: #6b7280 !important;
  margin-bottom: 16px !important;
}
.comparison-container {
  margin-top: 10px !important;
  padding: 0 !important;
}
.table-container {
  margin-top: 16px !important;
  padding: 0 !important;
}
"""

with gr.Blocks(theme=gr.themes.Soft(), css=custom_css, elem_classes="compact-interface") as iface:
    inventory_state = gr.State([])

    # Header
    gr.Markdown(f"<h1>{title}</h1>", elem_classes="center-text")
    gr.Markdown(f"<p class='app-tagline center-text small-text'>{description}</p>")

    # Main Container
    with gr.Row(equal_height=True):
        # Left: Receipt Upload Section
        with gr.Column(scale=1):
            with gr.Group(elem_classes="card"):
                gr.Markdown("<div class='card-header'>Upload Receipt</div>", elem_classes="compact-text")
                receipt_input = gr.Image(type="pil", label=None, show_label=False, elem_classes="upload-area")
        
        # Right: Controls Section
        with gr.Column(scale=1):
            with gr.Group(elem_classes="card"):
                gr.Markdown("<div class='card-header'>Controls</div>", elem_classes="compact-text")
                
                # Action Buttons
                with gr.Row():
                    submit_button = gr.Button("Process Receipt", variant="primary", elem_classes="compact-button primary-button")
                    clear_button = gr.Button("Clear All", variant="secondary", elem_classes="compact-button")
                
                # New "Add Another Receipt" button
                add_receipt_button = gr.Button("Add Another Receipt", variant="primary", elem_classes="compact-button")
                
                # Receipt Total
                latest_total_output = gr.Textbox(label="Receipt Total", lines=1, interactive=False, elem_classes="compact-textbox")
                
                # Download CSV Button
                download_button = gr.File(label="Export Inventory", file_count="single", elem_classes="compact-file")
    
    # Price Comparison Section
    with gr.Group(elem_classes="card comparison-container"):
        gr.Markdown("<div class='card-header'>Price Comparison</div>", elem_classes="compact-text")
        comparison_summary_output = gr.HTML("<div class='compact-text'>Process a receipt to see price comparison</div>")
    
    # Inventory Table Section
    with gr.Group(elem_classes="card table-container"):
        gr.Markdown("<div class='card-header'>Inventory Items</div>", elem_classes="compact-text")
        inventory_output_df = gr.DataFrame(
            label=None, show_label=False,
            headers=["Item", "Price Paid", "Predicted Expiry Date"],
            interactive=False,
            elem_classes="compact-dataframe",
            wrap=True
        )

    # --- Event Listeners --- 
    submit_button.click(
        fn=process_receipt,
        inputs=[receipt_input, inventory_state],
        outputs=[inventory_output_df, latest_total_output, download_button, inventory_state, comparison_summary_output] 
    )

    clear_button.click(
        fn=clear_inventory,
        inputs=None, 
        outputs=[inventory_state, inventory_output_df, download_button, latest_total_output, comparison_summary_output] 
    )
    
    add_receipt_button.click(
        fn=prepare_for_next_receipt,
        inputs=[inventory_state],
        outputs=[receipt_input, inventory_state, inventory_output_df, latest_total_output, download_button, comparison_summary_output]
    )

# --- Launch the App ---
if __name__ == "__main__":
    # Note: The .env file is loaded by src.config when it's imported.
    # Ensure that you run this script from the root directory of the project for correct .env loading,
    # e.g., python src/app.py
    iface.launch() 
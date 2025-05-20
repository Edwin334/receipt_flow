# Receipt Flow

Track inventory & compare prices online.

## Setup

1.  Activate the virtual environment: `source venv/bin/activate` (on macOS/Linux) or `venv\Scripts\activate` (on Windows).
2.  Install dependencies: `pip install -r requirements.txt`
3.  Create a `.env` file in the root directory with your API keys:
    ```
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    PERPLEXITY_API_KEY="YOUR_PERPLEXITY_API_KEY"
    ```

## Running the App

```bash
python -m src.app
```

## Project Report: Receipt Flow - Inventory & Price Comparison Tool

**1. Problem Addressed:**

The "Receipt Flow" application is designed to address common challenges associated with managing household expenses and grocery inventory. Manually tracking purchased items, their expiry dates, and comparing in-store prices with online alternatives can be tedious and time-consuming. This tool aims to automate these processes by:

*   **Digitizing Receipts**: Allowing users to upload images of their receipts.
*   **Automated Item Extraction**: Identifying individual items, their prices paid, and the total amount from the receipt.
*   **Inventory Management**: Predicting typical expiry dates for perishable items to help reduce food waste.
*   **Price Comparison**: Fetching current online prices for the purchased items from major retailers to identify potential savings.
*   **Data Consolidation**: Maintaining a running inventory and providing summaries of spending and potential savings across multiple receipts.

The overall goal is to provide users with a convenient way to manage their purchases, track potential food spoilage, and make more informed purchasing decisions.

**2. LLM(s) Employed:**

The application leverages two Large Language Models (LLMs) through their respective APIs:

*   **Google Gemini (`gemini-2.0-flash` model):**
    *   **Purpose**: Used for its multimodal capabilities, specifically vision and text generation. It analyzes the uploaded receipt image to extract structured data.
    *   **Task**: It identifies purchased items, extracts the price paid for each, determines the overall total amount from the receipt, and, importantly, estimates the number of days until each item would typically expire based on common food storage knowledge. The prompt is carefully engineered to request the output in a specific JSON format for easier parsing.
    *   A mock version of this API call is also implemented for development and testing, or if an API key is not available.

*   **Perplexity AI (`sonar-pro` model):**
    *   **Purpose**: Utilized for its web-searching and information retrieval capabilities, focused on e-commerce.
    *   **Task**: For each item extracted by Gemini, the Perplexity API is queried to find its current price and a direct product link from major online grocery retailers (e.g., Amazon, Walmart, Target). The prompt guides Perplexity to return the price, retailer, and URL in a JSON format. It also handles cases where the item is not found or the price varies.

**3. Implementation Process:**

The project was initially developed as a single-file Python application (`app.py`) using the Gradio library for the user interface. Recognizing the need for better organization, maintainability, and adherence to standard open-source practices, the application underwent a significant refactoring process:

*   **Modular Structure**: A `src` directory was created to house all source code, with subdirectories for:
    *   `config.py`: Manages API key loading (from a `.env` file) and initial configuration for the AI SDKs.
    *   `services/`: Contains client modules for interacting with external APIs:
        *   `gemini_client.py`: Encapsulates all logic for calling the Gemini Vision API (and its mock).
        *   `perplexity_client.py`: Encapsulates all logic for calling the Perplexity API.
    *   `core/`: Contains the core business logic and utilities:
        *   `logic.py`: Handles the main workflow of processing receipts, managing inventory state (including cumulative totals), interacting with the AI services, and preparing data for the UI.
        *   `utils.py`: Provides helper functions like parsing price strings from text and formatting the HTML summary for price comparisons.
    *   `app.py`: (Now located in `src/app.py`) Defines the Gradio user interface, sets up event listeners for user interactions, and serves as the main entry point for running the application.

*   **Dependency Management**: A `requirements.txt` file was created to list all necessary Python packages (`gradio`, `pandas`, `python-dotenv`, `google-generativeai`, `Pillow`, `requests`), enabling easy environment setup.

*   **Documentation**: A `README.md` file was added, providing a project description, setup instructions (including virtual environment and API key setup), and the command to run the application. This report is also part of the README.

*   **Import Resolution**: Addressed initial `ModuleNotFoundError` issues by structuring the project as a Python package and updating the run command to `python -m src.app`, ensuring correct relative imports. The `.env` file path loading in `config.py` was also corrected to properly locate the file from the project root.

**4. Evaluation Process:**

The evaluation of the application focuses on several key aspects:

*   **Core Functionality**:
    *   **Receipt Processing**: Successfully uploads and processes receipt images.
    *   **Data Extraction**: Accurately extracts items, prices, and totals using Gemini. The quality of extraction depends on the clarity of the receipt and the LLM's capabilities.
    *   **Expiry Prediction**: Provides reasonable expiry date estimations.
    *   **Price Comparison**: Fetches relevant online prices using Perplexity. The success rate depends on item name clarity and availability on major retail sites.
    *   **Inventory Tracking**: Maintains and displays a cumulative inventory and price comparison summary.

*   **API Integration**:
    *   Ensuring API calls are correctly authenticated and structured.
    *   Robust parsing of JSON responses from both LLMs.
    *   Graceful handling of API errors, rate limits, or unexpected response formats, providing feedback to the user or falling back to assumed values where appropriate (e.g., assuming online price is the same as receipt price if not found).

*   **Modularity and Maintainability**:
    *   The refactoring into a multi-file structure is evaluated by its improvement in code organization, readability, and ease of making future modifications or extensions to specific components (e.g., adding a new AI service or changing UI elements) without impacting the entire codebase.

*   **User Experience (Gradio UI)**:
    *   The UI is designed to be simple and intuitive: clear instructions for uploading receipts, easily understandable display of inventory and price comparison results.
    *   Responsive feedback during processing and clear error messages.

*   **Error Handling and Robustness**:
    *   Implementation of `try-except` blocks for critical operations like API calls, file I/O, and data parsing.
    *   The application should handle scenarios like missing API keys (falling back to mock data or displaying warnings) or malformed API responses.

*   **Setup and Execution**:
    *   The clarity and correctness of `README.md` instructions for setting up the environment and running the application.
    *   The completeness of `requirements.txt`.

Continuous evaluation would involve testing with a diverse range of receipt formats, monitoring the accuracy of LLM responses, and gathering user feedback to identify areas for improvement in both functionality and user interface.

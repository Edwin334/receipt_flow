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
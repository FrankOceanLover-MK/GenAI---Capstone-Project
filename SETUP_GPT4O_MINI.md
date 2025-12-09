# GPT-4o-mini Setup Guide

This application uses **GPT-4o-mini** from OpenAI as the AI model for the car shopping assistant.

## Quick Setup

### 1. Your OpenAI API Key is Already Configured

Your `.env` file already has the API key set and ready to use!

### 2. Start the Backend

```bash
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

You should see output confirming GPT-4o-mini is loaded:
```
[DEBUG] Loaded LLM_API_BASE: https://api.openai.com/v1
[DEBUG] Loaded LLM_MODEL_NAME: gpt-4o-mini
```

### 3. Start the Frontend

In a separate terminal:

```bash
venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py
```

### 4. Use the Application

1. Open your browser to http://localhost:8501
2. The sidebar will show "Using GPT-4o-mini by OpenAI"
3. Start asking questions about cars!

## Example Queries

- "I need a reliable family SUV under $30,000"
- "Show me fuel-efficient sedans with at least 35 MPG"
- "I'm looking for used pickup trucks within 50 miles"

## Troubleshooting

**Error: "OPENAI_API_KEY environment variable is not set"**
- Restart the backend server

**Error: "LLM server returned 401"**
- API key is invalid - check `.env` file

**Error: "LLM server returned 429"**
- Rate limit or out of credits

## Cost Information

GPT-4o-mini pricing:
- Input: ~$0.15 per 1M tokens
- Output: ~$0.60 per 1M tokens
- Average query: $0.0005 - $0.001

Very affordable for most use cases!

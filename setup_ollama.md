# Ollama Setup Instructions

## 1. Install Ollama (if you haven't already)
- Download from: https://ollama.com/download
- Install the Windows version
- Ollama will start automatically as a background service

## 2. Pull the Llama 3 model
Open a new terminal (Command Prompt or PowerShell) and run:
```bash
ollama pull llama3
```

This will download the Llama 3 model (about 4.7GB). It may take a few minutes.

## 3. Test Ollama
Test that Ollama is working:
```bash
ollama run llama3 "Hello, how are you?"
```

If you see a response, Ollama is working correctly! Press Ctrl+D or type `/bye` to exit.

## 4. Verify the API endpoint
Ollama runs an OpenAI-compatible API at: http://127.0.0.1:11434/v1

You can test it with:
```bash
curl http://127.0.0.1:11434/api/tags
```

## Alternative: Use a different LLM model
If you want to use a different model, you can:
- See available models at: https://ollama.com/library
- Pull any model: `ollama pull <model-name>`
- Update your .env file with the model name

Popular alternatives:
- `ollama pull llama3.2` (smaller, faster)
- `ollama pull mistral` (good alternative)
- `ollama pull phi3` (very small and fast)

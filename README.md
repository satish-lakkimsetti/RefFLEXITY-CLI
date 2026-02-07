# RefFLEXITY-CLI

**A Privacy-First Local AI Web Search Tool**

RefFLEXITY-CLI is a command-line tool that lets you search the web and get AI-powered answers **entirely locally** — no data leaves your machine. It uses DuckDuckGo for privacy-respecting web search and runs the AI reasoning on your own Ollama instance.

## Features

- **100% local & private**: Searches via DuckDuckGo HTML (no API keys), AI processing via Ollama.
- **Clean article extraction**: Uses `readability-lxml` for high-quality main content.
- **Fast page fetching**: Reads multiple sources efficiently.
- **Smooth streaming responses**: Real-time typing effect with stop support (Ctrl+C).
- **Top 5 results**: Shows and uses the top 5 search results.
- **No cloud dependency**: Everything runs on your machine.

## Prerequisites

- Python 3.8+
- Ollama installed and running (`ollama serve`)
- At least one model pulled in Ollama (e.g., `ollama pull llama3.2` or any compatible model)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/RefFLEXITY-CLI.git
   cd RefFLEXITY-CLI
   ```

2. (Recommended) Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Make sure Ollama is running in another terminal:
   ```bash
   ollama serve
   ```

## Usage

Run the tool:
```bash
python main.py
```

- Select a model from the list (or pull a new one with the download option).
- Type your query at "Search: ".
- Use `back` to return to model selection.
- Use `exit` to quit.

During response generation:
- Press **Ctrl+C** at any time to stop the response.

## Example

```
Search: latest Python release
```

The tool will search DuckDuckGo, read the top 5 results, and stream a detailed, context-grounded answer.

## Contributing

Feel free to open issues or PRs! This is a personal project focused on privacy and local AI.

## License

MIT License

Developed by Satish Lakkimsetti — privacy-first search for everyone.

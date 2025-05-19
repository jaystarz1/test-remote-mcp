# Research Papers MCP Server & Client

## Overview

This project lets you search academic papers by topic, save summaries and details, and access them with easy tools. The server is written in Python using FastAPI and FastMCP, and the client connects to it using MCP protocol commands.

## Features

- Search for papers by topic from arXiv.
- Save and retrieve paper info, organized by topic.
- Browse topics and see all papers for a topic.
- Ready for local use or remote deployment (e.g., Render).

## Requirements

- Python 3.11.x (or higher)
- Install dependencies with:  
  `pip install -r requirements.txt`

## How to Run

### 1. Clone this repo and go to the folder:
```bash
git clone <your-repo-url>
cd <your-folder>
```

### 2. (Optional but recommended) Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Mac/Linux
# OR
.venv\Scripts\activate       # On Windows
```

### 3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 4. Run the server:
```bash
python research_server.py
# or, if using uv:
uv run research_server.py
```
- Server will run on port 8000.

### 5. Run the client (optional):
```bash
python mcp_chatbot.py
```
- This will connect to the server and let you run tools and prompts.

## Deploying Remotely

- Push your code to GitHub.
- Use a service like Render or Cloudflare Workers.
- Make sure your `requirements.txt` is in the root folder.
- Set the start command to `python research_server.py`.

## Claude Desktop Connection

If you want Claude Desktop to use your server, add it to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://<your-server-url>/sse"
      ]
    }
  }
}
```
Replace `<your-server-url>` with your deployed server address.

## Files

- `research_server.py` — The server with search and data tools.
- `mcp_chatbot.py` — The sample client to connect and run commands.
- `requirements.txt` — List of all required Python packages.

## Notes

- You can edit and add new tools/resources in `research_server.py`.
- All paper info is saved under the `papers` directory by topic.
- You can use and expand this as a base for any similar MCP/AI project.

---

**Questions?**  
Open an issue or contact the repo owner.

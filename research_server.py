from fastapi import FastAPI
from fastmcp import FastMCP
import arxiv
import json
import os
from typing import List

PAPER_DIR = "papers"

app = FastAPI()
mcp = FastMCP("research", app=app, port=8000)

@app.get("/")
def root():
    return {"status": "ok"}

@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    client = arxiv.Client()
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    papers = client.results(search)
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, "papers_info.json")
    try:
        with open(file_path, "r") as f:
            papers_info = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}
    paper_ids = []
    for paper in papers:
        pid = paper.get_short_id()
        paper_ids.append(pid)
        paper_info = {
            'title': paper.title,
            'authors': [a.name for a in paper.authors],
            'summary': paper.summary,
            'pdf_url': paper.pdf_url,
            'published': str(paper.published.date())
        }
        papers_info[pid] = paper_info
    with open(file_path, "w") as f:
        json.dump(papers_info, f, indent=2)
    print(f"Results are saved in: {file_path}")
    return paper_ids

@mcp.tool()
def extract_info(paper_id: str) -> str:
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as f:
                        papers_info = json.load(f)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except Exception:
                    continue
    return f"No saved information related to paper {paper_id}."

@mcp.resource("papers://folders")
def get_available_folders() -> str:
    folders = []
    if os.path.exists(PAPER_DIR):
        for topic_dir in os.listdir(PAPER_DIR):
            topic_path = os.path.join(PAPER_DIR, topic_dir)
            if os.path.isdir(topic_path):
                papers_file = os.path.join(topic_path, "papers_info.json")
                if os.path.exists(papers_file):
                    folders.append(topic_dir)
    content = "# Available Topics\n\n"
    if folders:
        for folder in folders:
            content += f"- {folder}\n"
        content += "\nUse @<folder> to access papers in that topic.\n"
    else:
        content += "No topics found.\n"
    return content

@mcp.resource("papers://{topic}")
def get_topic_papers(topic: str) -> str:
    topic_dir = topic.lower().replace(" ", "_")
    papers_file = os.path.join(PAPER_DIR, topic_dir, "papers_info.json")
    if not os.path.exists(papers_file):
        return f"# No papers found for topic: {topic}\nTry searching first."
    try:
        with open(papers_file, 'r') as f:
            papers_data = json.load(f)
        content = f"# Papers on {topic.replace('_', ' ').title()}\n\nTotal papers: {len(papers_data)}\n\n"
        for paper_id, paper_info in papers_data.items():
            content += f"## {paper_info['title']}\n"
            content += f"- **Paper ID**: {paper_id}\n"
            content += f"- **Authors**: {', '.join(paper_info['authors'])}\n"
            content += f"- **Published**: {paper_info['published']}\n"
            content += f"- **PDF URL**: [{paper_info['pdf_url']}]({paper_info['pdf_url']})\n\n"
            content += f"### Summary\n{paper_info['summary'][:500]}...\n\n---\n\n"
        return content
    except json.JSONDecodeError:
        return f"# Error reading papers data for {topic}\nFile is corrupted."

@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    """Generate a prompt for Claude to find and discuss academic papers on a specific topic."""
    return f"""Search for {num_papers} academic papers about '{topic}' using the search_papers tool. Follow these instructions:
    1. First, search for papers using search_papers(topic='{topic}', max_results={num_papers})
    2. For each paper found, extract and organize the following information:
       - Paper title
       - Authors
       - Publication date
       - Brief summary of the key findings
       - Main contributions or innovations
       - Methodologies used
       - Relevance to the topic '{topic}'
    3. Provide a comprehensive summary that includes:
       - Overview of the current state of research in '{topic}'
       - Common themes and trends across the papers
       - Key research gaps or areas for future investigation
       - Most impactful or influential papers in this area
    4. Organize your findings in a clear, structured format with headings and bullet points for easy readability.
    Please present both detailed information about each paper and a high-level synthesis of the research landscape in {topic}."""

if __name__ == "__main__":
    mcp.run(transport='sse', host="0.0.0.0", port=8000)

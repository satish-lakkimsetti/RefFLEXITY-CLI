#!/usr/bin/env python3
"""
RefFLEXITY-CLI
Privacy-first local AI web search tool
Developed by Satish Lakkimsetti
"""

import sys
import json
from json import JSONDecodeError
import httpx
import time
import itertools
import threading
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import quote_plus, urlparse, parse_qs
from pyfiglet import figlet_format
from typing import List, Dict

OLLAMA_BASE = "http://localhost:11434"
MAX_RESULTS = 5
MAX_TEXT_PER_PAGE = 5000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

# Spinner animation on the same line with Ctrl+C hint
def spinner(stop_event):
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if stop_event.is_set():
            break
        print(f"\rThinking... {c} (press Ctrl+C to stop)", end="", flush=True)
        time.sleep(0.1)

def print_banner():
    banner = figlet_format("RefFLEXITY-CLI", font="standard")
    lines = banner.splitlines()
    for line in lines:
        print(f"\033[97m{line}\033[0m")
    print("\033[97m          A PRIVACY FOCUSED LOCAL AI WEB SEARCH TOOL\033[0m")

def check_ollama_running() -> bool:
    try:
        resp = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=4)
        return resp.status_code == 200
    except:
        return False

def get_available_models() -> List[Dict]:
    try:
        resp = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=8)
        resp.raise_for_status()
        return resp.json().get("models", [])
    except:
        return []

def pull_model(model_name: str):
    if not model_name:
        print("Error: No model name provided.")
        return

    print()
    print(f"Pulling {model_name}...")
    payload = {"name": model_name}
    current_layer = None
    first_status = True
    try:
        with httpx.stream("POST", f"{OLLAMA_BASE}/api/pull", json=payload, timeout=None) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                try:
                    data = json.loads(line)
                    if "error" in data:
                        print()
                        print(f"Error: {data['error']}")
                        return

                    status = data.get("status", "")

                    if status and not status.startswith("pulling ") and "digest" not in data:
                        if first_status:
                            print()
                            print(status)
                            first_status = False
                        else:
                            print()
                            print(status)
                        continue

                    if "digest" in data:
                        digest_short = data["digest"][:12]
                        if current_layer != digest_short:
                            print()
                            print(f"Downloading layer {digest_short}...")
                            current_layer = digest_short

                        if "total" in data:
                            try:
                                total = int(data["total"])
                                completed = int(data.get("completed", 0))
                                if total > 0:
                                    pct = (completed / total) * 100
                                    bar_length = 30
                                    filled = int(bar_length * completed // total)
                                    bar = "█" * filled + "░" * (bar_length - filled)
                                    mb_completed = completed // (1024 * 1024)
                                    mb_total = total // (1024 * 1024)
                                    progress_line = f"{bar} {pct:.1f}% ({mb_completed}/{mb_total} MB)"
                                    print(progress_line, end="\r")
                                    sys.stdout.flush()
                            except (TypeError, ValueError, ZeroDivisionError):
                                pass

                except JSONDecodeError:
                    pass

        print()
        print(f"{model_name} downloaded successfully.")
    except Exception as e:
        print()
        print(f"Failed to pull {model_name}: {e}")

def search_duckduckgo(query: str) -> List[Dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for div in soup.find_all("div", class_="result")[:MAX_RESULTS]:
            a = div.find("a", class_="result__a")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if "uddg=" in href:
                real_url = parse_qs(urlparse(href).query).get("uddg", [""])[0]
            else:
                real_url = href
            results.append({"title": title, "href": real_url})
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

def extract_main_text(html: str) -> str:
    doc = Document(html)
    summary_html = doc.summary()
    soup = BeautifulSoup(summary_html, "html.parser")
    
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe", "noscript"]):
        tag.decompose()
    
    text = soup.get_text(separator=" ")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = " ".join(lines)
    
    return cleaned[:MAX_TEXT_PER_PAGE]

def fetch_page_text(url: str) -> str:
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        return extract_main_text(resp.text)
    except:
        return ""

def stream_ollama(query: str, context: str, model: str):
    system_prompt = (
        "Use the provided web search context to answer the user's question.\n\n"
        "Be detailed, accurate, and thorough, sticking only to information from the context.\n\n"
        "If the context doesn't have enough relevant information, say so naturally (e.g., \"The sources don't provide details on that\").\n\n"
        "Answer in natural, readable plain text."
    )

    user_prompt = f"Context from web search:\n{context}\n\nQuestion: {query}\n\nAnswer using the context."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": True
    }

    print("\nThinking... (press Ctrl+C to stop)", end="", flush=True)

    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=spinner, args=(stop_event,))
    spinner_thread.start()

    first_chunk = True
    try:
        with httpx.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        if first_chunk:
                            stop_event.set()
                            spinner_thread.join()
                            print()  # Move to new line (keep thinking line visible)
                            print()  # One blank line after thinking
                            print("AI Response: ", end="", flush=True)
                            first_chunk = False
                        for char in content:
                            print(char, end="", flush=True)
                            time.sleep(0.05)
                except JSONDecodeError:
                    pass
        # No extra newline — response ends, next loop handles spacing
    except KeyboardInterrupt:
        stop_event.set()
        spinner_thread.join()
        print()
        print("Response stopped by user.")
        print()
    except Exception as e:
        stop_event.set()
        spinner_thread.join()
        print()
        print(f"Ollama error: {e}")

def process_query(query: str, model: str):
    if not query:
        return

    results = search_duckduckgo(query)

    if not results:
        print("No results found.")
        context = ""
    else:
        print()
        print("Sources:")
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r['title']}")
            print(f" {r['href']}")

        print()
        print("Reading pages...")

        context_parts = []
        for i, r in enumerate(results, 1):
            text = fetch_page_text(r["href"])
            if text:
                context_parts.append(f"Source {i}: {r['title']}\n{r['href']}\n\n{text}\n\n")

        context = "".join(context_parts)

    stream_ollama(query, context, model)

def show_menu(models: List[Dict]):
    print()
    print("Choose a model / option:")
    option_num = 1
    for m in models:
        size = f"({m['size']/(1024**3):.1f} GB)" if m.get("size") else ""
        print(f" {option_num}. {m['name']} {size}")
        option_num += 1

    print(f" {option_num}. Download (pull) a new model")
    pull_num = option_num
    option_num += 1
    print(f" {option_num}. Exit the application")

    while True:
        print()
        try:
            choice = int(input("Select option: ").strip())
            if 1 <= choice <= option_num:
                return choice, pull_num
            else:
                print()
                print("Invalid choice. Try Again.")
        except ValueError:
            print()
            print("Please enter a number.")

def main():
    if not check_ollama_running():
        print("Error: Ollama is not running. Start it with 'ollama serve'.")
        sys.exit(1)

    while True:
        print_banner()
        models = get_available_models()
        choice, pull_choice = show_menu(models)

        total_options = len(models) + 2
        exit_choice = total_options

        if choice == exit_choice:
            print()
            print("Goodbye!")
            print()
            sys.exit(0)

        if choice == pull_choice:
            model_name = input("\nEnter model name to pull: ").strip()
            pull_model(model_name)
            continue

        selected_model = models[choice - 1]["name"]
        print()
        print(f"Using model: {selected_model}")
        print()

        while True:
            print("Ask / Search for anything below (type 'back' to return to model selection, 'exit' to quit)")
            print()
            query = input("Search: ").strip()
            if query.lower() == "exit":
                print()
                print("Goodbye!")
                print()
                sys.exit(0)
            if query.lower() == "back":
                break
            process_query(query, selected_model)

if __name__ == "__main__":
    main()

import os
import shutil
from fastapi import FastAPI, Query
from parser_service import parse
from config import OUTPUT_FOLDER, INDEX_FILE, TOKENS_FOLDER, LEMMAS_FOLDER

import stanza
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

app = FastAPI()

stanza.download('en')
nlp = stanza.Pipeline(
    'en',
    processors='tokenize,pos,lemma',
    tokenize_no_ssplit=True,
    use_gpu=False
)

@app.post("/api/crawler/pars")
def start_parse():
    created_files = parse()
    return {"downloaded": created_files}

@app.delete("/api/crawler/clean")
def delete_files():
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    if os.path.exists(TOKENS_FOLDER):
        shutil.rmtree(TOKENS_FOLDER)
    if os.path.exists(LEMMAS_FOLDER):
        shutil.rmtree(LEMMAS_FOLDER)
    return {"status": "cleaned"}

def process_file(filename):
    """Обрабатывает один файл: создает файлы с токенами и леммами"""
    filepath = os.path.join(OUTPUT_FOLDER, f"{filename}.txt")
    if not os.path.exists(filepath):
        return
    
    tokens_filepath = os.path.join(TOKENS_FOLDER, f"{filename}_tokens.txt")
    lemmas_filepath = os.path.join(LEMMAS_FOLDER, f"{filename}_lemmas.txt")
    
    with open(filepath, "r", encoding="utf-8") as f:
        html_text = f.read()
    
    text = BeautifulSoup(html_text, "html.parser").get_text(separator=" ")
    
    all_tokens = set()
    lemmas_dict = {}
    
    doc = nlp(text)
    for sentence in doc.sentences:
        for word in sentence.words:
            token = word.text.lower()
            lemma = word.lemma.lower()
            
            if not token.isalpha() or token in (
                "the", "a", "and", "or", "in", "on", "at", "for", "of"
            ):
                continue
            
            all_tokens.add(token)
            lemmas_dict.setdefault(lemma, set()).add(token)
    
    with open(tokens_filepath, "w", encoding="utf-8") as f:
        for token in sorted(all_tokens):
            f.write(token + "\n")
    
    with open(lemmas_filepath, "w", encoding="utf-8") as f:
        for lemma, tokens in lemmas_dict.items():
            f.write(f"{lemma} " + " ".join(sorted(tokens)) + "\n")

@app.post("/api/crawler/tokenize")
def tokenize_files():
    if not os.path.exists(INDEX_FILE):
        return {"error": "No files to process"}
    
    os.makedirs(TOKENS_FOLDER, exist_ok=True)
    os.makedirs(LEMMAS_FOLDER, exist_ok=True)
    
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        files = [line.strip().split()[0] for line in f.readlines()]
    
    max_workers = min(8, os.cpu_count() or 4)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_file, fn): fn for fn in files}
        
        for future in as_completed(future_to_file):
            try:
                future.result()
            except Exception:
                pass
    
    return {"status": "tokenization completed"}





@app.get("/api/crawler/search")
def search_word(word: str = Query(..., min_length=1), context_chars: int = 30):
    word_lower = word.lower()
    results = []
    
    if not os.path.exists(OUTPUT_FOLDER):
        return {"error": "Output folder not found"}
    
    for filename in os.listdir(OUTPUT_FOLDER):
        if filename.endswith(".txt") and not filename.endswith("_tokens.txt") and not filename.endswith("_lemmas.txt"):
            filepath = os.path.join(OUTPUT_FOLDER, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read().lower()
                idx = text.find(word_lower)
                if idx != -1:
                    start = max(0, idx - context_chars)
                    end = min(len(text), idx + len(word_lower) + context_chars)
                    snippet = text[start:end]
                    
                    base_name = filename.replace('.txt', '')
                    
                    results.append({
                        "file": filename,
                        "snippet": snippet,
                        "tokens_file": f"{base_name}_tokens.txt",
                        "lemmas_file": f"{base_name}_lemmas.txt"
                    })
    
    if not results:
        return {"status": "not found"}
    
    return {"word": word, "found_in": results}



@app.get("/api/crawler/file/{filename}/tokens")
def get_file_tokens(filename: str):
    tokens_file = os.path.join(TOKENS_FOLDER, f"{filename}_tokens.txt")
    
    if not os.path.exists(tokens_file):
        return {"error": "Tokens file not found"}
    
    with open(tokens_file, "r", encoding="utf-8") as f:
        tokens = [line.strip() for line in f.readlines()]
    
    return {"tokens": tokens}

@app.get("/api/crawler/file/{filename}/lemmas")
def get_file_lemmas(filename: str):
    lemmas_file = os.path.join(LEMMAS_FOLDER, f"{filename}_lemmas.txt")
    
    if not os.path.exists(lemmas_file):
        return {"error": "Lemmas file not found"}
    
    lemmas = []
    with open(lemmas_file, "r", encoding="utf-8") as f:
        for line in f.readlines():
            parts = line.strip().split()
            if parts:
                lemmas.append({
                    "lemma": parts[0],
                    "tokens": parts[1:] if len(parts) > 1 else []
                })
    
    return {"lemmas": lemmas}
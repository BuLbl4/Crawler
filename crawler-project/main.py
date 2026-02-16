import os
import shutil
from fastapi import FastAPI, Query
from parser_service import parse
from config import OUTPUT_FOLDER, INDEX_FILE, TOKENS_FILE, LEMMAS_FILE

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
    return {"Downloaded": created_files}

@app.delete("/api/crawler/clean")
def delete_files():
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    if os.path.exists(TOKENS_FILE):
        os.remove(TOKENS_FILE)
    if os.path.exists(LEMMAS_FILE):
        os.remove(LEMMAS_FILE)
    return {"status": "cleaned"}

def process_file(filename):
    """
    Обрабатывает один файл: извлекает текст, токенизирует и собирает токены и леммы
    """
    filepath = os.path.join(OUTPUT_FOLDER, f"{filename}.txt")
    if not os.path.exists(filepath):
        return set(), {}

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

    return all_tokens, lemmas_dict


@app.post("/api/crawler/tokenize")
def tokenize_files():
    if not os.path.exists(INDEX_FILE):
        return {"error": "No files to process"}

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        files = [line.strip().split()[0] for line in f.readlines()]

    print(f"Starting tokenization for {len(files)} files...")

    all_tokens = set()
    lemmas_dict = {}

    max_workers = min(8, os.cpu_count() or 4) 
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_file, fn): fn for fn in files}

        for future in as_completed(future_to_file):
            fn = future_to_file[future]
            try:
                file_tokens, file_lemmas = future.result()
                all_tokens.update(file_tokens)
                for lemma, toks in file_lemmas.items():
                    lemmas_dict.setdefault(lemma, set()).update(toks)
                print(f"Processed file {fn}.txt | Tokens so far: {len(all_tokens)}")
            except Exception as e:
                print(f"Error processing {fn}.txt:", e)

    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        for token in sorted(all_tokens):
            f.write(token + "\n")

    with open(LEMMAS_FILE, "w", encoding="utf-8") as f:
        for lemma, tokens in lemmas_dict.items():
            f.write(f"{lemma} " + " ".join(sorted(tokens)) + "\n")

    print(f"Tokenization completed. Total tokens: {len(all_tokens)}, Total lemmas: {len(lemmas_dict)}")
    return {"status": "tokens and lemmas created", "tokens_file": TOKENS_FILE, "lemmas_file": LEMMAS_FILE}



@app.get("/api/crawler/search")
def search_word(word: str = Query(..., min_length=1), context_chars: int = 30):
    """
    Поиск слова в сохранённых файлах output
    """
    word_lower = word.lower()
    results = []

    if not os.path.exists(OUTPUT_FOLDER):
        return {"error": "Output folder not found"}

    for filename in os.listdir(OUTPUT_FOLDER):
        if filename.endswith(".txt"):
            filepath = os.path.join(OUTPUT_FOLDER, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read().lower()
                idx = text.find(word_lower)
                if idx != -1:
                    start = max(0, idx - context_chars)
                    end = min(len(text), idx + len(word_lower) + context_chars)
                    snippet = text[start:end]
                    results.append({
                        "file": filename,
                        "snippet": snippet
                    })

    if not results:
        return {"status": "not found"}

    return {"word": word, "found_in": results}



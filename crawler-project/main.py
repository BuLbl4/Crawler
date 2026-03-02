import os
import shutil
import re
from fastapi import FastAPI, Query
from parser_service import parse
from boolean_search import BooleanSearchEngine
from config import OUTPUT_FOLDER, INDEX_FILE, TOKENS_FOLDER, LEMMAS_FOLDER, INVERTED_INDEX_FILE, TFIDF_LEMMAS_FOLDER, TFIDF_FOLDER
from tfidf import TFIDFCalculator

import stanza
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

app = FastAPI()
search_engine = BooleanSearchEngine()

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




@app.post("/api/crawler/build-inverted-index")
def build_inverted_index():
    """Строит инвертированный индекс на основе файлов с токенами"""
    from config import INVERTED_INDEX_FILE
    
    if not os.path.exists(TOKENS_FOLDER):
        return {"error": "Tokens folder not found. Run tokenization first."}
    
    inverted_index = {}
    doc_count = 0
    
    for filename in os.listdir(TOKENS_FOLDER):
        if filename.endswith("_tokens.txt"):
            doc_id = int(filename.replace('_tokens.txt', ''))
            filepath = os.path.join(TOKENS_FOLDER, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    term = line.strip()
                    if term:
                        if term not in inverted_index:
                            inverted_index[term] = set()
                        inverted_index[term].add(doc_id)
            
            doc_count += 1
    
    with open(INVERTED_INDEX_FILE, 'w', encoding='utf-8') as f:
        for term in sorted(inverted_index.keys()):
            doc_ids = sorted(inverted_index[term])
            f.write(f"{term}:{','.join(map(str, doc_ids))}\n")
    
    global search_engine
    search_engine = BooleanSearchEngine()
    
    return {
        "status": "inverted index created",
        "terms_count": len(inverted_index),
        "documents_indexed": doc_count
    }

@app.post("/api/crawler/boolean-search")
def boolean_search(query: str):
    """
    Выполняет булев поиск по инвертированному индексу.
    
    Поддерживаемые операторы: AND, OR, NOT, скобки ().
    
    Примеры запросов:
    - "cat AND dog"
    - "cat OR dog"
    - "cat AND NOT dog"
    - "(cat AND dog) OR (mouse AND rat)"
    - "NOT cat"
    """
    if not os.path.exists(INVERTED_INDEX_FILE):
        return {"error": "Inverted index not found. Run build-inverted-index first."}
    
    results = search_engine.search(query)
    
    if not results:
        return {
            "query": query,
            "status": "not found",
            "results": []
        }
    
    return {
        "query": query,
        "found_in": len(results),
        "results": results
    }

@app.get("/api/crawler/index-stats")
def get_index_stats():
    """Возвращает статистику по инвертированному индексу"""
    if not os.path.exists(INVERTED_INDEX_FILE):
        return {"error": "Inverted index not found"}
    
    with open(INVERTED_INDEX_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    stats = {
        "total_terms": len(lines),
        "documents_count": len(search_engine.all_docs) if search_engine.all_docs else 0,
        "sample_terms": []
    }
    
    for i, line in enumerate(lines[:10]):
        term, docs = line.strip().split(':', 1)
        doc_count = len(docs.split(',')) if docs else 0
        stats["sample_terms"].append({
            "term": term,
            "documents_count": doc_count
        })
    
    return stats





@app.post("/api/crawler/calculate-tfidf")
def calculate_tfidf():
    """
    Рассчитывает TF-IDF для всех терминов и лемм во всех документах
    """
    if not os.path.exists(TOKENS_FOLDER) or not os.path.exists(LEMMAS_FOLDER):
        return {"error": "Tokens or lemmas folders not found. Run tokenization first."}
    
    if not os.path.exists(INVERTED_INDEX_FILE):
        return {"error": "Inverted index not found. Run build-inverted-index first."}
    
    calculator = TFIDFCalculator()
    doc_count = calculator.save_tfidf_for_all_documents()
    
    return {
        "status": "TF-IDF calculation completed",
        "documents_processed": doc_count,
        "terms_folder": "output/tfidf/",
        "lemmas_folder": "output/tfidf_lemmas/"
    }

@app.get("/api/crawler/document/{doc_id}/tfidf")
def get_document_tfidf(doc_id: int):
    """
    Возвращает TF-IDF для всех терминов в указанном документе
    """
    tfidf_file = os.path.join(TFIDF_FOLDER, f"{doc_id}_tfidf.txt")
    
    if not os.path.exists(tfidf_file):
        return {"error": f"TF-IDF file for document {doc_id} not found"}
    
    results = []
    with open(tfidf_file, 'r', encoding='utf-8') as f:
        for line in f:
            term, idf, tfidf = line.strip().split()
            results.append({
                "term": term,
                "idf": float(idf),
                "tfidf": float(tfidf)
            })
    
    return {
        "document_id": doc_id,
        "terms_count": len(results),
        "results": results
    }

@app.get("/api/crawler/document/{doc_id}/lemmas-tfidf")
def get_document_lemmas_tfidf(doc_id: int):
    """
    Возвращает TF-IDF для всех лемм в указанном документе
    """
    tfidf_file = os.path.join(TFIDF_LEMMAS_FOLDER, f"{doc_id}_lemmas_tfidf.txt")
    
    if not os.path.exists(tfidf_file):
        return {"error": f"TF-IDF lemmas file for document {doc_id} not found"}
    
    results = []
    with open(tfidf_file, 'r', encoding='utf-8') as f:
        for line in f:
            lemma, idf, tfidf = line.strip().split()
            results.append({
                "lemma": lemma,
                "idf": float(idf),
                "tfidf": float(tfidf)
            })
    
    return {
        "document_id": doc_id,
        "lemmas_count": len(results),
        "results": results
    }


@app.get("/api/crawler/search")
def search_word(word: str = Query(..., min_length=1), context_chars: int = 30, use_boolean: bool = False):
    """
    Поиск слова в документах.
    Если use_boolean=True, использует булев поиск по индексу.
    """
    if use_boolean and os.path.exists(INVERTED_INDEX_FILE):
        results = search_engine.search(word)
        if not results:
            return {"status": "not found", "query": word}
        
        return {
            "word": word,
            "found_in": results,
            "search_type": "boolean"
        }
    else:
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
        
        return {
            "word": word, 
            "found_in": results,
            "search_type": "linear"
        }
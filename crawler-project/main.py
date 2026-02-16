import os
import shutil
from fastapi import FastAPI
from parser_service import parse
from config import OUTPUT_FOLDER, INDEX_FILE, TOKENS_FILE, LEMMAS_FILE

import stanza
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

app = FastAPI()

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
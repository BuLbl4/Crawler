import os

OUTPUT_FOLDER = "output"
TOKENS_FOLDER = "tokens"
LEMMAS_FOLDER = "lemmas"
INDEX_FILE = os.path.join(OUTPUT_FOLDER, "index.txt")
INVERTED_INDEX_FILE = os.path.join(OUTPUT_FOLDER, "inverted_index.txt")
TFIDF_FOLDER = os.path.join(OUTPUT_FOLDER, "tfidf")
TFIDF_LEMMAS_FOLDER = os.path.join(OUTPUT_FOLDER, "tfidf_lemmas")
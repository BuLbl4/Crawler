import os
import math
import re
from collections import Counter
from typing import Dict, List, Set
from bs4 import BeautifulSoup
from config import OUTPUT_FOLDER


class VectorSearchEngine:
    def __init__(self):
        self.doc_vectors: Dict[int, Dict[str, float]] = {}   
        self.doc_norms: Dict[int, float] = {}               
        self.inverted_index: Dict[str, Set[int]] = {}     
        self.doc_count = 0

        self.load_data()


    def load_data(self):
        """Загружает TF-IDF векторы и инвертированный индекс"""

        if os.path.exists("output/inverted_index.txt"):
            with open("output/inverted_index.txt", 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        term, docs = line.strip().split(':', 1)
                        if docs:
                            self.inverted_index[term] = set(map(int, docs.split(',')))

        tfidf_folder = "output/tfidf"
        if os.path.exists(tfidf_folder):
            for filename in os.listdir(tfidf_folder):
                if filename.endswith("_tfidf.txt"):
                    try:
                        doc_id = int(filename.replace('_tfidf.txt', ''))
                        self.load_document_vector(doc_id)
                    except ValueError:
                        continue

        self.doc_count = len(self.doc_vectors)
        print(f"Загружено {self.doc_count} документов")
        print(f"Количество терминов: {len(self.inverted_index)}")

    def load_document_vector(self, doc_id: int):
        """Загружает вектор одного документа и сразу считает его норму"""

        filepath = f"output/tfidf/{doc_id}_tfidf.txt"
        if not os.path.exists(filepath):
            return

        vector = {}

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 3:
                    term, _, tfidf = parts
                    vector[term] = float(tfidf)

        if vector:
            self.doc_vectors[doc_id] = vector
            self.doc_norms[doc_id] = math.sqrt(sum(w * w for w in vector.values()))


    def preprocess_query(self, query: str) -> List[str]:
        """Токенизация и удаление стоп-слов"""
        words = re.findall(r'\b\w+\b', query.lower())

        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through",
            "before", "after", "between", "under", "over",
            "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did"
        }

        return [w for w in words if w not in stop_words and len(w) > 1]

    def create_query_vector(self, query_terms: List[str]) -> Dict[str, float]:
        """Создает TF-IDF вектор запроса"""
        if not query_terms:
            return {}

        term_counts = Counter(query_terms)
        max_count = max(term_counts.values())

        query_vector = {}

        for term, count in term_counts.items():
            if term in self.inverted_index:

                tf = count / max_count

                doc_freq = len(self.inverted_index[term])
                idf = math.log((self.doc_count + 1) / (doc_freq + 1)) + 1

                query_vector[term] = tf * idf

        return query_vector

    def cosine_similarity(self, query_vector: Dict[str, float], doc_id: int) -> float:
        """Косинусное сходство"""

        doc_vector = self.doc_vectors.get(doc_id)
        if not doc_vector:
            return 0.0

        dot_product = 0.0
        for term, q_weight in query_vector.items():
            dot_product += q_weight * doc_vector.get(term, 0.0)

        if dot_product == 0.0:
            return 0.0

        query_norm = math.sqrt(sum(w * w for w in query_vector.values()))
        doc_norm = self.doc_norms.get(doc_id)

        if not query_norm or not doc_norm:
            return 0.0

        similarity = dot_product / (query_norm * doc_norm)

        return min(similarity, 1.0)


    def get_snippet(self, doc_id: int, query_terms: List[str], context_chars: int = 150) -> str:
        """Получает сниппет вокруг первого найденного слова"""

        filepath = os.path.join(OUTPUT_FOLDER, f"{doc_id}.txt")
        if not os.path.exists(filepath):
            return ""

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")

            for tag in soup(["script", "style"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            text = ' '.join(text.split())

            if not query_terms:
                return text[:300] + "..." if len(text) > 300 else text

            text_lower = text.lower()
            best_pos = -1

            for term in query_terms:
                match = re.search(r'\b' + re.escape(term) + r'\b', text_lower)
                if match:
                    pos = match.start()
                    if best_pos == -1 or pos < best_pos:
                        best_pos = pos

            if best_pos != -1:
                start = max(0, best_pos - context_chars)
                end = min(len(text), best_pos + context_chars)
                prefix = "..." if start > 0 else ""
                suffix = "..." if end < len(text) else ""
                return f"{prefix}{text[start:end]}{suffix}"

            return text[:300] + "..." if len(text) > 300 else text

        except Exception as e:
            print(f"Snippet error: {e}")
            return ""


    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Оптимизированный векторный поиск"""

        if not self.doc_vectors:
            return []

        query_terms = self.preprocess_query(query)
        if not query_terms:
            return []

        query_vector = self.create_query_vector(query_terms)
        if not query_vector:
            return []

        candidate_docs = set()
        for term in query_vector:
            candidate_docs.update(self.inverted_index.get(term, set()))

        similarities = []

        for doc_id in candidate_docs:
            similarity = self.cosine_similarity(query_vector, doc_id)
            if similarity > 0:
                similarities.append((similarity, doc_id))

        similarities.sort(reverse=True)

        results = []

        for similarity, doc_id in similarities[:top_k]:
            results.append({
                "doc_id": doc_id,
                "relevance": round(similarity * 100, 2),  
                "filename": f"{doc_id}.txt",
                "snippet": self.get_snippet(doc_id, query_terms)
            })

        return results
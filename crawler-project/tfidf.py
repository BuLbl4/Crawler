import os
import math
from collections import Counter, defaultdict
from typing import Dict, List, Set
from config import OUTPUT_FOLDER, TOKENS_FOLDER, LEMMAS_FOLDER, INVERTED_INDEX_FILE
import re

class TFIDFCalculator:
    def __init__(self):
        self.inverted_index: Dict[str, Set[int]] = {}
        self.doc_count = 0
        self.load_inverted_index()
    
    def load_inverted_index(self):
        """Загружает инвертированный индекс"""
        if not os.path.exists(INVERTED_INDEX_FILE):
            return
        
        with open(INVERTED_INDEX_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                
                term, docs_str = line.split(':', 1)
                doc_ids = set(map(int, docs_str.split(','))) if docs_str else set()
                self.inverted_index[term] = doc_ids
                self.doc_count = max(self.doc_count, max(doc_ids) if doc_ids else 0)
        
        self.doc_count = len(set().union(*self.inverted_index.values())) if self.inverted_index else 0
    
    def calculate_tf_for_document(self, doc_id: int) -> Dict[str, float]:
        """
        Подсчитывает TF для каждого термина в документе
        TF = (количество вхождений термина) / (общее количество терминов в документе)
        """
        tokens_file = os.path.join(TOKENS_FOLDER, f"{doc_id}_tokens.txt")
        
        if not os.path.exists(tokens_file):
            return {}
        
        term_counts = Counter()
        total_terms = 0
        
        with open(tokens_file, 'r', encoding='utf-8') as f:
            for line in f:
                term = line.strip()
                if term:
                    term_counts[term] += 1
                    total_terms += 1
        
        tf_scores = {}
        for term, count in term_counts.items():
            tf_scores[term] = count / total_terms if total_terms > 0 else 0
        
        return tf_scores
    
    def calculate_tf_for_lemmas(self, doc_id: int) -> Dict[str, float]:
        """
        Подсчитывает TF для каждой леммы в документе
        TF = (сумма вхождений всех терминов леммы) / (общее количество терминов в документе)
        """
        lemmas_file = os.path.join(LEMMAS_FOLDER, f"{doc_id}_lemmas.txt")
        
        if not os.path.exists(lemmas_file):
            return {}
        
        term_tf = self.calculate_tf_for_document(doc_id)
        
        lemma_to_terms = {}
        with open(lemmas_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    lemma = parts[0]
                    terms = parts[1:] if len(parts) > 1 else []
                    lemma_to_terms[lemma] = terms
        
        lemma_tf = {}
        for lemma, terms in lemma_to_terms.items():
            total_tf = 0
            for term in terms:
                if term in term_tf:
                    total_tf += term_tf[term]
            lemma_tf[lemma] = total_tf
        
        return lemma_tf
    
    def calculate_idf(self, term: str) -> float:
        """
        Подсчитывает IDF для термина
        IDF = log(общее количество документов / количество документов с термином)
        """
        if self.doc_count == 0:
            return 0
        
        doc_frequency = len(self.inverted_index.get(term, set()))
        if doc_frequency == 0:
            return 0
        
        return math.log(self.doc_count / doc_frequency)
    
    def calculate_tfidf_for_document(self, doc_id: int) -> Dict[str, tuple]:
        """
        Подсчитывает TF-IDF для всех терминов документа
        Возвращает словарь {термин: (idf, tfidf)}
        """
        tf_scores = self.calculate_tf_for_document(doc_id)
        
        tfidf_scores = {}
        for term, tf in tf_scores.items():
            idf = self.calculate_idf(term)
            tfidf = tf * idf
            tfidf_scores[term] = (idf, tfidf)
        
        return tfidf_scores
    
    def calculate_tfidf_for_lemmas(self, doc_id: int) -> Dict[str, tuple]:
        """
        Подсчитывает TF-IDF для всех лемм документа
        IDF для леммы вычисляется как IDF для первого термина леммы (или минимальный/средний)
        Возвращает словарь {лемма: (idf, tfidf)}
        """
        lemma_tf = self.calculate_tf_for_lemmas(doc_id)
        
        lemmas_file = os.path.join(LEMMAS_FOLDER, f"{doc_id}_lemmas.txt")
        lemma_to_terms = {}
        
        with open(lemmas_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    lemma = parts[0]
                    terms = parts[1:] if len(parts) > 1 else []
                    lemma_to_terms[lemma] = terms
        
        tfidf_scores = {}
        for lemma, tf in lemma_tf.items():
            terms = lemma_to_terms.get(lemma, [])
            if terms:
                idf_sum = 0
                term_count = 0
                for term in terms:
                    idf = self.calculate_idf(term)
                    if idf > 0:
                        idf_sum += idf
                        term_count += 1
                
                idf = idf_sum / term_count if term_count > 0 else 0
            else:
                idf = 0
            
            tfidf = tf * idf
            tfidf_scores[lemma] = (idf, tfidf)
        
        return tfidf_scores
    
    def save_tfidf_for_all_documents(self):
        """
        Сохраняет TF-IDF для всех документов в отдельные файлы
        """
        if not os.path.exists(TOKENS_FOLDER):
            return
        
        tfidf_folder = os.path.join(OUTPUT_FOLDER, "tfidf")
        os.makedirs(tfidf_folder, exist_ok=True)
        
        tfidf_lemmas_folder = os.path.join(OUTPUT_FOLDER, "tfidf_lemmas")
        os.makedirs(tfidf_lemmas_folder, exist_ok=True)
        
        doc_ids = set()
        for filename in os.listdir(TOKENS_FOLDER):
            if filename.endswith("_tokens.txt"):
                try:
                    doc_id = int(filename.replace('_tokens.txt', ''))
                    doc_ids.add(doc_id)
                except:
                    continue
        
        for doc_id in sorted(doc_ids):
            tfidf_scores = self.calculate_tfidf_for_document(doc_id)
            output_file = os.path.join(tfidf_folder, f"{doc_id}_tfidf.txt")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for term, (idf, tfidf) in sorted(tfidf_scores.items()):
                    f.write(f"{term} {idf:.6f} {tfidf:.6f}\n")
            
            lemma_tfidf_scores = self.calculate_tfidf_for_lemmas(doc_id)
            output_lemmas_file = os.path.join(tfidf_lemmas_folder, f"{doc_id}_lemmas_tfidf.txt")
            
            with open(output_lemmas_file, 'w', encoding='utf-8') as f:
                for lemma, (idf, tfidf) in sorted(lemma_tfidf_scores.items()):
                    f.write(f"{lemma} {idf:.6f} {tfidf:.6f}\n")
        
        return len(doc_ids)
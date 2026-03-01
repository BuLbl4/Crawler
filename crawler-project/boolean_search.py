import os
import re
from typing import Set, Dict, List, Union, Tuple
from config import OUTPUT_FOLDER, INVERTED_INDEX_FILE, TOKENS_FOLDER

class BooleanSearchEngine:
    def __init__(self):
        self.inverted_index: Dict[str, Set[int]] = {}
        self.doc_ids: Dict[int, str] = {}  # id -> filename
        self.all_docs: Set[int] = set()
        self.load_index()
    
    def load_index(self):
        """Загружает инвертированный индекс из файла"""
        if not os.path.exists(INVERTED_INDEX_FILE):
            return
        
        with open(INVERTED_INDEX_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if ':' not in line:
                    continue
                    
                term, docs_str = line.split(':', 1)
                doc_ids = set(map(int, docs_str.split(','))) if docs_str else set()
                self.inverted_index[term] = doc_ids
                self.all_docs.update(doc_ids)
    
    def get_doc_id(self, filename: str) -> int:
        """Возвращает ID документа по имени файла"""
        try:
            return int(filename.replace('.txt', ''))
        except:
            return -1
    
    def get_filename(self, doc_id: int) -> str:
        """Возвращает имя файла по ID"""
        return f"{doc_id}.txt"
    
    def tokenize_query(self, query: str) -> List[str]:
        """Разбивает запрос на токены (термины и операторы)"""
        # Добавляем пробелы вокруг скобок для правильной токенизации
        query = query.replace('(', ' ( ').replace(')', ' ) ')
        tokens = query.split()
        return tokens
    
    def parse_expression(self, tokens: List[str], start: int = 0) -> tuple:
        """Парсит булево выражение и возвращает (результат, следующая_позиция)"""
        result = None
        current_op = None
        i = start
        
        while i < len(tokens):
            token = tokens[i].upper()
            
            if token == '(':
                sub_result, i = self.parse_expression(tokens, i + 1)
                
                if result is None:
                    result = sub_result
                elif current_op == 'AND':
                    result = result & sub_result
                elif current_op == 'OR':
                    result = result | sub_result
                
            elif token == ')':
                return result, i + 1
                
            elif token in ('AND', 'OR'):
                current_op = token
                i += 1
                
            elif token == 'NOT':
                next_token = tokens[i + 1] if i + 1 < len(tokens) else None
                if next_token and next_token != '(':
                    term = next_token.lower()
                    term_docs = self.inverted_index.get(term, set())
                    not_result = self.all_docs - term_docs
                    
                    if result is None:
                        result = not_result
                    elif current_op == 'AND':
                        result = result & not_result
                    elif current_op == 'OR':
                        result = result | not_result
                    
                    i += 2
                elif next_token == '(':
                    sub_result, i = self.parse_expression(tokens, i + 2)
                    not_result = self.all_docs - sub_result
                    
                    if result is None:
                        result = not_result
                    elif current_op == 'AND':
                        result = result & not_result
                    elif current_op == 'OR':
                        result = result | not_result
                else:
                    i += 1
                    
            else:
                term = token.lower()
                term_docs = self.inverted_index.get(term, set())
                
                if result is None:
                    result = term_docs
                elif current_op == 'AND':
                    result = result & term_docs
                elif current_op == 'OR':
                    result = result | term_docs
                
                i += 1
        
        return result if result is not None else set(), i
    
    def search(self, query: str) -> List[Dict]:
        """Выполняет булев поиск по запросу"""
        if not self.inverted_index:
            return []
        
        tokens = self.tokenize_query(query)
        
        try:
            result_docs, _ = self.parse_expression(tokens)
            
            results = []
            for doc_id in sorted(result_docs):
                filename = self.get_filename(doc_id)
                
                # Извлекаем ключевые слова из запроса (только те, что не являются операторами)
                keywords = self.extract_keywords(query)
                
                snippet = self.get_best_snippet(doc_id, keywords)
                
                results.append({
                    "file": filename,
                    "doc_id": doc_id,
                    "snippet": snippet,
                    "tokens_file": f"{doc_id}_tokens.txt",
                    "lemmas_file": f"{doc_id}_lemmas.txt"
                })
            
            return results
            
        except Exception as e:
            print(f"Error parsing query: {e}")
            return []
    
    def extract_keywords(self, query: str) -> List[str]:
        """
        Извлекает ключевые слова из запроса, исключая операторы.
        Операторы считаются только если они написаны ЗАГЛАВНЫМИ буквами.
        """
        # Убираем скобки
        query = re.sub(r'[()]', '', query)
        
        # Разбиваем на слова
        words = query.split()
        
        # Операторы только в верхнем регистре
        operators = {'AND', 'OR', 'NOT'}
        
        # Оставляем только те слова, которые НЕ являются операторами
        keywords = []
        for w in words:
            # Если слово в верхнем регистре и это оператор - пропускаем
            if w.upper() in operators and w.isupper():
                continue
            # Иначе добавляем как ключевое слово
            keywords.append(w.lower())
        
        return keywords
    
    def find_word_positions(self, text: str, word: str) -> List[int]:
        """
        Находит все позиции ЦЕЛОГО слова в тексте
        Использует регулярное выражение с границами слов \b
        """
        positions = []
        # Шаблон для поиска целого слова
        pattern = r'\b' + re.escape(word) + r'\b'
        for match in re.finditer(pattern, text.lower()):
            positions.append(match.start())
        return positions
    
    def get_best_snippet(self, doc_id: int, keywords: List[str], context_chars: int = 150) -> str:
        """
        Получает лучший сниппет из документа, находя фрагмент с наибольшей плотностью ключевых слов
        Ищет ТОЛЬКО целые слова
        """
        filepath = os.path.join(OUTPUT_FOLDER, f"{doc_id}.txt")
        
        if not os.path.exists(filepath):
            return ""
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Получаем чистый текст
            text = soup.get_text(separator=" ", strip=True)
            
            # Очищаем текст от лишних пробелов
            text = ' '.join(text.split())
            
            if not keywords:
                # Если нет ключевых слов, возвращаем начало текста
                return text[:300] + "..." if len(text) > 300 else text
            
            # Находим все вхождения ЦЕЛЫХ ключевых слов
            word_positions = []
            
            for keyword in keywords:
                if len(keyword) < 2:  # Игнорируем слишком короткие слова
                    continue
                
                # Ищем только целые слова
                positions = self.find_word_positions(text, keyword)
                for pos in positions:
                    word_positions.append((pos, keyword))
            
            if not word_positions:
                # Если ключевые слова не найдены как целые слова, возвращаем начало текста
                return text[:300] + "..." if len(text) > 300 else text
            
            # Сортируем позиции
            word_positions.sort()
            
            # Находим фрагмент с наибольшей плотностью ключевых слов
            best_snippet = ""
            best_score = -1
            
            # Проверяем окна вокруг каждого вхождения
            for i, (pos, keyword) in enumerate(word_positions):
                start = max(0, pos - context_chars)
                end = min(len(text), pos + context_chars)
                
                # Подсчитываем количество ЦЕЛЫХ ключевых слов в этом фрагменте
                snippet_text = text[start:end]
                
                score = 0
                for kw in keywords:
                    if len(kw) >= 2:
                        # Считаем только целые слова
                        pattern = r'\b' + re.escape(kw) + r'\b'
                        score += len(re.findall(pattern, snippet_text.lower()))
                
                # Учитываем близость к началу документа
                position_bonus = 1 + 0.1 * (1 - start / len(text))
                score = score * position_bonus
                
                if score > best_score:
                    best_score = score
                    
                    # Добавляем многоточия, если фрагмент не с начала или не до конца
                    prefix = "..." if start > 0 else ""
                    suffix = "..." if end < len(text) else ""
                    
                    best_snippet = f"{prefix}{snippet_text}{suffix}"
            
            return best_snippet if best_snippet else text[:300] + "..."
            
        except Exception as e:
            print(f"Error getting snippet: {e}")
            return ""
    
    def get_snippet(self, doc_id: int, query: str, context_chars: int = 150) -> str:
        """
        Старая функция для обратной совместимости
        """
        keywords = self.extract_keywords(query)
        return self.get_best_snippet(doc_id, keywords, context_chars)
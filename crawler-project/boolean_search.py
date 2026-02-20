import os
import re
from typing import Set, Dict, List, Union
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
                
                # Формат: термин: doc_id1,doc_id2,doc_id3
                if ':' not in line:
                    continue
                    
                term, docs_str = line.split(':', 1)
                doc_ids = set(map(int, docs_str.split(','))) if docs_str else set()
                self.inverted_index[term] = doc_ids
                self.all_docs.update(doc_ids)
    
    def get_doc_id(self, filename: str) -> int:
        """Возвращает ID документа по имени файла"""
        # Извлекаем номер из имени файла (например, "0.txt" -> 0)
        try:
            return int(filename.replace('.txt', ''))
        except:
            return -1
    
    def get_filename(self, doc_id: int) -> str:
        """Возвращает имя файла по ID"""
        return f"{doc_id}.txt"
    
    def tokenize_query(self, query: str) -> List[str]:
        """Разбивает запрос на токены (термины и операторы)"""
        # Добавляем пробелы вокруг скобок для правильного разбиения
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
                # Рекурсивно парсим выражение в скобках
                sub_result, i = self.parse_expression(tokens, i + 1)
                
                if result is None:
                    result = sub_result
                elif current_op == 'AND':
                    result = result & sub_result
                elif current_op == 'OR':
                    result = result | sub_result
                # NOT обрабатывается как унарный оператор
                
            elif token == ')':
                # Конец текущего выражения
                return result, i + 1
                
            elif token in ('AND', 'OR'):
                current_op = token
                i += 1
                
            elif token == 'NOT':
                # Унарный оператор NOT
                next_token = tokens[i + 1] if i + 1 < len(tokens) else None
                if next_token and next_token != '(':
                    # NOT для одиночного термина
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
                    # NOT для выражения в скобках
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
                # Обычный термин
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
        
        # Токенизируем запрос
        tokens = self.tokenize_query(query)
        
        try:
            # Парсим выражение
            result_docs, _ = self.parse_expression(tokens)
            
            # Преобразуем в список результатов
            results = []
            for doc_id in sorted(result_docs):
                filename = self.get_filename(doc_id)
                
                # Получаем сниппет для первого вхождения термина
                snippet = self.get_snippet(doc_id, query)
                
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
    
    def get_snippet(self, doc_id: int, query: str, context_chars: int = 150) -> str:
        """Получает сниппет из документа для запроса"""
        filepath = os.path.join(OUTPUT_FOLDER, f"{doc_id}.txt")
        
        if not os.path.exists(filepath):
            return ""
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # Извлекаем текст из HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Получаем текст
            text = soup.get_text(separator=" ", strip=True)
            
            # Очищаем текст от лишних пробелов
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Ищем первое вхождение любого термина из запроса
            words = re.findall(r'\b\w{3,}\b', query.lower())  # только слова длиннее 2 символов
            
            for word in words:
                text_lower = text.lower()
                idx = text_lower.find(word)
                if idx != -1:
                    start = max(0, idx - context_chars)
                    end = min(len(text), idx + len(word) + context_chars)
                    
                    # Добавляем ... если обрезали
                    prefix = "..." if start > 0 else ""
                    suffix = "..." if end < len(text) else ""
                    
                    return f"{prefix}{text[start:end]}{suffix}"
            
            # Если ни одно слово не найдено, возвращаем начало текста
            return text[:300] + "..." if len(text) > 300 else text
            
        except Exception as e:
            print(f"Error getting snippet: {e}")
            return ""
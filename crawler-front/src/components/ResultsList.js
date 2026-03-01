import React from 'react';

const ResultsList = ({ results, loading }) => {
  if (!results || loading) return null;

  const { query, total_results, results: items, search_type } = results;

  // Функция для подсветки только ключевых слов (не операторов)
  const highlightQuery = (text) => {
    if (!text || !query) return text;
    
    let searchWords = [];
    
    if (search_type === 'boolean') {
      // Для булева поиска - извлекаем только слова, не являющиеся операторами
      // Операторы: AND, OR, NOT, а также скобки () не учитываем
      const operators = ['AND', 'OR', 'NOT'];
      
      // Убираем скобки и разбиваем на слова
      const words = query
        .replace(/[()]/g, '')  // убираем скобки
        .split(' ')
        .filter(w => w.trim() !== '');  // убираем пустые
      
      // Оставляем только те слова, которые НЕ являются операторами
      searchWords = words.filter(w => !operators.includes(w.toUpperCase()));
    } else {
      // Для векторного поиска - все слова
      searchWords = query.toLowerCase().split(' ').filter(w => w.length > 2);
    }
    
    let highlightedText = text;
    
    // Подсвечиваем каждое найденное слово
    searchWords.forEach(word => {
      if (word && word.length > 2) {
        // Используем границы слов для точной подсветки
        const regex = new RegExp(`\\b${word}\\b`, 'gi');
        highlightedText = highlightedText.replace(regex, '<mark>$&</mark>');
      }
    });
    
    return highlightedText;
  };

  if (!items || items.length === 0) {
    return (
      <div className="alert alert-warning mt-4">
        По вашему запросу ничего не найдено
      </div>
    );
  }

  return (
    <div className="mt-4">
      {/* Статистика поиска */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h5 className="mb-0">
            Результаты поиска: <span className="badge bg-primary">{total_results}</span>
          </h5>
          {search_type === 'boolean' && (
            <small className="text-muted">
              Запрос: <code>{query}</code>
            </small>
          )}
        </div>
        <span className="text-muted">
          Показано топ-{Math.min(items.length, 10)} из {total_results}
        </span>
      </div>

      {/* Список результатов */}
      <div className="results-list">
        {items.slice(0, 10).map((result, index) => (
          <div key={result.doc_id || index} className="card result-card">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-start mb-2">
                <div className="d-flex align-items-center">
                  <span className="rank-badge me-2">{index + 1}</span>
                  <h6 className="mb-0">
                    Документ #{result.doc_id || result.filename?.replace('.txt', '') || '?'}
                  </h6>
                </div>
                {result.relevance && (
                  <span className="relevance-badge">
                    Релевантность: {(result.relevance).toFixed(1)}%
                  </span>
                )}
              </div>

              {/* Сниппет с подсветкой только ключевых слов */}
              {result.snippet && (
                <div 
                  className="snippet mt-2"
                  dangerouslySetInnerHTML={{
                    __html: highlightQuery(result.snippet)
                  }}
                />
              )}

              {/* Мета-информация */}
              <div className="mt-2 text-muted small">
                {result.filename && (
                  <span className="me-3">📄 {result.filename}</span>
                )}
                {result.top_terms && result.top_terms.length > 0 && (
                  <span>
                    🔑 Термины:{' '}
                    {result.top_terms.slice(0, 3).map((term, i) => (
                      <span key={i} className="badge bg-light text-dark me-1">
                        {term.term} ({(term.contribution * 100).toFixed(0)}%)
                      </span>
                    ))}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultsList;
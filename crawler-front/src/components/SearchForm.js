import React, { useState } from 'react';

const SearchForm = ({ onSearch, loading }) => {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('vector');
  const [useLemmas, setUseLemmas] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    let processedQuery = query;
    

    if (searchType === 'boolean') {
      processedQuery = query
        .replace(/\bAND\b/gi, 'AND')
        .replace(/\bOR\b/gi, 'OR')
        .replace(/\bNOT\b/gi, 'NOT');
    }
    
    onSearch(processedQuery, searchType, useLemmas);
  };

  return (
    <div className="card shadow-sm">
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label htmlFor="query" className="form-label fw-bold">
              Поисковый запрос
            </label>
            <div className="input-group">
              <input
                type="text"
                className="form-control form-control-lg"
                id="query"
                placeholder={searchType === 'boolean' 
                  ? "Введите запрос с операторами AND, OR, NOT (например: cat AND dog)" 
                  : "Введите слова для поиска..."}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
              />
              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={loading || !query.trim()}
              >
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" />
                    Поиск...
                  </>
                ) : (
                  'Найти'
                )}
              </button>
            </div>
            {searchType === 'boolean' && (
              <div className="mt-2">
                <small className="text-muted d-block">
                  Операторы: <strong>AND</strong>, <strong>OR</strong>, <strong>NOT</strong>, ()
                </small>
              </div>
            )}
          </div>

          <div className="row">
            <div className="col-md-6">
              <label className="form-label fw-bold">Тип поиска</label>
              <div className="btn-group w-100">
                <button
                  type="button"
                  className={`btn ${searchType === 'vector' ? 'btn-primary' : 'btn-outline-primary'}`}
                  onClick={() => setSearchType('vector')}
                >
                  Векторный
                </button>
                <button
                  type="button"
                  className={`btn ${searchType === 'boolean' ? 'btn-primary' : 'btn-outline-primary'}`}
                  onClick={() => setSearchType('boolean')}
                >
                  Булев
                </button>
              </div>
            </div>

            {searchType === 'vector' && (
              <div className="col-md-6">
                <label className="form-label fw-bold">Опции</label>
                <div className="form-check form-switch mt-2">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="useLemmas"
                    checked={useLemmas}
                    onChange={(e) => setUseLemmas(e.target.checked)}
                  />
                  <label className="form-check-label" htmlFor="useLemmas">
                    Использовать леммы (основы слов)
                  </label>
                </div>
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default SearchForm;
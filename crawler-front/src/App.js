import React, { useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import { searchApi } from './api/searchApi';
import SearchForm from './components/SearchForm';
import ResultsList from './components/ResultsList';
import StatsPanel from './components/StatsPanel';

function App() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState('search');

  const handleSearch = async (query, searchType, useLemmas) => {
    if (!query.trim()) {
      setError('Введите поисковый запрос');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      let response;
      
      if (searchType === 'boolean') {
        response = await searchApi.booleanSearch(query);
        // Преобразуем ответ булева поиска в единый формат
        response = {
          query: response.query,
          total_results: response.found_in || 0,
          results: (response.results || []).map(r => ({
            doc_id: r.doc_id,
            relevance: null,
            snippet: r.snippet,
            filename: r.file
          }))
        };
      } else {
        response = await searchApi.vectorSearch(query, 10, useLemmas);
      }
      
      setResults(response);
    } catch (err) {
      console.error('Search error:', err);
      setError(err.response?.data?.error || 'Ошибка при выполнении поиска');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const statsData = await searchApi.getIndexStats();
      setStats(statsData);
      setActiveTab('stats');
    } catch (err) {
      console.error('Stats error:', err);
      setError('Ошибка при загрузке статистики');
    }
  };

  return (
    <div className="App">
      <nav className="navbar navbar-dark bg-primary">
        <div className="container">
          <div className="navbar-nav">
            <button 
              className={`btn btn-sm ${activeTab === 'search' ? 'btn-light' : 'btn-outline-light'} me-2`}
              onClick={() => setActiveTab('search')}
            >
              Поиск
            </button>
            <button 
              className={`btn btn-sm ${activeTab === 'stats' ? 'btn-light' : 'btn-outline-light'}`}
              onClick={loadStats}
            >
              Статистика
            </button>
          </div>
        </div>
      </nav>

      <div className="container mt-4">
        {activeTab === 'search' ? (
          <>
            {/* Форма поиска */}
            <SearchForm onSearch={handleSearch} loading={loading} />

            {/* Ошибка */}
            {error && (
              <div className="alert alert-danger mt-3" role="alert">
                {error}
              </div>
            )}

            {/* Результаты */}
            {results && (
              <ResultsList 
                results={results} 
                loading={loading}
              />
            )}
          </>
        ) : (
          <StatsPanel stats={stats} />
        )}
      </div>

    
    </div>
  );
}

export default App;
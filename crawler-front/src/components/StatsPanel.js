import React from 'react';

const StatsPanel = ({ stats }) => {
  if (!stats) {
    return (
      <div className="text-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </div>
      </div>
    );
  }

  if (stats.error) {
    return (
      <div className="alert alert-danger">
        {stats.error}
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-4">Статистика индекса</h3>

      <div className="row">
        <div className="col-md-4 mb-3">
          <div className="stats-card">
            <h5>Всего терминов</h5>
            <div className="stats-number">{stats.total_terms || 0}</div>
            <small>уникальных слов в индексе</small>
          </div>
        </div>

        <div className="col-md-4 mb-3">
          <div className="stats-card" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
            <h5>Документов</h5>
            <div className="stats-number">{stats.documents_count || 0}</div>
            <small>проиндексировано</small>
          </div>
        </div>

        <div className="col-md-4 mb-3">
          <div className="stats-card" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
            <h5>Средняя частота</h5>
            <div className="stats-number">
              {stats.total_terms && stats.documents_count 
                ? (stats.total_terms / stats.documents_count).toFixed(1) 
                : 0}
            </div>
            <small>терминов на документ</small>
          </div>
        </div>
      </div>


      {/* Инструкция */}
      <div className="alert alert-info mt-4">
        <h6>ℹ️ Как использовать:</h6>
        <ul className="mb-0">
          <li><strong>Векторный поиск</strong> - для естественных запросов (например, "love story")</li>
          <li><strong>Булев поиск</strong> - для точных запросов с операторами (например, "love AND friendship")</li>
          <li><strong>Леммы</strong> - учитывает разные формы слов (love, loved, loving → love)</li>
        </ul>
      </div>
    </div>
  );
};

export default StatsPanel;
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchApi = {
  // Векторный поиск
  vectorSearch: async (query, topK = 10, useLemmas = false) => {
    try {
      const response = await api.post('/api/search/vector', null, {
        params: { 
          query, 
          top_k: topK, 
          use_lemmas: useLemmas,
          threshold: 0.0
        }
      });
      return response.data;
    } catch (error) {
      console.error('Vector search error:', error);
      throw error;
    }
  },

  // Булев поиск
  booleanSearch: async (query) => {
    try {
      const response = await api.post('/api/crawler/boolean-search', null, {
        params: { query }
      });
      return response.data;
    } catch (error) {
      console.error('Boolean search error:', error);
      throw error;
    }
  },

  // Детальный векторный поиск
  detailedVectorSearch: async (query, topK = 10, useLemmas = false) => {
    try {
      const response = await api.post('/api/search/vector-detailed', null, {
        params: { query, top_k: topK, use_lemmas: useLemmas }
      });
      return response.data;
    } catch (error) {
      console.error('Detailed search error:', error);
      throw error;
    }
  },

  // Статистика индекса
  getIndexStats: async () => {
    try {
      const response = await api.get('/api/crawler/index-stats');
      return response.data;
    } catch (error) {
      console.error('Get stats error:', error);
      throw error;
    }
  },

  // Получить TF-IDF документа
  getDocumentTfidf: async (docId) => {
    try {
      const response = await api.get(`/api/crawler/document/${docId}/tfidf`);
      return response.data;
    } catch (error) {
      console.error('Get document tfidf error:', error);
      throw error;
    }
  },

};
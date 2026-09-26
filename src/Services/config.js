const API_KEY = import.meta.env.VITE_INDIAN_API_KEY;

const BASE_URL = "https://dev.indianapi.in";

async function request(endpoint) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: {
      "X-API-Key": API_KEY,
    },
  });

  if (!res.ok) {
    throw new Error("API Error");
  }

  return res.json();
}

export const MarketAPI = {

  getIndices() {
    return request("/indices");
  },

  getTrending() {
    return request("/trending");
  },

  getNews() {
    return request("/news");
  },

  getIPO() {
    return request("/ipo");
  },

  getCommodities() {
    return request("/commodities");
  },

};
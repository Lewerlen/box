import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token');
    }
    return Promise.reject(error);
  }
);

export default api;

interface ParticipantFilters {
  page?: number;
  search?: string;
  gender?: string;
  age_category_id?: number | string;
  weight_category_id?: number | string;
  class_id?: number | string;
  club_id?: number | string;
  region_id?: number | string;
  competition_id?: number | string;
}

interface RegistrationData {
  fio: string;
  gender: string;
  dob: string;
  age_category_id: number;
  weight_category_id: number;
  class_name: string;
  rank_name: string | null;
  rank_assigned_on: string | null;
  order_number: string | null;
  region_name: string;
  city_name: string;
  club_name: string;
  coach_name: string;
  competition_id?: number | null;
}

interface BracketParams {
  class_name: string;
  gender: string;
  age_category_name: string;
  weight_name: string;
  competition_id?: number;
}

interface SwapParams extends BracketParams {
  index_a: number;
  index_b: number;
}

interface ParticipantUpdateData {
  fio?: string;
  gender?: string;
  dob?: string;
  age_category_id?: number;
  weight_category_id?: number;
  class_name?: string;
  rank_name?: string;
  region_name?: string;
  city_name?: string;
  club_name?: string;
  coach_name?: string;
}

export const publicApi = {
  getStats: () => api.get('/public/stats'),
  getParticipants: (params: ParticipantFilters) => api.get('/public/participants', { params }),
  getParticipant: (id: number) => api.get(`/public/participants/${id}`),
  getAgeCategories: () => api.get('/public/references/age-categories'),
  getWeightCategories: (ageCategoryId: number) => api.get('/public/references/weight-categories', { params: { age_category_id: ageCategoryId } }),
  getClasses: () => api.get('/public/references/classes'),
  getRanks: () => api.get('/public/references/ranks'),
  getRegions: () => api.get('/public/references/regions'),
  getCities: (regionId: number) => api.get('/public/references/cities', { params: { region_id: regionId } }),
  getClubs: (cityId?: number) => api.get('/public/references/clubs', { params: cityId ? { city_id: cityId } : {} }),
  getCoaches: (clubId: number) => api.get('/public/references/coaches', { params: { club_id: clubId } }),
  getApprovedBrackets: (competition_id?: number) => api.get('/public/brackets/approved', { params: competition_id !== undefined ? { competition_id } : {} }),
  getBracketImage: (params: { class_name: string; gender: string; age_category_name: string; weight_name: string; competition_id?: number }) => {
    const p: Record<string, string> = {
      class_name: params.class_name,
      gender: params.gender,
      age_category_name: params.age_category_name,
      weight_name: params.weight_name,
    };
    if (params.competition_id !== undefined) p.competition_id = String(params.competition_id);
    return `/api/public/brackets/image?${new URLSearchParams(p)}`;
  },
};

export const registrationApi = {
  getAgeCategoriesForGender: (gender: string) => api.get('/registration/age-categories', { params: { gender } }),
  determineAgeCategory: (dob: string, gender: string) => api.get('/registration/determine-age-category', { params: { dob, gender } }),
  getWeightCategories: (ageCategoryId: number) => api.get('/registration/weight-categories', { params: { age_category_id: ageCategoryId } }),
  getClasses: () => api.get('/registration/classes'),
  getRanks: () => api.get('/registration/ranks'),
  getRegions: () => api.get('/registration/regions'),
  getCities: (regionId: number) => api.get('/registration/cities', { params: { region_id: regionId } }),
  getClubs: (cityId: number) => api.get('/registration/clubs', { params: { city_id: cityId } }),
  getCoaches: (clubId: number) => api.get('/registration/coaches', { params: { club_id: clubId } }),
  submit: (data: RegistrationData) => api.post('/registration/submit', data),
};

export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  getMe: () => api.get('/auth/me'),
};

export const competitionsApi = {
  getAll: () => api.get('/competitions'),
  getById: (id: number) => api.get(`/competitions/${id}`),
  create: (data: {
    name: string;
    discipline: string;
    date_start?: string;
    date_end?: string;
    location?: string;
    status: string;
  }) => api.post('/admin/competitions', data),
  update: (id: number, data: {
    name?: string;
    discipline?: string;
    date_start?: string;
    date_end?: string;
    location?: string;
    status?: string;
  }) => api.put(`/admin/competitions/${id}`, data),
  delete: (id: number) => api.delete(`/admin/competitions/${id}`),
};

export const adminApi = {
  getParticipants: (params: ParticipantFilters) => api.get('/admin/participants', { params }),
  getParticipant: (id: number) => api.get(`/admin/participants/${id}`),
  createParticipant: (data: RegistrationData) => api.post('/admin/participants', data),
  updateParticipant: (id: number, data: ParticipantUpdateData) => api.put(`/admin/participants/${id}`, data),
  deleteParticipant: (id: number) => api.delete(`/admin/participants/${id}`),
  importCsv: (file: File, competition_id?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    const params = competition_id !== undefined ? { competition_id } : {};
    return api.post('/admin/import-csv', formData, { params });
  },
  getBracketCategories: (competition_id?: number) => api.get('/admin/brackets/categories', { params: competition_id !== undefined ? { competition_id } : {} }),
  getBracketDetail: (params: BracketParams) => api.get('/admin/brackets/detail', { params }),
  swapParticipants: (params: SwapParams) => api.post('/admin/brackets/swap', null, { params }),
  toggleApproval: (params: BracketParams) => api.post('/admin/brackets/approve', null, { params }),
  regenerateBracket: (params: BracketParams) => api.post('/admin/brackets/regenerate', null, { params }),
  downloadExcel: (type: 'preliminary' | 'weigh-in' | 'brackets' | 'protocol', competition_id?: number) => {
    const params: Record<string, string | number> = {}
    if (competition_id !== undefined) params.competition_id = competition_id
    return api.get(`/admin/excel/${type}`, { responseType: 'blob', params }).then((res) => {
      const blob = new Blob([res.data])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${type}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    })
  },
  downloadBracketPng: (params: BracketParams) => {
    return api.get('/admin/brackets/image', { params, responseType: 'blob' }).then((res) => {
      const blob = new Blob([res.data])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bracket_${params.class_name}_${params.gender}_${params.age_category_name}_${params.weight_name}.png`
      a.click()
      URL.revokeObjectURL(url)
    })
  },
  fetchBracketImageBlob: (params: BracketParams) => {
    return api.get('/admin/brackets/image', { params, responseType: 'blob' }).then((res) => {
      return URL.createObjectURL(new Blob([res.data]))
    })
  },
  getRefRegions: () => api.get('/admin/references/regions'),
  getRefCities: (regionId: number) => api.get('/admin/references/cities', { params: { region_id: regionId } }),
  getRefClubs: (cityId: number) => api.get('/admin/references/clubs', { params: { city_id: cityId } }),
  getRefCoaches: (clubId: number) => api.get('/admin/references/coaches', { params: { club_id: clubId } }),
  createRef: (type: string, name: string, parentId?: number) => api.post(`/admin/references/${type}`, { name, parent_id: parentId }),
  renameRef: (type: string, id: number, name: string) => api.put(`/admin/references/${type}/${id}`, { name }),
  deleteRef: (type: string, id: number) => api.delete(`/admin/references/${type}/${id}`),
  mergeRef: (type: string, id: number, targetId: number) => api.post(`/admin/references/${type}/${id}/merge`, { target_id: targetId }),
};

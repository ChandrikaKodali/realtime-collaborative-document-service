import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export const getDocuments = async () => {
  const response = await API.get("/api/documents");
  return response.data;
};

export const createDocument = async (document) => {
  const response = await API.post("/api/documents", document);
  return response.data;
};

export const updateDocument = async (id, document) => {
  const response = await API.put(`/api/documents/${id}`, document);
  return response.data;
};

export const deleteDocument = async (id) => {
  const response = await API.delete(`/api/documents/${id}`);
  return response.data;
};
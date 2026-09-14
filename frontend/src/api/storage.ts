import { apiRequest, downloadFile as downloadFileBlob } from "./client";

export interface FolderItem {
  id: number;
  parent_folder_id: number | null;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface FileItem {
  id: number;
  folder_id: number | null;
  name: string;
  size: number;
  mime_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface StorageUsage {
  quota_bytes: number;
  used_bytes: number;
  available_bytes: number;
}

export function listFolders(
  token: string,
  parentFolderId: number | null
): Promise<FolderItem[]> {
  const query = parentFolderId !== null ? `?parent_folder_id=${parentFolderId}` : "";
  return apiRequest<FolderItem[]>(`/folders${query}`, { method: "GET" }, token);
}

export function createFolder(
  token: string,
  name: string,
  parentFolderId: number | null
): Promise<FolderItem> {
  return apiRequest<FolderItem>(
    "/folders",
    {
      method: "POST",
      body: JSON.stringify({ name, parent_folder_id: parentFolderId }),
    },
    token
  );
}

export function renameFolder(token: string, folderId: number, name: string): Promise<FolderItem> {
  return apiRequest<FolderItem>(
    `/folders/${folderId}`,
    { method: "PATCH", body: JSON.stringify({ name }) },
    token
  );
}

export function deleteFolder(token: string, folderId: number): Promise<void> {
  return apiRequest<void>(`/folders/${folderId}`, { method: "DELETE" }, token);
}

export function listFiles(token: string, folderId: number | null): Promise<FileItem[]> {
  const query = folderId !== null ? `?folder_id=${folderId}` : "";
  return apiRequest<FileItem[]>(`/files${query}`, { method: "GET" }, token);
}

export function uploadFile(
  token: string,
  file: File,
  folderId: number | null
): Promise<FileItem> {
  const formData = new FormData();
  formData.append("upload", file);
  const query = folderId !== null ? `?folder_id=${folderId}` : "";
  return apiRequest<FileItem>(
    `/files/upload${query}`,
    { method: "POST", body: formData },
    token
  );
}

export function renameFile(token: string, fileId: number, name: string): Promise<FileItem> {
  return apiRequest<FileItem>(
    `/files/${fileId}`,
    { method: "PATCH", body: JSON.stringify({ name }) },
    token
  );
}

export function deleteFile(token: string, fileId: number): Promise<void> {
  return apiRequest<void>(`/files/${fileId}`, { method: "DELETE" }, token);
}

export function downloadFile(token: string, file: FileItem): Promise<void> {
  return downloadFileBlob(`/files/${file.id}/download`, token, file.name);
}

export function getStorageUsage(token: string): Promise<StorageUsage> {
  return apiRequest<StorageUsage>("/storage/usage", { method: "GET" }, token);
}

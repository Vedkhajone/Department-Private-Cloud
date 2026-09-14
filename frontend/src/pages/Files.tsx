import { useCallback, useEffect, useState, type ChangeEvent } from "react";

import { ApiError } from "../api/client";
import {
  createFolder,
  deleteFile,
  deleteFolder,
  downloadFile,
  getStorageUsage,
  listFiles,
  listFolders,
  renameFile,
  renameFolder,
  uploadFile,
  type FileItem,
  type FolderItem,
  type StorageUsage,
} from "../api/storage";
import { useAuth } from "../context/AuthContext";

interface Crumb {
  id: number | null;
  name: string;
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exponent);
  return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

/**
 * A minimal "My Files" manager: folder navigation via a breadcrumb
 * trail, file/folder listing, upload, new folder, rename, delete,
 * download, and a storage usage indicator. Kept simple and functional
 * rather than visually elaborate, per the Phase 3 brief.
 */
export function Files() {
  const { token } = useAuth();
  const [path, setPath] = useState<Crumb[]>([{ id: null, name: "My Files" }]);
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [usage, setUsage] = useState<StorageUsage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentFolderId = path[path.length - 1].id;

  const refresh = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const [folderList, fileList, usageData] = await Promise.all([
        listFolders(token, currentFolderId),
        listFiles(token, currentFolderId),
        getStorageUsage(token),
      ]);
      setFolders(folderList);
      setFiles(fileList);
      setUsage(usageData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load files");
    } finally {
      setIsLoading(false);
    }
  }, [token, currentFolderId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function openFolder(folder: FolderItem) {
    setPath((prev) => [...prev, { id: folder.id, name: folder.name }]);
  }

  function goToCrumb(index: number) {
    setPath((prev) => prev.slice(0, index + 1));
  }

  async function withErrorHandling(action: () => Promise<unknown>, fallback: string) {
    if (!token) return;
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fallback);
    }
  }

  function handleNewFolder() {
    const name = window.prompt("Folder name");
    if (!name) return;
    void withErrorHandling(
      () => createFolder(token!, name, currentFolderId),
      "Failed to create folder"
    );
  }

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    if (!token || !e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    e.target.value = ""; // allow re-selecting the same file afterwards
    setIsUploading(true);
    setError(null);
    try {
      await uploadFile(token, file, currentFolderId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  function handleRenameFolder(folder: FolderItem) {
    const name = window.prompt("Rename folder", folder.name);
    if (!name || name === folder.name) return;
    void withErrorHandling(() => renameFolder(token!, folder.id, name), "Rename failed");
  }

  function handleDeleteFolder(folder: FolderItem) {
    if (!window.confirm(`Delete folder "${folder.name}"?`)) return;
    void withErrorHandling(() => deleteFolder(token!, folder.id), "Delete failed");
  }

  function handleRenameFile(file: FileItem) {
    const name = window.prompt("Rename file", file.name);
    if (!name || name === file.name) return;
    void withErrorHandling(() => renameFile(token!, file.id, name), "Rename failed");
  }

  function handleDeleteFile(file: FileItem) {
    if (!window.confirm(`Delete "${file.name}"?`)) return;
    void withErrorHandling(() => deleteFile(token!, file.id), "Delete failed");
  }

  async function handleDownload(file: FileItem) {
    if (!token) return;
    try {
      await downloadFile(token, file);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Download failed");
    }
  }

  const usagePercent = usage ? Math.min(100, (usage.used_bytes / usage.quota_bytes) * 100) : 0;

  return (
    <div className="files-card">
      <div className="files-header">
        <h2>My Files</h2>
        {usage && (
          <div className="usage-bar-wrap">
            <div className="usage-bar">
              <div className="usage-bar-fill" style={{ width: `${usagePercent}%` }} />
            </div>
            <span className="usage-text">
              {formatBytes(usage.used_bytes)} of {formatBytes(usage.quota_bytes)} used
            </span>
          </div>
        )}
      </div>

      <div className="breadcrumbs">
        {path.map((crumb, index) => (
          <span key={crumb.id ?? "root"}>
            {index > 0 && <span className="crumb-sep"> / </span>}
            <button
              type="button"
              className="link-button"
              onClick={() => goToCrumb(index)}
              disabled={index === path.length - 1}
            >
              {crumb.name}
            </button>
          </span>
        ))}
      </div>

      <div className="files-toolbar">
        <button type="button" onClick={handleNewFolder}>
          New Folder
        </button>
        <label className="upload-button">
          {isUploading ? "Uploading..." : "Upload"}
          <input type="file" onChange={handleUpload} disabled={isUploading} hidden />
        </label>
      </div>

      {error && <p className="form-error">{error}</p>}

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <ul className="file-list">
          {folders.map((folder) => (
            <li key={`folder-${folder.id}`} className="file-row">
              <button
                type="button"
                className="link-button file-name"
                onClick={() => openFolder(folder)}
              >
                📁 {folder.name}
              </button>
              <span className="file-actions">
                <button type="button" onClick={() => handleRenameFolder(folder)}>
                  Rename
                </button>
                <button type="button" onClick={() => handleDeleteFolder(folder)}>
                  Delete
                </button>
              </span>
            </li>
          ))}

          {files.map((file) => (
            <li key={`file-${file.id}`} className="file-row">
              <span className="file-name">
                📄 {file.name} <span className="file-size">({formatBytes(file.size)})</span>
              </span>
              <span className="file-actions">
                <button type="button" onClick={() => handleDownload(file)}>
                  Download
                </button>
                <button type="button" onClick={() => handleRenameFile(file)}>
                  Rename
                </button>
                <button type="button" onClick={() => handleDeleteFile(file)}>
                  Delete
                </button>
              </span>
            </li>
          ))}

          {folders.length === 0 && files.length === 0 && (
            <li className="file-row empty-row">This folder is empty.</li>
          )}
        </ul>
      )}
    </div>
  );
}

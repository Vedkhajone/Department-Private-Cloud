import { useCallback, useEffect, useState, type ChangeEvent } from "react";
import { Folder, FolderPlus, Upload as UploadIcon } from "lucide-react";

import { ApiError } from "../api/client";
import {
  createFolder,
  deleteFile,
  deleteFolder,
  downloadFile,
  listFiles,
  listFolders,
  renameFile,
  renameFolder,
  uploadFile,
  type FileItem,
  type FolderItem,
} from "../api/storage";
import { EmptyState } from "../components/EmptyState";
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
 * "My Files": folder navigation via a breadcrumb trail, file/folder
 * listing, upload, new folder, rename, delete, download. Storage
 * usage lives in its own card on the dashboard (components/StorageCard)
 * -- this section only manages the file tree itself.
 */
export function Files() {
  const { token } = useAuth();
  const [path, setPath] = useState<Crumb[]>([{ id: null, name: "My Files" }]);
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentFolderId = path[path.length - 1].id;
  const atRoot = path.length === 1;

  const refresh = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const [folderList, fileList] = await Promise.all([
        listFolders(token, currentFolderId),
        listFiles(token, currentFolderId),
      ]);
      setFolders(folderList);
      setFiles(fileList);
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

  const isEmpty = folders.length === 0 && files.length === 0;

  return (
    <div className="card section-card">
      <div className="section-header">
        <div className="section-header-title">
          <span className="section-icon accent-blue">
            <Folder size={18} />
          </span>
          <div>
            <h3>My Files</h3>
            <p>Your personal cloud storage</p>
          </div>
        </div>

        <div className="section-header-actions">
          <button type="button" className="btn btn-secondary" onClick={handleNewFolder}>
            <FolderPlus size={15} /> New Folder
          </button>
          <label className="btn btn-primary">
            <UploadIcon size={15} />
            {isUploading ? "Uploading..." : "Upload"}
            <input type="file" onChange={handleUpload} disabled={isUploading} hidden />
          </label>
        </div>
      </div>

      {!atRoot && (
        <div className="breadcrumbs">
          {path.map((crumb, index) => (
            <span key={crumb.id ?? "root"}>
              {index > 0 && <span className="crumb-sep">/</span>}
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
      )}

      {error && <p className="form-error">{error}</p>}

      {isLoading ? (
        <p className="section-loading">Loading...</p>
      ) : isEmpty ? (
        <EmptyState
          icon={<Folder size={28} />}
          title="This folder is empty"
          description="Upload files or create a new folder to get started."
        />
      ) : (
        <ul className="file-list">
          {folders.map((folder) => (
            <li key={`folder-${folder.id}`} className="file-row">
              <button
                type="button"
                className="link-button file-name"
                onClick={() => openFolder(folder)}
              >
                <Folder size={16} className="file-row-icon" /> {folder.name}
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
        </ul>
      )}
    </div>
  );
}

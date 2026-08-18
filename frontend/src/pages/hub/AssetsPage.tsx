import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { Dialog } from "./Dialog";
import { useHub } from "./HubContext";
import { hubText } from "./i18n";
import type { AssetFile, AssetRecord } from "./types";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;
type Filter = "all" | "upload" | "workflow" | "benchmark";
type PreviewStatus = "loading" | "image" | "text" | "unsupported" | "error";

interface PreviewState {
  file: AssetFile;
  status: PreviewStatus;
  content?: string;
  imageUrl?: string;
  truncated?: boolean;
}

function formatBytes(value = 0): string {
  if (!value) return "";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function AssetsPage() {
  const { language } = useLanguage();
  const { toast, confirm } = useHub();
  const location = useLocation();
  const tooltip = useTooltipText();
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const previewRequestRef = useRef<AbortController | null>(null);
  const previewObjectUrlRef = useRef<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<{ assets: AssetRecord[] }>("/assets/");
      setAssets(response.assets || []);
    } catch (error) {
      toast(error instanceof Error ? error.message : hubText(language, "assets.load_error"), "error");
    } finally {
      setLoading(false);
    }
  }, [language, toast]);

  // Hub giữ các tab đã ghé thăm ở trạng thái mounted và chỉ ẩn chúng. Theo dõi
  // route để lần quay lại Tài sản luôn đọc snapshot mới thay vì chờ remount.
  useEffect(() => {
    if (location.pathname === "/hub/assets" || location.pathname.startsWith("/hub/assets/")) {
      void load();
    }
  }, [load, location.pathname]);

  useEffect(() => {
    const reloadWhenVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    window.addEventListener("focus", reloadWhenVisible);
    document.addEventListener("visibilitychange", reloadWhenVisible);
    return () => {
      window.removeEventListener("focus", reloadWhenVisible);
      document.removeEventListener("visibilitychange", reloadWhenVisible);
    };
  }, [load]);

  useEffect(() => () => {
    previewRequestRef.current?.abort();
    if (previewObjectUrlRef.current) URL.revokeObjectURL(previewObjectUrlRef.current);
  }, []);

  const closePreview = useCallback(() => {
    previewRequestRef.current?.abort();
    previewRequestRef.current = null;
    if (previewObjectUrlRef.current) {
      URL.revokeObjectURL(previewObjectUrlRef.current);
      previewObjectUrlRef.current = null;
    }
    setPreview(null);
  }, []);

  const openPreview = async (file: AssetFile) => {
    previewRequestRef.current?.abort();
    if (previewObjectUrlRef.current) {
      URL.revokeObjectURL(previewObjectUrlRef.current);
      previewObjectUrlRef.current = null;
    }
    setPreview({ file, status: "loading" });
    if (!file.preview_url) {
      setPreview({ file, status: "unsupported" });
      return;
    }

    const controller = new AbortController();
    previewRequestRef.current = controller;
    try {
      const response = await fetch(file.preview_url, { cache: "no-store", signal: controller.signal });
      if (response.status === 415) {
        setPreview({ file, status: "unsupported" });
        return;
      }
      if (!response.ok) {
        setPreview({ file, status: "error" });
        return;
      }

      const mediaType = (response.headers.get("Content-Type") || "").split(";", 1)[0];
      const truncated = response.headers.get("X-Preview-Truncated") === "true";
      if (["image/png", "image/jpeg", "image/gif", "image/webp"].includes(mediaType)) {
        const imageUrl = URL.createObjectURL(await response.blob());
        previewObjectUrlRef.current = imageUrl;
        setPreview({ file, status: "image", imageUrl });
        return;
      }
      if (mediaType === "text/plain" || mediaType === "application/json") {
        let content = await response.text();
        if (mediaType === "application/json") {
          try {
            content = JSON.stringify(JSON.parse(content), null, 2);
          } catch {
            // JSON bị hỏng hoặc bị cắt vẫn có ích ở dạng nguyên văn.
          }
        }
        setPreview({ file, status: "text", content, truncated });
        return;
      }
      setPreview({ file, status: "unsupported" });
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setPreview({ file, status: "error" });
      }
    } finally {
      if (previewRequestRef.current === controller) previewRequestRef.current = null;
    }
  };

  const upload = async (files: FileList | File[]) => {
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const form = new FormData();
        form.append("file", file);
        await apiClient.postForm("/assets/upload", form);
      }
      toast(hubText(language, "assets.upload_success"), "success");
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : hubText(language, "assets.upload_error"), "error");
    } finally {
      setUploading(false);
    }
  };

  const remove = async (asset: AssetRecord) => {
    if (!asset.id.startsWith("upload-") || !(await confirm(hubText(language, "assets.delete_confirm")))) return;
    await apiClient.delete(`/assets/${asset.id.slice(7)}`);
    toast(hubText(language, "assets.delete_success"), "success");
    await load();
  };

  const filtered = filter === "all" ? assets : assets.filter((asset) => asset.source === filter);
  const labels: Record<Filter, string> = {
    all: hubText(language, "assets.all"), upload: hubText(language, "assets.uploaded"),
    workflow: hubText(language, "assets.workflow"), benchmark: hubText(language, "assets.benchmark"),
  };

  return <div className={c("page")}>
    <header className={c("pageHeader")}><div><h1>{hubText(language, "assets.title")}</h1><p>{hubText(language, "assets.subtitle")}</p></div></header>
    <div className={c("filterBar")}>{(Object.keys(labels) as Filter[]).map((key) => <Tooltip key={key} label={tooltip("tooltip.assets.filter", labels[key])}><button className={filter === key ? c("activePill") : c("pill")} onClick={() => setFilter(key)}>{labels[key]} ({key === "all" ? assets.length : assets.filter((asset) => asset.source === key).length})</button></Tooltip>)}</div>
    <Tooltip label={tooltip(uploading ? "tooltip.assets.uploading" : "tooltip.assets.upload")}>
      <button className={c("dropzone")} disabled={uploading} onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); if (event.dataTransfer.files.length) void upload(event.dataTransfer.files); }}>
        <Icon name={uploading ? "sync" : "upload"} /><strong>{uploading ? hubText(language, "common.loading") : hubText(language, "assets.upload")}</strong>
        <input ref={inputRef} type="file" multiple hidden onChange={(event) => { if (event.target.files?.length) void upload(event.target.files); event.target.value = ""; }} />
      </button>
    </Tooltip>
    {loading ? <div className={c("loading")}><Icon name="sync" />{hubText(language, "common.loading")}</div> : filtered.length ? <section className={c("assetGrid")}>{filtered.map((asset) => <article className={c("assetCard")} key={asset.id}>
      <div className={c("assetTop")}><span className={c("assetIcon")}><Icon name={asset.source === "benchmark" ? "flask" : asset.source === "workflow" ? "workflow" : "document"} /></span><span className={c("tag")}>{labels[asset.source as Filter] || asset.source}</span></div>
      <h2>{asset.name}</h2><p>{asset.label ? `${asset.label} · ` : ""}{asset.files.length} file · {(asset.created_at || "").slice(0, 16)}</p>
      <div className={c("assetFiles")}>{asset.files.map((file) => <button type="button" key={`${asset.id}-${file.name}`} onClick={() => void openPreview(file)}><span>{file.name}</span><small>{formatBytes(file.size_bytes)}</small><Icon name="eye" /></button>)}</div>
      {asset.deletable ? <Tooltip label={tooltip("tooltip.assets.delete", asset.name || "")}><button className={c("dangerLink")} onClick={() => void remove(asset)}><Icon name="trash" />{hubText(language, "common.delete")}</button></Tooltip> : null}
    </article>)}</section> : <div className={c("empty")}><Icon name="assets" /><span>{hubText(language, "assets.empty")}</span></div>}

    {preview ? <Dialog title={`${hubText(language, "assets.preview")}: ${preview.file.name}`} onClose={closePreview} wide>
      <div className={c("assetPreviewBody")}>
        {preview.status === "loading" ? <div className={c("loading")}><Icon name="sync" />{hubText(language, "assets.preview_loading")}</div> : null}
        {preview.status === "image" && preview.imageUrl ? <img className={c("assetPreviewImage")} src={preview.imageUrl} alt={preview.file.name} /> : null}
        {preview.status === "text" ? <pre className={c("assetPreviewText")}>{preview.content}</pre> : null}
        {preview.status === "unsupported" ? <div className={c("assetPreviewMessage")}><Icon name="warning" /><span>{hubText(language, "assets.preview_unsupported")}</span></div> : null}
        {preview.status === "error" ? <div className={c("assetPreviewMessage")}><Icon name="warning" /><span>{hubText(language, "assets.preview_error")}</span></div> : null}
        {preview.truncated ? <p className={c("assetPreviewNotice")}><Icon name="info" />{hubText(language, "assets.preview_truncated")}</p> : null}
        <div className={c("assetPreviewActions")}>
          <a className={c("buttonGhost")} href={preview.file.download_url} target="_blank" rel="noreferrer"><Icon name="download" />{hubText(language, "assets.download")}</a>
          <button type="button" className={c("primaryButton")} onClick={closePreview}>{hubText(language, "assets.close")}</button>
        </div>
      </div>
    </Dialog> : null}
  </div>;
}

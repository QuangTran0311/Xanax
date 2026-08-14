import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "../../api/client";
import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { useTooltipText } from "../../i18n/tooltips";
import { useLanguage } from "../../store/language";
import { useHub } from "./HubContext";
import { hubText } from "./i18n";
import type { AssetRecord } from "./types";
import styles from "./HubPage.module.css";

const c = (name: string) => styles[name] ?? name;
type Filter = "all" | "upload" | "workflow" | "benchmark";

function formatBytes(value = 0): string {
  if (!value) return ""; if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function AssetsPage() {
  const { language } = useLanguage(); const { toast, confirm } = useHub();
  const tooltip = useTooltipText();
  const [assets, setAssets] = useState<AssetRecord[]>([]); const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true); const [uploading, setUploading] = useState(false); const inputRef = useRef<HTMLInputElement>(null);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<{ assets: AssetRecord[] }>("/assets/");
      setAssets(response.assets || []);
    } catch (error) {
      const fallback = language === "vi" ? "Không tải được tài sản" : "Could not load assets";
      toast(error instanceof Error ? error.message : fallback, "error");
    } finally {
      setLoading(false);
    }
  }, [language, toast]);
  useEffect(() => { void load(); }, [load]);

  const upload = async (files: FileList | File[]) => {
    setUploading(true);
    try {
      for (const file of Array.from(files)) { const form = new FormData(); form.append("file", file); await apiClient.postForm("/assets/upload", form); }
      toast(language === "vi" ? "Đã tải file lên" : "Files uploaded", "success"); await load();
    } catch (error) { toast(error instanceof Error ? error.message : "Upload failed", "error"); } finally { setUploading(false); }
  };
  const remove = async (asset: AssetRecord) => {
    if (!asset.id.startsWith("upload-") || !(await confirm(hubText(language, "assets.delete_confirm")))) return;
    await apiClient.delete(`/assets/${asset.id.slice(7)}`); toast(language === "vi" ? "Đã xoá file" : "File deleted", "success"); await load();
  };
  const filtered = filter === "all" ? assets : assets.filter((asset) => asset.source === filter);
  const labels: Record<Filter, string> = { all: hubText(language, "assets.all"), upload: hubText(language, "assets.uploaded"), workflow: hubText(language, "assets.workflow"), benchmark: hubText(language, "assets.benchmark") };
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
      <div className={c("assetFiles")}>{asset.files.map((file) => <a key={`${asset.id}-${file.name}`} href={file.download_url} target="_blank" rel="noreferrer"><span>{file.name}</span><small>{formatBytes(file.size_bytes)}</small><Icon name="download" /></a>)}</div>
      {asset.deletable ? <Tooltip label={tooltip("tooltip.assets.delete", asset.name || "")}><button className={c("dangerLink")} onClick={() => void remove(asset)}><Icon name="trash" />{hubText(language, "common.delete")}</button></Tooltip> : null}
    </article>)}</section> : <div className={c("empty")}><Icon name="assets" /><span>{hubText(language, "assets.empty")}</span></div>}
  </div>;
}

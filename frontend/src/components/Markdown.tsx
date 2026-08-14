import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import { marked, Renderer, type Tokens } from "marked";

import { useTooltipText } from "../i18n/tooltips";
import { Tooltip } from "./Tooltip";

marked.setOptions({ breaks: true, gfm: true });

const defaultImageRenderer = new Renderer().image;
const defaultLinkRenderer = new Renderer().link;

const DOCUMENT_FILE_RE = /\.(xlsx|xls|csv|docx|doc|pdf|pptx|ppt|zip|rar|7z|txt|json|xml)(?:[?#]|$)/i;
const DOCUMENT_FILE_LABEL_RE = /\.(xlsx|xls|csv|docx|doc|pdf|pptx|ppt|zip|rar|7z|txt|json|xml)$/i;

const FILE_META: Record<string, { kind: string; label: string; icon: string }> = {
  xlsx: { kind: "excel", label: "Excel", icon: "XLS" },
  xls: { kind: "excel", label: "Excel", icon: "XLS" },
  csv: { kind: "excel", label: "Excel", icon: "CSV" },
  docx: { kind: "word", label: "Word", icon: "DOC" },
  doc: { kind: "word", label: "Word", icon: "DOC" },
  pdf: { kind: "pdf", label: "PDF", icon: "PDF" },
  pptx: { kind: "presentation", label: "PowerPoint", icon: "PPT" },
  ppt: { kind: "presentation", label: "PowerPoint", icon: "PPT" },
  zip: { kind: "archive", label: "Nén", icon: "ZIP" },
  rar: { kind: "archive", label: "Nén", icon: "RAR" },
  "7z": { kind: "archive", label: "Nén", icon: "7Z" },
  txt: { kind: "text", label: "Văn bản", icon: "TXT" },
  json: { kind: "text", label: "Văn bản", icon: "JSON" },
  xml: { kind: "text", label: "Văn bản", icon: "XML" },
};

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
  })[character] || character);
}

function cleanFileLabel(label: string): string {
  return label.replace(/^\s*📎\s*/, "").trim();
}

function fileNameFromLink(href: string, label: string): string {
  const cleanLabel = cleanFileLabel(label);
  if (cleanLabel && cleanLabel !== href) return cleanLabel;
  const path = href.split(/[?#]/, 1)[0];
  const rawName = path.slice(path.lastIndexOf("/") + 1) || "Tệp đính kèm";
  try { return decodeURIComponent(rawName); } catch { return rawName; }
}

marked.use({
  renderer: {
    image(token: Tokens.Image) {
      const html = Reflect.apply(defaultImageRenderer, this, [token]) as string;
      if (!html.startsWith("<img ")) return html;
      return html.replace(
        "<img ",
        '<img class="markdown-chat-thumbnail" loading="lazy" tabindex="0" role="button" ',
      );
    },
    link(token: Tokens.Link) {
      // `download_url` của backend không có phần mở rộng, nên phải soi cả nhãn và ưu tiên nhãn vì đó mới là tên file thật.
      const match = DOCUMENT_FILE_LABEL_RE.exec(cleanFileLabel(token.text)) ?? DOCUMENT_FILE_RE.exec(token.href);
      if (!match) return Reflect.apply(defaultLinkRenderer, this, [token]) as string;

      const extension = match[1].toLocaleLowerCase("en");
      const meta = FILE_META[extension];
      const fileName = fileNameFromLink(token.href, token.text);
      const normalLink = Reflect.apply(defaultLinkRenderer, this, [token]) as string;
      const openingEnd = normalLink.indexOf(">");
      if (openingEnd === -1 || !normalLink.startsWith("<a ")) return normalLink;
      const opening = normalLink.slice(0, openingEnd).replace(
        "<a ",
        `<a class="markdown-chat-file" data-file-kind="${meta.kind}" download `,
      );
      const titledOpening = /\stitle=/.test(opening) ? opening : `${opening} title="Tải ${escapeHtml(fileName)}"`;
      return `${titledOpening}>`
        + `<span class="markdown-chat-file-icon" aria-hidden="true">${meta.icon}</span>`
        + `<span class="markdown-chat-file-copy"><strong>${escapeHtml(fileName)}</strong>`
        + `<small>${meta.label} · Bấm để tải xuống</small></span>`
        + '<span class="markdown-chat-file-download" aria-hidden="true">↓</span></a>';
    },
  },
});

const ATTACHMENT_COMMENT = /\n*<!--\s*FILE PAPA GỬI KÈM[\s\S]*?-->\n*/g;
const TOOL_PREFIX = "[[XANAX:";

export interface LightboxImage {
  src: string;
  caption: string;
}

interface LightboxState {
  images: LightboxImage[];
  index: number;
}

export function ImageLightbox({ images, index, onIndexChange, onClose }: {
  images: LightboxImage[];
  index: number;
  onIndexChange: (index: number) => void;
  onClose: () => void;
}) {
  const tooltip = useTooltipText();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const currentImage = images[index];

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [onClose]);

  if (!currentImage) return null;
  const move = (direction: -1 | 1) => onIndexChange((index + direction + images.length) % images.length);

  return createPortal(
    <div
      className="markdown-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={`Xem ảnh: ${currentImage.caption}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <Tooltip label={tooltip("tooltip.image.close")}><button ref={closeButtonRef} type="button" className="markdown-lightbox-close" aria-label={tooltip("tooltip.image.close")} onClick={onClose}>×</button></Tooltip>
      {images.length > 1 ? <>
        <Tooltip label={tooltip("tooltip.image.previous")}><button type="button" className="markdown-lightbox-prev" aria-label={tooltip("tooltip.image.previous")} onClick={() => move(-1)}>‹</button></Tooltip>
        <Tooltip label={tooltip("tooltip.image.next")}><button type="button" className="markdown-lightbox-next" aria-label={tooltip("tooltip.image.next")} onClick={() => move(1)}>›</button></Tooltip>
      </> : null}
      <figure className="markdown-lightbox-figure">
        <img className="markdown-lightbox-image" src={currentImage.src} alt={currentImage.caption} />
        <figcaption className="markdown-lightbox-caption">
          <span>{currentImage.caption}</span>
          <span className="markdown-lightbox-actions">
            <a href={currentImage.src} download={currentImage.caption}>Tải xuống</a>
            <a href={currentImage.src} target="_blank" rel="noreferrer">Mở tab mới</a>
          </span>
        </figcaption>
      </figure>
      {images.length > 1 ? <div className="markdown-lightbox-count" aria-live="polite">{index + 1} / {images.length}</div> : null}
    </div>,
    document.body,
  );
}

/**
 * Loại bỏ lệnh công cụ đã hoàn chỉnh và giữ kín lệnh hoặc tiền tố còn dang dở.
 * Gọi hàm này với mỗi phần nội dung tích luỹ để cú pháp công cụ không chớp lên.
 */
export function stripToolSyntaxForDisplay(raw: string): string {
  let visible = "";
  let cursor = 0;
  while (cursor < raw.length) {
    const marker = raw.indexOf(TOOL_PREFIX, cursor);
    if (marker === -1) {
      visible += raw.slice(cursor);
      break;
    }
    visible += raw.slice(cursor, marker);
    const end = raw.indexOf("]]", marker + TOOL_PREFIX.length);
    if (end === -1) return visible;
    cursor = end + 2;
  }

  // Một phần nội dung có thể kết thúc giữa tiền tố (`[`, `[[`, `[[XA`, ...).
  for (let length = Math.min(TOOL_PREFIX.length - 1, visible.length); length > 0; length -= 1) {
    if (TOOL_PREFIX.startsWith(visible.slice(-length))) return visible.slice(0, -length);
  }
  return visible;
}

export function renderMarkdown(content: string, streaming = false): string {
  const withoutPrivateAttachmentPath = content.replace(ATTACHMENT_COMMENT, "\n\n");
  const display = streaming
    ? stripToolSyntaxForDisplay(withoutPrivateAttachmentPath)
    : withoutPrivateAttachmentPath.replace(/\[\[XANAX:[\s\S]*?\]\]/g, "");
  return marked.parse(display) as string;
}

function imageFromElement(image: HTMLImageElement): LightboxImage {
  return {
    src: image.currentSrc || image.src,
    caption: image.alt.trim() || "Ảnh đính kèm",
  };
}

function markImageAsError(image: HTMLImageElement) {
  image.classList.add("markdown-chat-thumbnail-error");
  image.removeAttribute("role");
  image.removeAttribute("tabindex");
  image.setAttribute("aria-label", `Không tải được ảnh: ${image.alt || "không có tên"}`);
  image.title = `Không tải được ảnh: ${image.alt || "không có tên"}`;
}

export function Markdown({ content, streaming = false }: { content: string; streaming?: boolean }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [lightbox, setLightbox] = useState<LightboxState | null>(null);

  const openLightbox = (image: HTMLImageElement) => {
    if (image.classList.contains("markdown-chat-thumbnail-error")) return;
    const elements = Array.from(
      rootRef.current?.querySelectorAll<HTMLImageElement>(".markdown-chat-thumbnail:not(.markdown-chat-thumbnail-error)") ?? [],
    );
    const index = elements.indexOf(image);
    if (index === -1) return;
    setLightbox({ images: elements.map(imageFromElement), index });
  };

  const handleClick = (event: MouseEvent<HTMLDivElement>) => {
    if (!(event.target instanceof HTMLImageElement) || !event.target.classList.contains("markdown-chat-thumbnail")) return;
    event.preventDefault();
    openLightbox(event.target);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!(event.target instanceof HTMLImageElement) || !event.target.classList.contains("markdown-chat-thumbnail")) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openLightbox(event.target);
  };

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const handleImageError = (event: Event) => {
      if (!(event.target instanceof HTMLImageElement) || !event.target.classList.contains("markdown-chat-thumbnail")) return;
      markImageAsError(event.target);
    };

    // `error` không bubble; phải nghe DOM ở pha capture vì ảnh được tạo bởi innerHTML, không có onError của React.
    root.addEventListener("error", handleImageError, true);
    return () => root.removeEventListener("error", handleImageError, true);
  }, []);

  useEffect(() => {
    rootRef.current?.querySelectorAll<HTMLImageElement>("img.markdown-chat-thumbnail").forEach((image) => {
      if (image.complete && image.naturalWidth === 0) markImageAsError(image);
    });
  }, [content, streaming]);

  return (
    <>
      <div
        ref={rootRef}
        className="markdown-chat-content"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        dangerouslySetInnerHTML={{ __html: renderMarkdown(content, streaming) }}
      />
      {lightbox ? <ImageLightbox
        images={lightbox.images}
        index={lightbox.index}
        onIndexChange={(index) => setLightbox((current) => current ? { ...current, index } : null)}
        onClose={() => setLightbox(null)}
      /> : null}
    </>
  );
}

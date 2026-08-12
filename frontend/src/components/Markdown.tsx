import { marked } from "marked";

marked.setOptions({ breaks: true, gfm: true });

const ATTACHMENT_COMMENT = /\n*<!--\s*FILE PAPA GỬI KÈM[\s\S]*?-->\n*/g;
const TOOL_PREFIX = "[[XANAX:";
const IMAGE_PATH = /^(https?:\/\/|\/)\S+\.(png|jpe?g|gif|webp)(\?\S*)?$/i;
const IMAGE_MARKDOWN = /!\[([^\]]*)\]\(((?:https?:\/\/|\/)[^\s)]+)\)/g;

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Exact React port of legacy hub/utils.js renderOutputContent(). */
export function renderOutputContent(raw: unknown): string {
  const text = String(raw || "");
  if (!text) return "";
  const trimmed = text.trim();
  if (IMAGE_PATH.test(trimmed)) {
    return `<img src="${escapeHtml(trimmed)}" alt="Ảnh đã tạo" style="max-width:100%;border-radius: 0;">`;
  }
  if (!IMAGE_MARKDOWN.test(text)) return escapeHtml(text);
  IMAGE_MARKDOWN.lastIndex = 0;
  let output = "";
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = IMAGE_MARKDOWN.exec(text))) {
    output += escapeHtml(text.slice(lastIndex, match.index));
    output += `<img src="${escapeHtml(match[2])}" alt="${escapeHtml(match[1] || "Ảnh đã tạo")}" style="max-width:100%;border-radius: 0;margin:6px 0;display:block;">`;
    lastIndex = IMAGE_MARKDOWN.lastIndex;
  }
  return output + escapeHtml(text.slice(lastIndex));
}

/**
 * Remove complete tool commands and withhold an incomplete command or prefix.
 * Calling this for every accumulated chunk guarantees tool syntax never flashes.
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

  // A chunk may end halfway through the marker (`[`, `[[`, `[[XA`, ...).
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

export function Markdown({ content, streaming = false }: { content: string; streaming?: boolean }) {
  return <div dangerouslySetInnerHTML={{ __html: renderMarkdown(content, streaming) }} />;
}

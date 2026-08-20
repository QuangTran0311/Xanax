import type { CSSProperties } from "react";

export const ICONS = {
  bell: '<path d="M18 8a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  home: '<path d="M4 11L12 4l8 7" /><path d="M6 10v9a1 1 0 001 1h10a1 1 0 001-1v-9" /><rect x="10" y="14" width="4" height="6" rx="1" fill="currentColor" stroke="none"/>',
  bot: '<rect x="5" y="7" width="14" height="12" rx="5" /><circle cx="9.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="14.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><path d="M9.5 16c.8.6 3.2.6 4 0" /><line x1="12" y1="7" x2="12" y2="4.5"/><circle cx="12" cy="4" r="1" fill="currentColor" stroke="none"/>',
  sliders: '<line x1="4" y1="7" x2="20" y2="7"/><circle cx="9" cy="7" r="2" fill="currentColor" stroke="none"/><line x1="4" y1="13" x2="20" y2="13"/><circle cx="15" cy="13" r="2" fill="currentColor" stroke="none"/><line x1="4" y1="19" x2="20" y2="19"/><circle cx="7" cy="19" r="2" fill="currentColor" stroke="none"/>',
  briefcase: '<rect x="3" y="8" width="18" height="11" rx="2"/><path d="M8 8V6a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="3" y1="13" x2="21" y2="13"/>',
  meeting: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.3"/><path d="M15 20c0-2.5 1.8-4.5 4-4.8"/>',
  teach: '<path d="M12 5l9 4-9 4-9-4 9-4z"/><path d="M6 11v4c0 1.5 2.7 3 6 3s6-1.5 6-3v-4"/>',
  workflow: '<circle cx="5" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="19" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="12" cy="18" r="2" fill="currentColor" stroke="none"/><path d="M7 6h10"/><path d="M12 8v6"/>',
  bolt: '<path d="M13 3L6 14h5l-1 7 7-11h-5l1-7z" fill="currentColor" stroke="none"/>',
  assets: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M4 7.5L12 12l8-4.5"/><path d="M12 12v9"/>',
  brain: '<path d="M9 4a3 3 0 00-3 3v1a3 3 0 000 6v1a3 3 0 003 3M15 4a3 3 0 013 3v1a3 3 0 010 6v1a3 3 0 01-3 3M9 4v16M15 4v16"/>',
  cost: '<circle cx="12" cy="12" r="8"/><path d="M12 7v10M9.5 9.5h4a1.5 1.5 0 010 3h-3a1.5 1.5 0 000 3h4.5"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M21 12h-3M6 12H3M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1M18.4 18.4l-2.1-2.1M7.7 7.7L5.6 5.6"/>',
  folder: '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
  sync: '<path d="M4 12a8 8 0 0114-5.3M20 12a8 8 0 01-14 5.3"/><path d="M18 4v4h-4M6 20v-4h4"/>',
  close: '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>',
  check: '<path d="M4 12l5 5L20 6"/>',
  warning: '<path d="M12 4l9 15.5H3L12 4z"/><line x1="12" y1="10" x2="12" y2="14"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><line x1="12" y1="11" x2="12" y2="16"/><circle cx="12" cy="7.5" r="0.9" fill="currentColor" stroke="none"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3.2 2"/>',
  document: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><line x1="9.5" y1="12" x2="14.5" y2="12"/><line x1="9.5" y1="15.5" x2="14.5" y2="15.5"/>',
  download: '<path d="M12 4v11"/><path d="M7.5 11L12 15.5 16.5 11"/><path d="M5 18.5h14"/>',
  upload: '<path d="M12 19V8"/><path d="M7.5 12L12 7.5 16.5 12"/><path d="M5 19.5h14"/>',
  lock: '<rect x="5.5" y="11" width="13" height="9" rx="2"/><path d="M8 11V7.5a4 4 0 018 0V11"/>',
  plug: '<path d="M9 3v6M15 3v6"/><path d="M6.5 9h11v3a5.5 5.5 0 01-11 0V9z"/><path d="M12 17.5V21"/>',
  people: '<circle cx="8.5" cy="8" r="3"/><path d="M2.5 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.3"/><path d="M15 20c0-2.5 1.8-4.5 4-4.8"/>',
  send: '<path d="M4 12l16-8-6 16-3-6-7-2z"/>',
  edit: '<path d="M15.5 4.5l4 4L8 20H4v-4L15.5 4.5z"/>',
  save: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v6h8V4"/><rect x="8" y="14" width="8" height="6"/>',
  trophy: '<path d="M7 4h10v6a5 5 0 01-10 0V4z"/><path d="M7 6H4v2a3 3 0 003 3M17 6h3v2a3 3 0 01-3 3"/><path d="M12 15v3"/><path d="M8.5 21h7l-1-3h-5l-1 3z"/>',
  puzzle: '<path d="M9 4h4v2.3a1.7 1.7 0 003.4 0V4H20v4h-2.3a1.7 1.7 0 000 3.4H20v4h-4v-2.3a1.7 1.7 0 00-3.4 0V15H9v-4H6.7a1.7 1.7 0 010-3.4H9V4z"/>',
  chart: '<line x1="5" y1="20" x2="5" y2="11"/><line x1="12" y1="20" x2="12" y2="6"/><line x1="19" y1="20" x2="19" y2="14"/><line x1="3" y1="20" x2="21" y2="20"/>',
  tag: '<path d="M12 3h6a2 2 0 012 2v6L11 20 2 11 12 3z"/><circle cx="15" cy="8" r="1.2" fill="currentColor" stroke="none"/>',
  book: '<path d="M4 5.5c2.5-1 5-1 8 0v14c-3-1-5.5-1-8 0z"/><path d="M20 5.5c-2.5-1-5-1-8 0v14c3-1 5.5-1 8 0z"/>',
  image: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M4 17l5-4.5 3.5 3 3-2.5L20 17"/>',
  code: '<path d="M9 8l-4.5 4L9 16"/><path d="M15 8l4.5 4-4.5 4"/>',
  flask: '<path d="M10 3h4M10 3v6l-4.5 8a2 2 0 001.7 3h9.6a2 2 0 001.7-3L14 9V3"/><line x1="8" y1="14" x2="16" y2="14"/>',
  arrowUp: '<line x1="12" y1="19" x2="12" y2="6"/><path d="M7 10.5L12 6 17 10.5"/>',
  arrowDown: '<line x1="12" y1="5" x2="12" y2="18"/><path d="M7 13.5L12 18 17 13.5"/>',
  arrowRight: '<line x1="4" y1="12" x2="19" y2="12"/><path d="M13.5 6.5L19 12l-5.5 5.5"/>',
  arrowLeft: '<line x1="20" y1="12" x2="5" y2="12"/><path d="M10.5 6.5L5 12l5.5 5.5"/>',
  chevronDown: '<path d="M6 9l6 6 6-6"/>',
  sun: '<circle cx="12" cy="12" r="4.2"/><path d="M12 3v2.2M12 18.8V21M4.2 12H2M22 12h-2.2M5.6 5.6l1.5 1.5M16.9 16.9l1.5 1.5M18.4 5.6l-1.5 1.5M7.1 16.9l-1.5 1.5"/>',
  moon: '<path d="M20 13.5A8.5 8.5 0 119.7 3.2 6.8 6.8 0 0020 13.5z"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.3" y1="15.3" x2="20.5" y2="20.5"/>',
  scale: '<path d="M12 3v18"/><path d="M5 7h14"/><path d="M5 7l-2.5 6a2.5 2.5 0 005 0L5 7z"/><path d="M19 7l-2.5 6a2.5 2.5 0 005 0L19 7z"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  globe: '<circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/>',
  doc: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  robot: '<rect x="4" y="7" width="16" height="13" rx="2"/><path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/><line x1="9" y1="13" x2="9" y2="14"/><line x1="15" y1="13" x2="15" y2="14"/><line x1="9" y1="17" x2="15" y2="17"/>',
  branch: '<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="12" r="2.5"/><path d="M8.2 7.2 15.8 10.8"/><path d="M8.2 16.8 15.8 13.2"/>',
  taskImage: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
  person: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/>',
  stop: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
  filter: '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
  db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/><path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/>',
  taskCode: '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
  layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
  taskClock: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
  octagon: '<polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
  taskBook: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  api: '<path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/><path d="M12 3v14"/><path d="M6 9l6-6 6 6"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  shuffle: '<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/>',
  taskSliders: '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
  link: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  external: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle>',
  loginLock: '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path>',
  eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>',
  eyeOff: '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>',
  loginArrow: '<path d="M5 12h14M12 5l7 7-7 7"></path>',
} as const;

export type IconName = keyof typeof ICONS;

export interface IconProps {
  name: IconName;
  className?: string;
  size?: number | string;
  strokeWidth?: number;
  title?: string;
  filled?: boolean;
  style?: CSSProperties;
}

export function Icon({
  name,
  className,
  size,
  strokeWidth = 1.8,
  title,
  filled = false,
  style,
}: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
      style={style}
    >
      {title ? <title>{title}</title> : null}
      <g dangerouslySetInnerHTML={{ __html: ICONS[name] }} />
    </svg>
  );
}

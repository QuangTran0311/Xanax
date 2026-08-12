// Bảng màu cho hình đại diện nhân viên — 20 màu, khôi phục từ bản vanilla cũ.
//
// Mỗi màu là một cặp: `bg` cho nền chip, `ink` cho nét vẽ. Cặp pastel-nền /
// đậm-nét này đọc được trên CẢ nền sáng lẫn nền tối, nên không cần bản riêng
// cho từng theme — cũng là lý do giữ nguyên giá trị cũ thay vì chỉnh lại.
//
// Trước file này, danh sách màu là ["mint","lavender","peach","sky","gold","#9366ff"]
// và CSS chỉ có rule cho 4 cái. Chọn "gold" hay "#9366ff" thì avatar lặng lẽ về
// màu mặc định. Giờ màu vẽ thẳng bằng inline style nên không còn khoảng cách
// giữa "màu chào ra" và "màu CSS biết vẽ".

export interface AvatarColor {
  label: string;
  bg: string;
  ink: string;
}

export const AVATAR_COLORS: Record<string, AvatarColor> = {
  mint: { label: "Bạc hà", bg: "#D8EEE0", ink: "#3F8A63" },
  peach: { label: "Đào", bg: "#FBE3CE", ink: "#C97A3A" },
  lavender: { label: "Oải hương", bg: "#E4DBF7", ink: "#7C6BAE" },
  sky: { label: "Trời xanh", bg: "#DCEAF5", ink: "#4A7FA6" },
  rose: { label: "Hoa hồng", bg: "#F7DCE3", ink: "#AE536B" },
  coral: { label: "San hô", bg: "#F8D8CF", ink: "#B85D48" },
  amber: { label: "Hổ phách", bg: "#F8E7BE", ink: "#9A6A17" },
  lemon: { label: "Chanh", bg: "#F5EFBF", ink: "#81751D" },
  lime: { label: "Chanh xanh", bg: "#E2EDC7", ink: "#64813A" },
  forest: { label: "Rừng", bg: "#D3E6D7", ink: "#477655" },
  teal: { label: "Ngọc lam", bg: "#CFE9E5", ink: "#347C73" },
  aqua: { label: "Biển sáng", bg: "#D3EDF0", ink: "#397D85" },
  blue: { label: "Lam", bg: "#D6E2F5", ink: "#4B6FA7" },
  indigo: { label: "Chàm", bg: "#DCDDF3", ink: "#5E61A0" },
  violet: { label: "Tím", bg: "#E8D9F2", ink: "#82569E" },
  plum: { label: "Mận", bg: "#EBD8E7", ink: "#8F557F" },
  sand: { label: "Cát", bg: "#EEE3CF", ink: "#856D48" },
  cocoa: { label: "Ca cao", bg: "#E7DAD2", ink: "#805F50" },
  silver: { label: "Bạc", bg: "#E5E8EA", ink: "#606A70" },
  slate: { label: "Đá phiến", bg: "#DDE3E7", ink: "#536674" },
};

export const AVATAR_COLOR_KEYS = Object.keys(AVATAR_COLORS);
export const DEFAULT_COLOR = "mint";

/** Cặp màu cho một key bất kỳ; key lạ hoặc mã hex cũ thì rơi về mặc định. */
export function avatarColor(key: string | undefined | null): AvatarColor {
  return AVATAR_COLORS[key || ""] ?? AVATAR_COLORS[DEFAULT_COLOR];
}

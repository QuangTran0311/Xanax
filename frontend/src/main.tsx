// Font tự chứa, không tải từ fonts.googleapis.com nữa. Chỉ nạp đúng các độ đậm
// mà giao diện dùng — đúng bộ trước đây khai trong thẻ <link> của index.html:
// Quicksand 500/600/700, Inter 400/500/600/700, JetBrains Mono 400/500.
// Vite gom chúng vào bản build nên app chạy được khi mất mạng ngoài.
import "@fontsource/quicksand/500.css";
import "@fontsource/quicksand/600.css";
import "@fontsource/quicksand/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";

// Bảng màu + thang cỡ chữ dùng chung. Nạp SAU font và TRƯỚC mọi CSS module,
// để token có mặt trước khi trang đầu tiên vẽ.
import "./styles/theme.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Không tìm thấy phần tử #root");
}

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);

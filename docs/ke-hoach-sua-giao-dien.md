# Kế hoạch sửa giao diện Xanax — Phase 1–10, kèm Phase 2-bis và 2-ter

> Tài liệu này viết cho một agent thực thi (Codex). Đọc **toàn bộ mục "Luật chung"**
> trước khi gõ dòng code đầu tiên. Sau mỗi phase **PHẢI DỪNG** và chờ người duyệt.

Ngày lập: 2026-08-12 · Nhánh gốc: `main` @ `e7bb3d7` · Typecheck sạch tại thời điểm lập.

---

## 0. LUẬT CHUNG — đọc kỹ, vi phạm là hỏng

### 0.1. Quy tắc dừng

Mỗi phase kết thúc bằng mục **"CHỐT PHASE"**. Khi tới đó:

1. Chạy đủ các lệnh trong "Kiểm chứng máy" của phase đó, dán **nguyên văn output** ra.
2. Commit với đúng message ghi trong phase (không gộp phase).
3. **DỪNG. Không được bắt đầu phase kế tiếp.** Chờ người duyệt nói "tiếp".

Nếu một bước trong phase không làm được, **không tự ý bỏ qua và cũng không tự ý
làm cách khác** — dừng lại, báo rõ vướng ở đâu, chờ chỉ đạo.

### 0.1-bis. AI KHÔNG KIỂM MẮT — kiểm mắt là việc của con người

**Agent thực thi (Codex) và agent soạn kế hoạch (Claude) đều KHÔNG có công cụ trình
duyệt.** Cả hai đều không mở được trang, không chụp được màn hình, và **không cấp
được phiên Browser cho bên kia.** Đừng hỏi xin — câu trả lời sẽ luôn là không.

Chỉ **người dùng** kiểm mắt được. Vì vậy quy trình chốt phase là:

| Bước | Ai làm |
|---|---|
| 1. Sửa code | Codex |
| 2. `npm run typecheck` + `npm run build` | Codex |
| 3. Chạy lệnh "Kiểm chứng máy", dán output | Codex |
| 4. **BÀN GIAO**: dán checklist kiểm mắt của phase + URL, rồi dừng | Codex |
| 5. **Kiểm mắt** | **NGƯỜI DÙNG** |
| 6. Người dùng nói "đạt" hoặc mô tả cái lệch | Người dùng |
| 7. Commit theo message của phase, rồi dừng chờ duyệt phase sau | Codex |

**Bước 4 không phải là "bị chặn".** Đó là bàn giao có chủ đích, và là trạng thái
đúng để dừng. Báo cáo phải ghi rõ: *"Đã xong bước 1-3. Chờ người dùng kiểm mắt theo
checklist mục X.Y tại <URL>."* — **không** viết "không hoàn tất được cửa kiểm mắt"
và **không** yêu cầu ai mở trình duyệt hộ.

Nếu người dùng nói bỏ qua kiểm mắt cho một phase, cứ commit và **ghi vào báo cáo
phase** rằng kiểm mắt đã được hoãn theo chỉ đạo — để lần duyệt sau còn biết.

### 0.2. Phạm vi tuyệt đối không đụng tới

- **Không** sửa file trong `backend/`.
- **Không** sửa `src/api/`, `src/ws/`, `src/store/`, `src/i18n/`, `src/pages/hub/meetingProtocol.ts`,
  `src/pages/taskrunner/protocol.ts`, `src/pages/taskrunner/graphAdapter.ts`, `src/pages/taskrunner/workflowApi.ts`.
- **Không** đổi/xoá bất kỳ `data-testid` nào. Chúng là điểm neo của script kiểm thử.
- **Không** đổi đường dẫn route, tên API, hình dạng props giữa các component.
- **Không** chạy `npm install`, không thêm dependency mới, không đổi `package.json`.
- **Không** format lại hàng loạt (prettier/eslint --fix trên cả file). Chỉ sửa đúng dòng được chỉ định.
  File CSS trong repo này cố tình viết dòng dài; format lại sẽ tạo diff hàng nghìn dòng và
  che mất thay đổi thật.

### 0.3. Bốn màu KHÔNG được token hoá — để nguyên hex

Có bốn nhóm mã hex trông "cần dọn" nhưng thực ra là **cố ý**. Đụng vào là hỏng:

| Nhóm | Vị trí | Vì sao phải giữ |
|---|---|---|
| Chữ/nền trong sidebar | `HubPage.module.css` các luật `.sidebar`, `.brand`, `.brand small`, `.navItem`, `.navItem:hover`, `.navActive`, `.sidebarHealth*`, `.collapseButton*` — gồm `#f2f6f4 #91aaa2 #a9bbb5 #dff8ec #8da79e #9fb1ab #fff #52d6a0 #d7a95e` | Sidebar **luôn** nền tối ở cả hai theme (`--sidebar` là `#06110f` ở tối và `#12382d` ở sáng). Chữ ở đây phải cố định sáng. Đổi sang `var(--text)` là chữ đen trên nền xanh đậm ở theme Sáng. |
| Ô xem trước theme | `.themePreviewLight`, `.themePreviewDark` (`#f4eee6 #fff #221e1a #2c2721`) | Đây là **mẫu màu minh hoạ** trong trang Cài đặt. Chúng phải trông giống theme mà chúng đại diện, bất kể theme đang bật. |
| Icon trên node | `TaskrunnerPage.module.css` `.flow-node .node-icon`, `.pick-node-item .node-icon`, `.inspector-header .node-icon`, `.se-card-icon`, `.editor-logo`, `.flow-node.node-running::before` (`#fff`) | Nền của các phần tử này do inline style đặt theo loại node, luôn là màu đậm bão hoà. |
| Chữ nút đăng nhập | `LoginPage.module.css` `.submit-btn` (`#fff`) | Quyết định của người dùng ngày **2026-08-13**, sau khi đã được cho biết chữ trắng trên nền accent ở theme tối chỉ đạt **1.83:1**, dưới ngưỡng WCAG AA **4.5:1**. Người dùng ưu tiên hình thức ở trang đăng nhập và chấp nhận đánh đổi này. Phase sau quét chữ trắng trên nền màu sẽ thấy chỗ này: phải **BỎ QUA**, không “sửa” về token. |

### 0.3-bis. ⚠ SỐ DÒNG TRONG TÀI LIỆU NÀY LÀ THAM KHẢO, KHÔNG PHẢI ĐỊA CHỈ

Mọi số dòng trong các bảng "Dòng | Selector" được tính ở mốc `e7bb3d7`, **trước
Phase 1**. Phase 1 xoá các khối token rỗng nên số dòng đã trôi:

| File | Độ lệch sau Phase 1 |
|---|---|
| `pages/hub/HubPage.module.css` | **−22** |
| `pages/workspace/WorkspacePage.module.css` | −12 |
| `pages/taskrunner/TaskrunnerPage.module.css` | −20 |
| `pages/login/LoginPage.module.css` | 0 (Phase 1 không đụng) |
| `styles/theme.css` | +4 |

Và mỗi phase sau lại làm trôi tiếp.

**LUẬT: định vị bằng SELECTOR, không bằng số dòng.** Mọi bảng trong tài liệu đều
có cột selector — đó mới là địa chỉ thật. Cách làm đúng:

```bash
grep -n '<selector>' <file>      # tìm vị trí HIỆN TẠI rồi mới sửa
```

Nếu selector tìm không ra, hoặc ra nhiều hơn một chỗ — **DỪNG và báo**. Đừng đoán
theo số dòng ghi trong tài liệu.

### 0.4-bis. Khi lệnh kiểm chứng mâu thuẫn với chính kế hoạch

Các con số "KỲ VỌNG" trong tài liệu này do người soạn tính tay và **có thể sai**.
Nếu output của một lệnh lệch với kỳ vọng, phân loại trước khi kết luận:

| Loại lệch | Cách xử lý |
|---|---|
| Lệch vì **chú thích** bạn vừa được yêu cầu viết cũng chứa chuỗi đang grep | Kết quả **hợp lệ**. Ghi rõ trong báo cáo phase là "lệch do chú thích", nêu con số thật, đi tiếp. |
| Lệch vì lệnh đếm cả file `dist/`, `node_modules/` | Chạy lại có giới hạn `src/`. |
| Lệch vì **code** thật khác kỳ vọng | **DỪNG.** Không tự chỉnh cho khớp con số. Báo lại. |

Nguyên tắc: **kỳ vọng phục vụ việc kiểm chứng, không phải ngược lại.** Không bao giờ
sửa code chỉ để một lệnh grep ra đúng số. Khi nghi ngờ thì dừng và hỏi — như bạn đang làm.

### 0.4. Cách kiểm chứng bằng máy

Không có Playwright, không có test frontend trong repo. Công cụ có sẵn:

```bash
cd frontend
npm run typecheck          # tsc -b --pretty false
npm run build              # tsc -b && vite build
npm run verify:graphs
npm run verify:workflow-protocol
npm run verify:meeting-protocol
npm run verify:hub-integration
```

Backend (chỉ chạy ở phase cuối để chắc không vạ lây):

```bash
cd backend && python -m pytest -q
```

Vì không có test giao diện, **grep là công cụ kiểm chứng chính**. Mỗi phase có sẵn
lệnh grep với con số kỳ vọng. Con số không khớp = chưa xong hoặc làm quá tay.

### 0.5. Kiểm tra bằng mắt

> ## ⚠ XEM ĐÚNG CỔNG — dự án này có HAI đường vào cùng lúc
>
> | URL | Phục vụ cái gì | Dùng để kiểm mắt? |
> |---|---|---|
> | `http://127.0.0.1:5173` | **Dev server Vite** — đọc thẳng từ `src/`, có HMR | ✅ **DÙNG CÁI NÀY** |
> | `http://localhost:8000` | Backend phục vụ thư mục `dist/` — bản **đã build** | ❌ Chỉ đúng sau `npm run build` |
>
> Đây là bẫy đã sập một lần thật ở Phase 2: kiểm mắt trên `:8000` cho thấy nút vẫn
> hỏng y như trước, vì `dist/` là bản build từ trước khi sửa. Kế hoạch chỉ yêu cầu
> `npm run typecheck` sau mỗi phase, **không** yêu cầu `npm run build`, nên `dist/`
> gần như luôn cũ hơn `src/`.
>
> **Kiểm mắt LUÔN LUÔN trên `:5173`.** Nếu vì lý do gì phải xem ở `:8000` thì bắt
> buộc `npm run build` ngay trước đó, và nói rõ trong báo cáo là đã build.
>
> Cách nhận biết bạn đang xem bản cũ: sửa xong mà giao diện **không đổi gì hết** —
> kiểm cổng trước khi kết luận là sửa không ăn.

Sau mỗi phase có sửa hiển thị, chạy `npm run dev` và tự mở **trên `127.0.0.1:5173`**,
ở **cả hai theme** (nút mặt trăng góc phải trên) và **cả hai ngôn ngữ**
(Cài đặt → Ngôn ngữ):

```
/hub            /hub/agents     /hub/skills     /hub/tasks
/hub/meeting    /hub/train      /hub/company-runner
/hub/auto-runner /hub/assets    /hub/model      /hub/cost
/hub/settings   /login
```

Mở DevTools Console — **phải 0 lỗi JS**. Nếu phase nào có nói "chụp màn hình", chụp
và đính kèm khi báo cáo.

### 0.6. Ghi chú về `c()`

Cả ba trang dùng `const c = (name) => styles[name] ?? name`. Gõ sai tên class
**không báo lỗi** — nó lặng lẽ trả về chuỗi thô không khớp luật nào. Vì vậy:
mỗi khi thêm/đổi tên class, phải chạy lệnh đối chiếu ở Phase 8 để chắc không lệch.

---

# PHASE 1 — Sửa lỗi vỡ bố cục trang "Dạy AI"

**Mức độ: nghiêm trọng. Trang đang hỏng thật, không phải chuyện thẩm mỹ.**

## 1.1. Bối cảnh (đọc để hiểu vì sao, đừng sửa kiểu khác)

File `frontend/src/pages/workspace/WorkspacePage.module.css` dòng 113:

```css
.workspace {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: var(--sidebar) 1fr var(--info);
  overflow: hidden;
}
```

Trước commit `1ebe071`, file này tự khai `--sidebar: 240px` và `--info: 300px` trong
khối `.workspace-page-root`. Commit đó dọn token màu cục bộ và **xoá nhầm cả hai token
độ dài này** (chúng nằm lẫn trong cùng khối).

Trong khi đó `frontend/src/styles/theme.css` có hai token **trùng tên nhưng là màu**:

- dòng 23: `--sidebar: #06110f`  (nền sidebar, theme tối)
- dòng 45: `--info: #5b9df0`     (xanh dương ngữ nghĩa)
- dòng 83: `--sidebar: #12382d`  (theme sáng)
- dòng 100: `--info: #2f6fb8`    (theme sáng)

Nên hiện tại dòng 113 tính ra `grid-template-columns: #06110f 1fr #5b9df0` — không hợp lệ
ở thời điểm computed-value → trình duyệt **bỏ nguyên khai báo** → grid rơi về một cột.
Ba panel (danh sách phiên / chat / thông tin) xếp chồng dọc thay vì nằm cạnh nhau.

## 1.2. Việc phải làm

### Bước 1.2.a — Khai lại hai token, đặt tên riêng không đụng theme

Mở `frontend/src/pages/workspace/WorkspacePage.module.css`.

Hiện dòng 4-33 là một khối rỗng (chỉ có chú thích và ~27 dòng trắng):

```css
.workspace-page-root {
  /* Token gốc "Quản lý một đội ngũ" — bản Tối ấm (tự soạn) */
    
   
   
   ... (khoảng 27 dòng trắng) ...
}
```

**Thay toàn bộ khối đó** (từ `.workspace-page-root {` ở dòng 4 tới `}` đóng khối,
tức là hết dòng 33) bằng đúng đoạn này:

```css
/* ══════════════════════════════════════════════════════════════════════════
   Bề rộng hai cột biên của bố cục ba panel.

   TÊN CÓ TIỀN TỐ `--ws-` LÀ BẮT BUỘC, KHÔNG ĐƯỢC RÚT GỌN.

   Trước đây hai token này tên là `--sidebar` và `--info`. Mà theme.css cũng có
   `--sidebar` (nền sidebar, #06110f) và `--info` (xanh dương, #5b9df0) — là MÀU.
   Khi token cục bộ bị gỡ trong commit 1ebe071, var(--sidebar) rơi xuống lấy giá
   trị màu ở :root, biến grid-template-columns thành `#06110f 1fr #5b9df0`. Khai
   báo không hợp lệ bị bỏ, grid ba cột sập xuống một cột, và KHÔNG có lỗi nào
   trong console để lần ra.

   Đổi lại tên ngắn là tái hiện đúng lỗi đó.
   ══════════════════════════════════════════════════════════════════════════ */
.workspace-page-root {
  --ws-col-sessions: 240px;
  --ws-col-info: 300px;
}
```

### Bước 1.2.b — Dùng tên mới ở dòng grid

Tại luật `.workspace` (dòng ~113 trước khi sửa), đổi:

```css
  grid-template-columns: var(--sidebar) 1fr var(--info);
```

thành:

```css
  grid-template-columns: var(--ws-col-sessions) minmax(0, 1fr) var(--ws-col-info);
```

> `minmax(0, 1fr)` thay cho `1fr`: cột giữa chứa khung chat có nội dung không co được
> (khối code, bảng, ảnh). Với `1fr` thuần, min-width mặc định là `auto` nên nội dung dài
> sẽ đẩy phồng cột và tràn ngang. Hai cột biên đã cố định px nên không cần.

### Bước 1.2.c — Dọn khối rỗng cùng loại ở hai file còn lại

Cùng một commit để lại hai khối rỗng tương tự. Chúng vô hại **nhưng chính chúng đã che
mất lỗi trên** (nhìn vào thấy khối rỗng, không ai ngờ có token bị mất). Xoá đi:

1. `frontend/src/pages/taskrunner/TaskrunnerPage.module.css` dòng 3-21 — khối
   `.taskrunner-root{ /* Token gốc ... */ <18 dòng trắng> }`.
   **Xoá cả khối.** Không xoá luật `.taskrunner-root` ở dòng ~697
   (`{height:100vh;display:flex;...}`) — luật đó đang có tác dụng.

2. `frontend/src/pages/hub/HubPage.module.css` — trong luật `.hubRoot` (dòng ~7-22)
   và `:global(body.light) .hubRoot`, xoá các dòng trắng thừa.
   **GIỮ LẠI** `--accentStrong` và `--accentSoft` ở cả hai khối — chúng đang được dùng.
   Kiểm tra trước khi xoá: `grep -c 'accentStrong\|accentSoft' HubPage.module.css`

### Bước 1.2.d — Chặn tái diễn: thêm cảnh báo vào theme.css

Vào `frontend/src/styles/theme.css`, ngay trên dòng `--sidebar: #06110f;` (dòng 23),
chèn chú thích:

```css
  /* CẢNH BÁO: đây là MÀU nền sidebar, không phải bề rộng. Trang Dạy AI từng có
     token cục bộ trùng tên mang giá trị 240px; khi nó bị gỡ, var(--sidebar) rơi
     xuống lấy màu này và làm sập bố cục ba cột mà không báo lỗi. Token độ dài của
     trang đó nay tên là --ws-col-sessions / --ws-col-info. */
```

## 1.3. Kiểm chứng máy

```bash
cd frontend

# 1. Không còn chỗ nào dùng token màu cho thuộc tính độ dài.
#    KỲ VỌNG: không in ra dòng nào.
grep -rn 'grid-template-columns:.*var(--sidebar)\|grid-template-columns:.*var(--info)' src/

# 2. Token mới đã có và đang được dùng.
#    KỲ VỌNG: đúng 4 dòng —
#      WorkspacePage.module.css : 2 dòng khai báo (--ws-col-sessions, --ws-col-info)
#      WorkspacePage.module.css : 1 dòng dùng trong grid-template-columns
#      theme.css                : 1 dòng CHÚ THÍCH (bước 1.2.d nhắc cả hai tên trên
#                                 cùng một dòng — đây là mong muốn, không phải lỗi)
grep -rn -- '--ws-col-sessions\|--ws-col-info' src/

# 2b. Chỉ đếm phần CODE, bỏ chú thích. KỲ VỌNG: đúng 3 dòng, đều ở WorkspacePage.
grep -rn -- '--ws-col-sessions\|--ws-col-info' src/ | grep -v '^\S*theme\.css'

# 3. KỲ VỌNG: sạch, không lỗi.
npm run typecheck && npm run build
```

## 1.4. Kiểm chứng mắt (bắt buộc, đây là mục đích của cả phase)

`npm run dev` → mở `/hub/train`. Phải thấy **đúng ba cột nằm ngang**:

```
┌──────────────┬───────────────────────────┬────────────────┐
│ 240px        │  co giãn                  │ 300px          │
│ Phiên dạy    │  Khung chat               │ Thông tin phiên│
│ học AI       │  (tin nhắn + ô nhập)      │ (tên, đánh giá,│
│ [+]          │                           │  bài học...)   │
└──────────────┴───────────────────────────┴────────────────┘
```

Đối chiếu với ảnh lỗi: trước khi sửa, ba khối này xếp chồng dọc và chỉ có
**một** thanh cuộn dọc chung; sau khi sửa mỗi panel cuộn riêng.

Kiểm ở **cả theme Tối và Sáng**. Console phải 0 lỗi.

## 1.5. CHỐT PHASE 1

```
fix(ui): khôi phục bố cục ba cột trang Dạy AI

Token --sidebar/--info của trang bị gỡ nhầm trong 1ebe071 cùng với đám token
màu. theme.css lại có hai token trùng tên nhưng là màu, nên
grid-template-columns thành `#06110f 1fr #5b9df0` — không hợp lệ, bị trình
duyệt bỏ, grid ba cột sập xuống một cột và không có lỗi nào trong console.

Đặt lại tên thành --ws-col-sessions / --ws-col-info để không còn va tên. Cột
giữa đổi 1fr → minmax(0,1fr) để nội dung không co được (code block, bảng, ảnh)
không đẩy phồng cột.

Dọn hai khối token rỗng còn lại của commit đó và thêm cảnh báo cạnh --sidebar
trong theme.css.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 2 — Sửa nút "Kết thúc" bị xuống dòng ở Phòng họp

**Phase nhỏ, ít rủi ro nhất. Làm riêng để nếu có gì lạ thì khoanh vùng được ngay.**

## 2.1. Bối cảnh

`frontend/src/pages/hub/HubPage.module.css` luật `.meetingRoomHeader`:

```css
.meetingRoomHeader { min-height:66px;border-bottom:1px solid var(--border);padding:10px 14px;display:flex;align-items:center;gap:9px; }
.meetingRoomHeader > div:first-child { flex:1;min-width:0; }
```

Header là flex, có 3 con: ô tiêu đề (`flex:1`), `.meetingConnection` (`white-space:nowrap`),
và nút `.buttonDanger`/`.primaryButton`. Nút là phần tử **duy nhất** không có
`flex-shrink:0` cũng không có `white-space:nowrap`, nên nó là chỗ bị bóp. Chữ
"Kết thúc" tách xuống hai dòng, nút cao gấp đôi mọi nút khác trong app.
`--fs-scale: 1.15` làm chuyện này xảy ra sớm hơn nhiều so với thiết kế gốc.

## 2.2. Việc phải làm

### Bước 2.2.a — Sửa toàn cục cho mọi nút

Tìm luật gộp bằng `grep -n 'primaryButton,\.buttonDanger,\.buttonGhost' src/pages/hub/HubPage.module.css`
(sau Phase 1 nó ở **dòng 112**; xem mục 0.3-bis về việc số dòng trôi). **Thêm** hai
thuộc tính vào cuối khối, giữ nguyên mọi thứ đang có:

```css
white-space: nowrap;
flex-shrink: 0;
```

Nút trong app này ở đâu cũng là nhãn ngắn (1-3 từ). Không có nút nào cần xuống dòng.
Sửa ở luật gộp thì mọi nút chính/nguy hiểm/phụ đều được, không phải vá từng chỗ.

### Bước 2.2.b — Cho tiêu đề phòng họp co được

Tiêu đề dài cũng góp phần ép nút. Tại `.meetingRoomHeader h2` (sau Phase 1 ở **dòng 149**,
tìm bằng `grep -n 'meetingRoomHeader h2'`), **thêm**:

```css
overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
```

(`.meetingRoomHeader p` đã có ba thuộc tính này rồi — làm cho `h2` khớp với `p`.)

## 2.3. Không được làm

- **Không** rút ngắn chữ "Kết thúc" / "End" / "Chốt kế hoạch" / "Finalize" trong
  `MeetingsPage.tsx`. Sửa CSS, không sửa nội dung.
- **Không** bỏ icon trong nút.
- **Không** đổi `min-height:66px` của header.

## 2.4. Kiểm chứng

```bash
cd frontend
# KỲ VỌNG: luật .primaryButton,.buttonDanger,.buttonGhost có cả nowrap lẫn flex-shrink
grep -o '\.primaryButton,\.buttonDanger,\.buttonGhost[^}]*}' src/pages/hub/HubPage.module.css
npm run typecheck
```

Mắt: `/hub/meeting` → chọn một cuộc họp đang diễn ra. Nút "Kết thúc" phải **một dòng**,
cùng chiều cao với các nút khác trong app (so với nút "Cuộc họp mới" ở đầu trang).
Thử thu hẹp cửa sổ tới ~900px — nút vẫn một dòng, tiêu đề cụt bằng dấu `…`.

## 2.5. CHỐT PHASE 2

```
fix(ui): nút trong header phòng họp không còn xuống dòng

.meetingRoomHeader là flex; ô tiêu đề có flex:1 và .meetingConnection có
white-space:nowrap, nên nút là phần tử duy nhất co được và bị bóp cho tới khi
chữ tách hai dòng, cao gấp đôi mọi nút khác. --fs-scale 1.15 làm nó xảy ra sớm.

Thêm white-space:nowrap và flex-shrink:0 vào luật gộp của cả ba loại nút —
nhãn nút trong app đều 1-3 từ, không nút nào cần xuống dòng. Tiêu đề h2 nay
cụt bằng ellipsis giống đoạn phụ đề p ngay dưới nó.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 2-BIS — Ô nhập tin nhắn Phòng họp nằm sát đáy

**PHẢI LÀM TRƯỚC PHASE 3.** Lý do ở mục 2b.2.

## 2b.1. Bối cảnh

`.meetingLayout` trong `HubPage.module.css`:

```css
.meetingLayout { display:grid;grid-template-columns:285px minmax(0,1fr);gap:14px;height:calc(100vh - 155px);min-height:590px; }
```

`155px` là ước lượng **cứng** cho chiều cao mọi thứ nằm trên khung họp. Chiều cao thật,
đo ở viewport 1920px:

| Thành phần | Cao |
|---|---|
| `.workspace` topbar (`grid-template-rows: 58px ...`) | 58px |
| `.page` padding-top | 28px |
| `.pageHeader h1` — `clamp(24px,3vw,32px)` × line-height 1.15 | 36.8px |
| `.pageHeader h1` margin-bottom | 5px |
| `.pageHeader p` — `calc(12px × 1.15)` × line-height 1.55 | 21.4px |
| `.pageHeader` margin-bottom | 24px |
| **TỔNG** | **173.2px** |

Trừ 155 trong khi thật là 173.2 → khung họp cao dư **18.2px**. Cộng
`.page { padding-bottom: 50px }` → tổng **~68px** vượt quá vùng nhìn. `.content` sinh
thanh cuộn và ô nhập tin bị đẩy lên khỏi đáy đúng chừng đó.

**Đây là lỗi có sẵn từ trước, không phải do Phase 2 gây ra.** Đối chiếu ảnh chụp
trước Phase 2: ô nhập tin ở đúng vị trí đó với khoảng trống bên dưới y hệt.

## 2b.2. Vì sao phải làm TRƯỚC Phase 3

`155px` mã hoá cứng chiều cao `.pageHeader`, mà `.pageHeader p` phụ thuộc `--fs-scale`.
Phase 3 mở rộng `--fs-scale` ra thêm 23 chỗ nữa, và mục đích của cái núm đó là để
người dùng chỉnh. **Mọi lần chỉnh `--fs-scale` đều làm lệch thêm con số này.**

Vá bằng cách đổi `155px` thành `173px` chỉ là đổi số ma này lấy số ma khác — **KHÔNG
ĐƯỢC LÀM THẾ.** Phải bỏ hẳn cơ chế trừ chiều cao.

## 2b.3. Cách làm — tái dùng cơ chế đã có sẵn trong repo

Ba tab `train` / `company-runner` / `auto-runner` đã giải đúng bài này bằng
`.tabPanelFull`. Cho `meeting` dùng chung cơ chế đó.

### Bước 2b.3.a — `HubPage.tsx`

Trong `HubShell`, tìm biến `fullHeight`:

```tsx
const fullHeight = item.tab === "train"
  || item.tab === "company-runner"
  || item.tab === "auto-runner";
```

Thêm `meeting`:

```tsx
const fullHeight = item.tab === "train"
  || item.tab === "company-runner"
  || item.tab === "auto-runner"
  || item.tab === "meeting";
```

**Chỉ sửa đúng biểu thức này.** Không đụng `navigation[]`, không đụng `HubTabContent`,
không đụng thứ tự tab.

### Bước 2b.3.b — `HubPage.module.css`

Thêm ba luật mới. `.tabPanelFull` và `.page` cùng nằm trong một CSS module nên
selector con hoạt động bình thường (tên hash khớp nhau).

```css
/* Phòng họp lấp đúng chiều cao còn lại thay vì trừ đi một con số đoán trước.
   `155px` cũ mã hoá cứng chiều cao topbar + padding + pageHeader; sai 18px ngay
   từ đầu, và lệch thêm mỗi lần đổi --fs-scale. */
.tabPanelFull .page { flex: 1; min-height: 0; width: 100%; display: flex; flex-direction: column; padding-bottom: 18px; }
.tabPanelFull .pageHeader { flex-shrink: 0; }
.tabPanelFull .meetingLayout { height: auto; flex: 1; min-height: 0; }
```

> ### ⚠ `width: 100%` LÀ BẮT BUỘC, KHÔNG ĐƯỢC BỎ
>
> `.page` gốc có `max-width: 1500px; margin: 0 auto`. Khi nó là **block** trong
> `.tabPanel`, `margin:0 auto` nghĩa là "chiếm hết bề rộng khả dụng đến 1500px rồi
> căn giữa" — đúng ý.
>
> Nhưng `.tabPanelFull` là flex container, nên `.page` thành **flex item**. Với flex
> item, **margin `auto` theo trục ngang vô hiệu hoá `align-self: stretch`**: hộp co
> về đúng bề rộng nội dung rồi căn giữa. Kết quả là cả trang teo lại còn ~710px giữa
> màn hình, thừa hai bên.
>
> `width: 100%` khôi phục hành vi cũ: hộp giãn hết khung, `max-width` chặn ở 1500px,
> `margin: 0 auto` căn giữa phần dư. `box-sizing: border-box` đã đặt toàn cục ở dòng 1
> nên `width:100%` cộng padding không tràn.
>
> Đây là lỗi đã xảy ra thật một lần khi kiểm mắt Phase 2-bis. Nếu sau khi sửa mà
> trang Phòng họp hẹp bất thường — kiểm dòng này trước tiên.

> ### ⚠ KHÔNG ĐẾM CỨNG SỐ CON CỦA `.meetingRoom`
>
> Kiểm mắt lần 1 của Phase 2-bis phát hiện ô nhập tin của cuộc họp đang diễn ra
> còn cách đáy panel khoảng 200px. Nguyên nhân là `grid-template-rows` khai báo năm
> hàng theo giả định luôn có đủ header, participantPanel, meetingRecord,
> meetingMessages và meetingComposer. Trong thực tế `meetingRecord` chỉ render khi
> cuộc họp không active, còn `meetingComposer` chỉ render khi active; hai khối loại
> trừ nhau nên `.meetingRoom` luôn chỉ có bốn con trực tiếp. Ở trạng thái active,
> composer vì thế rơi vào hàng `minmax(190px,1fr)` và bị kéo giãn.
>
> Cách sửa bền vững là dùng flex column cho `.meetingRoom`, cho
> `.meetingMessages { flex:1; min-height:190px }`, và giữ header, participantPanel,
> meetingRecord, meetingComposer ở `flex-shrink:0`. Như vậy vùng tin nhắn tự nhận
> phần chiều cao dư, không phụ thuộc vị trí hay số lượng phần tử tùy điều kiện.

> **Vì sao `padding-bottom: 18px` chứ không phải 0:** để khung họp không dính sát
> mép dưới cửa sổ. `.page` gốc có `padding-bottom: 50px` — trong bố cục cuộn thì hợp
> lý, trong bố cục lấp đầy thì đó là 50px chết.

> **`.tabPanelFull .page` KHÔNG ảnh hưởng ba tab kia** — `train` và hai runner render
> `WorkspacePage`/`TaskrunnerPage`, không dùng class `.page` của Hub. Kiểm lại bằng
> `grep -n 'c("page")' src/pages/hub/*.tsx` — chỉ các trang Hub có, và trong số đó
> chỉ `MeetingsPage` chạy dưới `.tabPanelFull`.

### Bước 2b.3.c — `min-height: 590px` biến đi đâu

Luật gốc có `min-height:590px` để khung họp không bị bóp trên màn thấp. Trong bố cục
mới, `.tabPanelFull` có `overflow:hidden` nên `min-height` sẽ gây **cắt cụt** thay vì
sinh thanh cuộn. Vì vậy `.tabPanelFull .meetingLayout` đặt `min-height: 0`.

Đánh đổi: trên cửa sổ **rất thấp** (dưới ~600px chiều cao), khung họp bị nén. Ba tab
kia đã chịu đánh đổi y hệt và chạy ổn. **Bắt buộc kiểm mắt ở cửa sổ cao ~600px** —
xem mục 2b.5.

## 2b.4. Không được làm

- **KHÔNG** đổi `155px` thành một số khác. Đó là quay lại đúng vấn đề.
- **KHÔNG** xoá luật `.meetingLayout` gốc — luật gốc vẫn phục vụ media query 720px
  (`.meetingLayout{height:auto;min-height:0}`) và trường hợp chưa vào tabPanelFull.
  Chỉ **thêm** luật `.tabPanelFull .meetingLayout` đè lên.
- **KHÔNG** đưa `.meetingRoom` trở lại `grid-template-rows` đếm cứng số con.
  `meetingRecord` và `meetingComposer` loại trừ nhau; vùng co giãn phải gắn trực
  tiếp vào `.meetingMessages`, không gắn vào thứ tự phần tử.
- **KHÔNG** dùng `position:absolute`/`fixed` để ghim ô nhập tin xuống đáy. Nó phải là
  flex child cuối không co giãn, nếu không sẽ đè lên tin nhắn.

## 2b.5. Kiểm chứng

```bash
cd frontend

# 1. Không còn chiều cao tính bằng 100vh trừ số ma trong khối phòng họp dùng
#    tabPanelFull. KỲ VỌNG: chỉ còn 1 dòng — luật gốc, dành cho media query.
grep -n 'meetingLayout' src/pages/hub/HubPage.module.css

# 2. meeting đã vào danh sách fullHeight. KỲ VỌNG: có dòng `|| item.tab === "meeting"`.
grep -n -A4 'const fullHeight' src/pages/hub/HubPage.tsx

# 3. Chỉ MeetingsPage dùng c("page") và chạy dưới tabPanelFull.
grep -n 'c("page")' src/pages/hub/*.tsx

npm run typecheck && npm run build      # BẮT BUỘC build — xem mục 0.5 về cổng
```

## 2b.6. Kiểm mắt — cửa chính của phase này

Trên `:5173`, **hoặc** `:8000` sau khi đã `npm run build`:

| Việc | Kỳ vọng |
|---|---|
| `/hub/meeting`, chọn cuộc họp | Ô nhập tin **sát đáy vùng nội dung**, không còn khoảng trống dưới nó |
| Cùng lúc | **Không** còn thanh cuộn dọc ở `.content` (mép phải ngoài cùng) |
| Vùng tin nhắn | Vẫn cuộn được **riêng nó**, thanh cuộn nằm trong khung họp |
| Thu hẹp cửa sổ **cao ~600px** | Khung họp bị nén nhưng ô nhập tin **vẫn thấy được** |
| Thu hẹp ngang **~700px** | Media query 720px vào cuộc, bố cục xếp dọc, vẫn dùng được |
| **Đi hết 11 tab còn lại** | Không tab nào đổi bố cục — `.tabPanelFull .page` chỉ được chạm tới ở tab Phòng họp |
| Đổi theme | Không đổi gì về bố cục |

Tab cần soi kỹ nhất sau Phòng họp: `/hub/tasks`, `/hub/agents`, `/hub/model` — chúng
dùng `.page` nhiều nhất. Nếu chúng đổi bố cục thì `.tabPanelFull .page` đang rò sang
chỗ không mong muốn → **DỪNG và báo**.

## 2b.7. CHỐT PHASE 2-BIS

```
fix(ui): ô nhập tin Phòng họp nằm sát đáy, bỏ chiều cao đoán trước

.meetingLayout dùng height:calc(100vh - 155px). 155px là ước lượng cứng cho
topbar + padding + pageHeader, mà chiều cao thật ở 1920px là 173.2px — sai 18px
ngay từ đầu. Cộng .page{padding-bottom:50px} thành ~68px vượt vùng nhìn, nên
.content sinh thanh cuộn và ô nhập tin bị đẩy lên khỏi đáy đúng chừng đó.

Đổi 155 thành 173 chỉ là đổi số ma này lấy số ma khác: con số đó mã hoá chiều
cao .pageHeader, mà .pageHeader phụ thuộc --fs-scale — cái núm sinh ra để người
dùng chỉnh. Nên bỏ hẳn cơ chế trừ chiều cao.

Cho tab Phòng họp dùng .tabPanelFull như ba tab train/company-runner/auto-runner
đã dùng: .page thành flex column lấp đầy, .meetingLayout flex:1 min-height:0.
Khung họp tự lấp chỗ còn lại, không phụ thuộc cỡ chữ hay chiều cao topbar.

Đánh đổi: min-height:590px cũ bị bỏ trong nhánh tabPanelFull vì overflow:hidden
sẽ cắt cụt thay vì sinh thanh cuộn. Trên cửa sổ cao dưới ~600px khung họp bị
nén — ba tab kia đã chịu đánh đổi y hệt.

Lỗi này có sẵn từ trước, không phải do phase sửa nút gây ra.

Kiểm mắt lần 1 còn làm lộ một lỗi có sẵn khác sau khi khung họp lấp đầy chiều
cao: .meetingRoom khai grid-template-rows cho 5 con, nhưng meetingRecord (chỉ
khi status != active) và meetingComposer (chỉ khi status == active) loại trừ
nhau nên thực tế luôn chỉ có 4 con. Khi họp đang diễn ra, composer rơi vào hàng
minmax(190px,1fr), bị kéo giãn khoảng 200px và tạo mảng trống dưới ô nhập. Đổi
.meetingRoom sang flex column, cho .meetingMessages{flex:1;min-height:190px},
và đặt bốn phần tử tĩnh ở flex-shrink:0 để chỉ vùng tin nhắn nhận chiều cao dư.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 2-TER — Bỏ tiêu đề trang Phòng họp, đưa nút tạo mới vào cột danh sách

**ĐÃ ĐƯỢC NGƯỜI DÙNG DUYỆT NGÀY 2026-08-13. PHẢI LÀM TRƯỚC PHASE 3.**

## 2t.1. Bối cảnh

Tab Phòng họp là workspace lấp đầy chiều cao. Sidebar đã đánh dấu rõ “Phòng họp”
đang active, nên `h1` “Phòng họp” và dòng mô tả trong `.pageHeader` lặp lại thông tin,
đồng thời lấy mất chiều cao dành cho danh sách và khung họp.

Nút **“Cuộc họp mới”** hiện nằm trong chính `.pageHeader`, vì vậy phải được giữ và
chuyển vào đầu cột danh sách bên trái. `.meetingList` đang có `overflow:auto`; nếu
đặt nút thẳng vào phần tử này thì nút sẽ cuộn mất khi danh sách dài. Cột trái phải
được tách thành một flex column: hàng thao tác cố định phía trên và danh sách cuộn
độc lập phía dưới.

Phase này cũng chốt nguyên tắc cho Phase 8: nhất quán theo **loại trang**, không ép
mọi tab cùng có `<h1>`. Bốn workspace lấp đầy màn hình (`meeting`, `train`,
`company-runner`, `auto-runner`) ưu tiên chiều cao nội dung và không có page header.

## 2t.2. Việc phải làm

### Bước 2t.2.a — Bỏ page header, giữ nút tạo mới

Trong `frontend/src/pages/hub/MeetingsPage.tsx`:

- Xoá toàn bộ `.pageHeader`, gồm `h1` “Phòng họp” và dòng mô tả.
- Giữ nguyên nút “Cuộc họp mới” / “New meeting”, icon, handler
  `setCreating(true)` và cơ chế song ngữ đang có.
- Đưa nút lên trên cùng của cột danh sách cuộc họp bên trái.

### Bước 2t.2.b — Tách phần cố định và phần cuộn của cột trái

Trong `MeetingsPage.tsx`, bọc cột trái bằng `.meetingSidebar`, gồm hai con trực tiếp:

1. `.meetingListActions` chứa nút tạo mới;
2. `.meetingList` chỉ chứa danh sách hoặc empty state.

Trong `frontend/src/pages/hub/HubPage.module.css`:

```css
.meetingSidebar { min-height:0;display:flex;flex-direction:column;gap:8px; }
.meetingListActions { display:flex;flex-shrink:0; }
.meetingList { flex:1;min-height:0;...;overflow:auto; }
```

Hàng thao tác bắt buộc `flex-shrink:0`; chính `.meetingList` nhận phần chiều cao dư
và giữ `overflow:auto`. Nút có thể chiếm toàn chiều rộng cột để hành động chính dễ thấy.

### Bước 2t.2.c — Dọn selector thừa và cân khoảng đệm

Kiểm tra ba trang con của `train` / `company-runner` / `auto-runner` trước khi đụng
`.tabPanelFull .pageHeader`. Nếu chúng không dùng `.pageHeader` của
`HubPage.module.css`, xoá selector `.tabPanelFull .pageHeader{flex-shrink:0}` vì sau
khi bỏ header Phòng họp không còn phần tử nào khớp.

Sau khi page header biến mất, khung họp không nên thừa khoảng trống phía trên hoặc
dính sát mép. Đặt `padding-top` của `.tabPanelFull .page` bằng `padding-bottom:18px`
đã chốt ở Phase 2-bis: **18px trên và 18px dưới**, đối xứng và không tạo thêm số ma.

## 2t.3. Không được làm

- **Không** xoá, đổi nhãn, đổi icon hoặc đổi handler của nút “Cuộc họp mới”.
- **Không** đặt nút bên trong `.meetingList`; nút phải đứng ngoài vùng `overflow:auto`.
- **Không** đổi `fullHeight`, `navigation[]`, thứ tự tab hay bắt đầu Phase 3.
- **Không** thêm chuỗi tiếng Việt cứng mới trong JSX. Chữ hiển thị phải qua
  `hubText()` hoặc nhánh `language === "vi" ? ... : ...` / biến `vi` như code hiện có.
- **Không** tạo key i18n mới khi nhãn song ngữ hiện tại dùng lại được.
- **Không** xoá `.tabPanelFull .pageHeader` trước khi xác nhận ba workspace còn lại
  không dùng class Hub này.

## 2t.4. Kiểm chứng máy

```bash
cd frontend

# 1. Header và hai chuỗi tiêu đề cũ đã rời MeetingsPage.
# KỲ VỌNG: không in ra gì.
grep -nE 'pageHeader|<h1>|Trao đổi cùng Xanax|Talk with Xanax' src/pages/hub/MeetingsPage.tsx

# 2. Cột trái có đủ wrapper, hàng thao tác và danh sách.
# KỲ VỌNG: TSX có meetingSidebar, meetingListActions, meetingList;
# CSS có flex column, flex-shrink:0, flex:1/min-height:0 và overflow:auto tương ứng.
grep -nE 'meetingSidebar|meetingListActions|meetingList' src/pages/hub/MeetingsPage.tsx
grep -nE '^\.meetingSidebar|^\.meetingListActions|^\.meetingList \{' src/pages/hub/HubPage.module.css

# 3. Selector pageHeader dưới tabPanelFull đã chết phải được dọn.
# KỲ VỌNG: không in ra gì.
grep -n '\.tabPanelFull \.pageHeader' src/pages/hub/HubPage.module.css

# 4. Khoảng đệm trên/dưới của page full-height cân nhau.
# KỲ VỌNG: luật in ra có padding-top:18px và padding-bottom:18px.
grep -n '^\.tabPanelFull \.page' src/pages/hub/HubPage.module.css

npm run typecheck && npm run build
```

Sau build, kiểm artifact:

```bash
# KỲ VỌNG: đúng 1 file HubPage-*.css.
find dist/assets -maxdepth 1 -name 'HubPage-*.css' -print

# KỲ VỌNG: CSS build có meetingSidebar/meetingListActions và không có selector
# .tabPanelFull .pageHeader.
grep -o 'meetingSidebar[^}]*}\|meetingListActions[^}]*}' dist/assets/HubPage-*.css
grep -o 'tabPanelFull[^}]*pageHeader[^}]*}' dist/assets/HubPage-*.css
```

## 2t.5. Kiểm mắt

Tại `http://localhost:8000/hub/meeting`, hard refresh sau khi build:

| Việc | Kỳ vọng |
|---|---|
| Đầu trang | Không còn `h1` “Phòng họp” và dòng mô tả |
| Cột trái | Nút “Cuộc họp mới” nằm trên cùng, ngay trên danh sách |
| Danh sách dài | Chỉ danh sách cuộn; nút tạo mới luôn đứng yên và nhìn thấy |
| Mép trên/dưới | Khung họp có khoảng thở cân nhau, không hụt cũng không dư |
| Chọn cuộc họp active | Ô nhập vẫn sát đáy vùng nội dung và thấy được |
| Cao khoảng 600px | Hàng thao tác không co mất; khung họp vẫn dùng được |
| Ngang khoảng 700px | Bố cục xếp dọc đúng media query, danh sách cuộn riêng |
| Hai theme, hai ngôn ngữ | Nhãn nút đúng; không vỡ bố cục; console 0 lỗi |

## 2t.6. CHỐT PHASE 2-TER

```
fix(ui): bỏ tiêu đề Phòng họp, ghim nút tạo mới trên danh sách

Phòng họp là workspace lấp đầy chiều cao và sidebar đã chỉ rõ tab đang active,
nên h1 cùng dòng mô tả lặp thông tin và lấy mất không gian của khung họp.

Giữ nút Cuộc họp mới nhưng chuyển lên đầu cột trái. Tách cột thành flex column:
hàng thao tác flex-shrink:0 ở trên, danh sách flex:1 min-height:0 overflow:auto ở
dưới, nên danh sách dài vẫn cuộn mà nút không biến mất.

Dọn selector .tabPanelFull .pageHeader sau khi xác nhận ba workspace còn lại không
dùng class Hub này. Cân padding trên/dưới của page full-height ở 18px, dùng lại
khoảng thở đã chốt trong Phase 2-bis thay vì thêm một số đoán trước mới.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 3 — Đưa toàn bộ cỡ chữ về `--fs-scale`

## 3.1. Bối cảnh

`--fs-scale` (mặc định `1.15`) là núm chỉnh cỡ chữ toàn app. **259** khai báo `font-size`
đã dùng nó đúng (231 với px nguyên, 28 với px thập phân kiểu `12.5px` — nhớ dùng regex
phủ cả hai, xem 3.5). Nhưng **25 khai báo dùng cú pháp viết tắt `font:`** có px thô,
trong đó cỡ chữ nằm giữa chuỗi shorthand nên không nhân được. 23 cái phải sửa, 2 cái
là ngoại lệ (mục 3.4).

Hệ quả cụ thể, đo được:

| Phần tử | Cỡ thật hiện tại |
|---|---|
| Chữ thân bài (`body`) | `14px × 1.15` = **16.1px** |
| Tiêu đề `<h2>` của panel (`.panel h2`) | **14px** |

Tiêu đề đang **nhỏ hơn** nội dung mà nó đặt tên. Toàn bộ thang phân cấp chữ bị nén.
Đây là nguyên nhân trực tiếp của cảm giác "giao diện loạn".

## 3.2. Phép biến đổi — áp dụng máy móc, đừng sáng tạo

Với **mỗi** luật CSS chứa `font:` có số px thô, **giữ nguyên dòng `font:` đó** và
**thêm ngay sau nó** một khai báo `font-size` riêng:

```css
/* TRƯỚC */
.panel h2 { margin: 0 0 15px; ...; font: 700 14px Quicksand,sans-serif; }

/* SAU */
.panel h2 { margin: 0 0 15px; ...; font: 700 14px Quicksand,sans-serif; font-size: calc(14px * var(--fs-scale)); }
```

**Vì sao thêm chứ không viết lại shorthand:** `font:` shorthand đặt luôn `font-weight`,
`line-height` và `font-family`. Tách nó ra thành các thuộc tính rời là 3-4 dòng cho
mỗi chỗ và rất dễ đánh rơi một cái. Khai `font-size` **sau** shorthand chỉ đè đúng
phần cỡ chữ, mọi thứ khác giữ nguyên.

**Về `line-height`:** mọi shorthand ở đây dùng line-height **không đơn vị**
(`/1.3`, `/1.2`, `/1`, `/1.5`, `/1.6`) — số không đơn vị nhân theo `font-size` cuối cùng,
nên nó tự giãn đúng. Không phải làm gì thêm. Nếu gặp line-height có đơn vị px thì
**dừng lại hỏi** (hiện không có chỗ nào).

## 3.3. Danh sách đầy đủ — 23 chỗ phải sửa

### `frontend/src/pages/hub/HubPage.module.css` (12 chỗ)

| Dòng | Selector | Thêm vào |
|---|---|---|
| 46 | `.brand small` | `font-size: calc(7px * var(--fs-scale));` |
| 89 | `.panel h2,.settingsCard h2` | `font-size: calc(14px * var(--fs-scale));` |
| 98 | `.liveClock time` | `font-size: calc(26px * var(--fs-scale));` |
| 116 | `.overviewPanelHeader h2` | `font-size: calc(12px * var(--fs-scale));` |
| 120 | `.overviewAvatar` | `font-size: calc(11px * var(--fs-scale));` |
| 144 | `.codeArea` | `font-size: calc(11px * var(--fs-scale));` |
| 145 | `.entityCard h2,.projectCard h2` | `font-size: calc(14px * var(--fs-scale));` |
| 148 | `.dialog > header h2` | `font-size: calc(16px * var(--fs-scale));` |
| 156 | `.projectHeader > div h1` | `font-size: calc(22px * var(--fs-scale));` |
| 164 | `.detailHeader h2` | `font-size: calc(16px * var(--fs-scale));` |
| 166 | `.modelCard h2` | `font-size: calc(15px * var(--fs-scale));` |
| 171 | `.meetingRoomHeader h2` | `font-size: calc(15px * var(--fs-scale));` |

### `frontend/src/pages/login/LoginPage.module.css` (9 chỗ)

| Dòng | Selector | Thêm vào |
|---|---|---|
| 40 | `.wordmark` | `font-size: calc(20px * var(--fs-scale));` |
| 46 | `.eyebrow-tag` | `font-size: calc(11px * var(--fs-scale));` |
| 65 | `.card-name` | `font-size: calc(15px * var(--fs-scale));` |
| 69 | `.badge-cyan, .badge-purple` | `font-size: calc(10px * var(--fs-scale));` |
| 99 | `.form-eyebrow` | `font-size: calc(10px * var(--fs-scale));` |
| 102 | `.form-title` | `font-size: calc(28px * var(--fs-scale));` |
| 108 | `.field-label` | `font-size: calc(11px * var(--fs-scale));` |
| 115 | `.field-input` | `font-size: calc(14px * var(--fs-scale));` |
| 135 | `.submit-btn` | `font-size: calc(14px * var(--fs-scale));` |

### `frontend/src/pages/taskrunner/TaskrunnerPage.module.css` (2 chỗ)

| Dòng | Selector | Thêm vào |
|---|---|---|
| 716 | `.output-content` | `font-size: calc(12px * var(--fs-scale));` |
| 721 | `.editor-title-input` | `font-size: calc(15px * var(--fs-scale));` |

## 3.4. Hai chỗ CỐ Ý BỎ QUA — không đụng vào

| Vị trí | Nội dung | Lý do |
|---|---|---|
| `HubPage.module.css:83` | `.pageHeader h1 { font: 700 clamp(24px,3vw,32px)/1.15 ... }` | Đã co giãn theo viewport bằng `clamp()`. Nhân thêm 1.15 làm tiêu đề trang tràn ở màn hẹp. Ở 32px so với thân bài 16.1px, tỉ lệ vẫn 2:1 — dư sức. **Đây là ngoại lệ có chủ ý, ghi lại trong commit.** |
| `HubPage.module.css:146` | `.avatar { font:700 calc(18px * var(--fs-scale)) ... }` | **Đã đúng rồi.** Đây là mẫu tham chiếu. Đừng thêm `font-size` lần nữa. |

## 3.5. Kiểm chứng

```bash
cd frontend

# 1. Đếm số shorthand `font:` còn chứa px thô. TRƯỚC: 25. SAU KỲ VỌNG: 25 (không xoá cái nào).
grep -roE 'font:\s*[^;]*[0-9]+px[^;]*' --include=*.css src/ | wc -l

# 2. Đếm khai báo font-size đã token hoá. TRƯỚC: 259. SAU KỲ VỌNG: 282 (259 + 23).
#    CHÚ Ý regex: phải là [0-9.]+ chứ không phải [0-9]+. Có 28 chỗ dùng px thập phân
#    (12.5px, 14.5px, 10.5px trong TaskrunnerPage); regex chỉ nhận số nguyên sẽ đếm
#    thiếu và làm bạn tưởng còn nhiều việc chưa làm.
grep -roE 'font-size:[^;]*var\(--fs-scale\)' --include=*.css src/ | wc -l

# 3. Không được sinh ra font-size px thô nào. KỲ VỌNG: 0.
grep -roE 'font-size:\s*[0-9.]+px' --include=*.css src/ | wc -l

npm run typecheck && npm run build
```

## 3.6. Kiểm chứng mắt

Mở `/hub/model` (trang Bộ não AI, nhiều `.panel h2`) và `/login`.
Tiêu đề panel phải **rõ ràng to hơn** chữ thân bài bên dưới nó.

Thử đổi `--fs-scale` trong `theme.css` thành `1.5` rồi tải lại: **mọi** chữ phải to lên
đều nhau, kể cả tiêu đề panel và tiêu đề dialog. Chỉ `.pageHeader h1` giữ nguyên
(ngoại lệ đã ghi ở 3.4). **Nhớ trả `--fs-scale` về `1.15` trước khi commit.**

## 3.7. CHỐT PHASE 3

```
style(ui): 23 khai báo font: shorthand nay theo --fs-scale

259 khai báo cỡ chữ đã token hoá, nhưng 25 cái viết bằng shorthand `font:` thì
cỡ chữ nằm giữa chuỗi nên không nhân được. Hệ quả đo được: chữ thân bài
14px × 1.15 = 16.1px, còn `.panel h2` vẫn đúng 14px — tiêu đề nhỏ hơn nội dung
nó đặt tên. Toàn bộ thang phân cấp chữ bị nén.

Giữ nguyên shorthand và thêm font-size riêng ngay sau nó: chỉ đè phần cỡ chữ,
giữ nguyên weight/line-height/family. Mọi line-height ở đây đều không đơn vị
nên tự giãn theo.

Chừa .pageHeader h1 — nó đã dùng clamp() co theo viewport, nhân thêm 1.15 sẽ
tràn ở màn hẹp; 32px so với thân bài 16.1px vẫn là tỉ lệ 2:1.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 4 — Chữ trắng trên nền màu (tương phản)

## 4.1. Bối cảnh

`theme.css` dòng 36-40 ghi rõ:

```
Màu chữ ĐẶT TRÊN nền accent. Ở theme tối, accent là xanh sáng nên chữ trắng
chỉ đạt 1.83:1 — không đọc nổi. Chữ gần đen đạt 10.2:1.
Đừng hardcode `color:white` cho nút chính; dùng token này.
```

Commit `1ebe071` tuyên bố đã sửa, nhưng chỉ sửa `.primaryButton` của Hub.
Quét lại bằng parser đa dòng: **còn 11 chỗ**.

Tương phản đo theo công thức WCAG:

| Nền | Chữ trắng, theme Tối | Chữ trắng, theme Sáng |
|---|---|---|
| `--accent` / `--cyan` | **1.83:1** ✗ | 4.58:1 ✓ |
| `--danger` / `--red` | **2.88:1** ✗ | 4.9:1 ✓ |
| `--info` / `--blue` | **2.79:1** ✗ | 5.14:1 ✓ |

Ngưỡng WCAG AA cho chữ thường là 4.5:1.

## 4.2. Bước 4.2.a — Thêm token `--on-info` vào theme.css

`--on-accent` và `--on-danger` đã có. Thiếu `--on-info`. Thêm vào:

- Trong khối `:root` (cạnh `--on-danger`, dòng ~43):
  ```css
  /* Chữ trắng trên nút xanh dương tối chỉ 2.79:1; gần-đen đạt trên 7:1 */
  --on-info: #06121f;
  ```
- Trong khối `body.light` (cạnh `--on-danger`, dòng ~102):
  ```css
  --on-info: #ffffff;
  ```

## 4.3. Bước 4.3.a — Sửa đúng 11 chỗ

Với mỗi dòng dưới đây, **chỉ đổi giá trị của `color`**, không đụng gì khác trong luật:

### `frontend/src/pages/hub/HubPage.module.css`

| Dòng | Selector | Nền | `color` từ | `color` thành |
|---|---|---|---|---|
| 173 | `.userMessage > div` | `var(--accent)` | `white` | `var(--on-accent)` |

### `frontend/src/pages/login/LoginPage.module.css`

| Dòng | Selector | Nền | từ | thành |
|---|---|---|---|---|
| 131-135 | `.submit-btn` | `var(--accent)` | `#fff` | `var(--on-accent)` |
| 140-141 | `.spinner` | — | `rgba(255,255,255,.35)` và `#fff` | xem dưới |

> **Ngoại lệ sau Phase 4 (quyết định người dùng 2026-08-13):** dòng `.submit-btn`
> trong bảng trên đã được đổi lại thành `#fff`; không áp lại `var(--on-accent)`. Xem mục 0.3.

`.spinner` đã xác nhận nằm **bên trong** `.submit-btn` (`LoginPage.tsx:209`, hiện lúc
`loading`). Nó có **hai** giá trị trắng, phải đổi **cả hai**:

```css
/* TRƯỚC */
.spinner { width:16px; height:16px; border: 2px solid rgba(255,255,255,.35); border-top-color: #fff; ... }
/* SAU   */
.spinner { width:16px; height:16px; border: 2px solid color-mix(in srgb, var(--on-accent) 35%, transparent); border-top-color: var(--on-accent); ... }
```

### `frontend/src/pages/taskrunner/TaskrunnerPage.module.css`

| Dòng | Selector | Nền | từ | thành |
|---|---|---|---|---|
| 196 | `.editor-btn.primary` | `var(--blue)` | `#fff` | `var(--on-info)` |
| 346 | `.modal-btn.danger` | `var(--red)` | `#fff` | `var(--on-danger)` |
| 348 | `.modal-btn.primary` | `var(--cyan)` | `#fff` | `var(--on-accent)` |

### `frontend/src/pages/workspace/WorkspacePage.module.css`

| Dòng | Selector | Nền | từ | thành |
|---|---|---|---|---|
| 140 | `.btn-new` | `var(--cyan)` | `#fff` | `var(--on-accent)` |
| 262 | `.msg-user .msg-avatar` | `var(--accent)` | `#fff` | `var(--on-accent)` |
| 392 | `.btn-send` | `var(--cyan)` | `#fff` | `var(--on-accent)` |
| 611 | `.fp-btn-submit` | `var(--cyan)` | `#fff` | `var(--on-accent)` |
| 790 | `.btn-create` | `var(--cyan)` | `#fff` | `var(--on-accent)` |

### Chỗ thứ 11 — `.cp-btn-confirm` (dòng 669), xử lý khác

```css
.cp-btn-confirm { padding: 8px 20px; background: #ef4444; ...; color: #fff; ... }
```

Nền ở đây là hex thô `#ef4444` (đỏ Tailwind), không phải token. Đổi **cả hai**:

```css
background: var(--danger);
color: var(--on-danger);
```

Cùng lúc, hai chỗ dùng `#ef4444` khác trong file này cũng đổi sang `var(--danger)`:
- dòng 646 `.cp-title` → `color: var(--danger)`
- dòng 718 `.btn-delete-session` → `color: var(--danger)`

## 4.4. Bước 4.4.a — Thống nhất trong Taskrunner

Chú ý mâu thuẫn nội bộ: `.wf-btn.primary` (dòng 136) và `:global(#add-workflow-btn)`
(dòng 144) đang dùng `color:#04141a` — **đúng ý đồ** nhưng ghi cứng. Đổi cả hai
thành `var(--on-accent)` để cùng một nguồn. (Ở theme tối `--on-accent` là `#08120f`,
gần như y hệt `#04141a` — thay đổi hình ảnh gần bằng không, mục đích là gom về một mối.)

## 4.5. Không được làm

- **Không** đổi `#fff` ở nhóm sidebar, ô xem trước theme, icon node, hay chữ nút đăng nhập —
  xem **mục 0.3**. Đó là 4 nhóm bất khả xâm phạm.
- **Không** đổi giá trị của `--accent`, `--danger` hay bất kỳ màu nền nào.
  Phase này chỉ đổi **màu chữ đặt trên** nền.

## 4.6. Kiểm chứng

```bash
cd frontend

# Quét lại đúng bằng script đã dùng khi khảo sát.
# KỲ VỌNG: chỉ còn các dòng thuộc 4 nhóm miễn trừ ở mục 0.3. Riêng .submit-btn
# của LoginPage có nền var(--accent) là ngoại lệ có chủ ý; phải BỎ QUA, không sửa về token.
python - <<'PY'
import re, os
pat = re.compile(r'([^{}]*)\{([^{}]*)\}', re.S)
bg  = re.compile(r'background(-color)?:\s*(var\(--[a-z-]+\)|#[0-9a-fA-F]{3,6})')
wht = re.compile(r'color:\s*(#fff\b|#ffffff\b|white\b)')
for root, _, fs in os.walk('src'):
    for f in sorted(fs):
        if not f.endswith('.css'): continue
        p = os.path.join(root, f); s = open(p, encoding='utf-8').read()
        for m in pat.finditer(s):
            sel, body = m.group(1), m.group(2)
            a = bg.search(body)
            if a and wht.search(body):
                print(f'{p}:{s[:m.start()].count(chr(10))+1} | {sel.strip().splitlines()[-1][:44]} | bg={a.group(2)}')
PY

# --on-info đã khai ở cả hai theme. KỲ VỌNG: đúng 2 dòng.
grep -n -- '--on-info' src/styles/theme.css

npm run typecheck && npm run build
```

## 4.7. Kiểm chứng mắt — **ưu tiên theme TỐI**, đây là nơi lỗi nằm

| Trang | Xem gì |
|---|---|
| `/login` | Nút "Đăng nhập" — chữ trắng trên nền xanh ở cả theme Tối lẫn Sáng (ngoại lệ mục 0.3). Bấm vào xem vòng xoay có thấy không. |
| `/hub/meeting` | Gõ một tin nhắn — bong bóng của bạn (bên phải, nền xanh) phải đọc được rõ. |
| `/hub/train` | Nút `+` tạo phiên, nút gửi, avatar chữ "P" của bạn trong chat. |
| `/hub/company-runner` | Mở một quy trình → nút "Lưu"; mở dialog → nút chính và nút xoá. |

Chụp màn hình `/hub/meeting` ở theme Tối **trước và sau** để đối chiếu.

## 4.8. CHỐT PHASE 4

```
fix(a11y): 11 chỗ chữ trắng trên nền màu, đo theo WCAG

theme.css đã khai --on-accent/--on-danger và ghi rõ "đừng hardcode color:white",
nhưng 1ebe071 chỉ áp cho .primaryButton của Hub. Quét lại bằng parser đa dòng
(grep một dòng bỏ sót các luật xuống dòng) tìm thấy 11 chỗ còn lại.

Ở theme tối: trắng trên accent 1.83:1, trên danger 2.88:1, trên info 2.79:1 —
đều dưới ngưỡng AA 4.5:1. Thêm token --on-info cho trường hợp thứ ba.

.cp-btn-confirm dùng nền #ef4444 ghi cứng thay vì token; gom nó cùng hai chỗ
#ef4444 khác trong file về var(--danger).

Taskrunner có .wf-btn.primary dùng #04141a đúng ý đồ còn .modal-btn.primary
dùng #fff — cùng một loại nút, hai cách xử lý. Nay cả hai dùng --on-accent.

Tại thời điểm chốt Phase 4, chừa nguyên ba nhóm cố ý ghi cứng: chữ trong sidebar
(sidebar luôn nền tối ở cả hai theme), ô xem trước theme trong Cài đặt, và icon
trên node của trình soạn quy trình. Ngày 2026-08-13, người dùng thêm `.submit-btn`
của LoginPage thành nhóm miễn trừ thứ tư; xem mục 0.3 và không sửa nó về token.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 5 — Dọn bảng màu nâu-kem còn sót

## 5.1. Bối cảnh

`theme.css` ánh xạ 49 tên token cũ về token chuẩn, nên các trang cũ đổi màu mà không
phải sửa CSS bố cục. Nhưng chỗ nào **ghi thẳng mã hex** thì lớp ánh xạ không với tới.

Bốn màu của bảng nâu-kem cũ còn nằm rải rác trong `HubPage.module.css`. Ở theme Sáng
chúng gần như không đọc được:

| Hex | Vai trò | Tương phản trên nền sáng `#fffefa` |
|---|---|---|
| `#5fc996` | xanh "thành công" | ~2.0:1 ✗ |
| `#e0b265` | vàng "chờ duyệt" | ~1.9:1 ✗ |
| `#6fa8d6` | xanh dương "đang chạy" | ~2.6:1 ✗ |
| `#5da9db`, `#9b8ad8` | tông thẻ chỉ số | không đổi theo theme |

## 5.2. Bảng thay thế

Áp dụng cho **`frontend/src/pages/hub/HubPage.module.css`**:

| Hex cũ | Thay bằng | Dùng cho `rgba()` |
|---|---|---|
| `#5fc996` | `var(--accent)` | `rgba(var(--accent-rgb), <alpha>)` |
| `#e0b265` | `var(--warning)` | `rgba(var(--warning-rgb), <alpha>)` |
| `#6fa8d6` | `var(--info)` | `rgba(var(--info-rgb), <alpha>)` |
| `#5da9db` | `var(--info)` | `rgba(var(--info-rgb), <alpha>)` |
| `#9b8ad8` | `var(--purple-tone)` | `rgba(var(--purple-rgb-base), <alpha>)` |
| `#d8eee0` / `#35795a` (`.overviewAvatar`) | `var(--accentSoft)` / `var(--accent)` | — |

**Về `rgba()`:** không truyền được hex qua `var()`. `theme.css` đã khai sẵn bộ ba RGB
cho đúng việc này. Ví dụ chuyển đổi:

```css
/* TRƯỚC */ .running { background: #6fa8d6; box-shadow: 0 0 0 4px rgba(111,168,214,.12); }
/* SAU   */ .running { background: var(--info); box-shadow: 0 0 0 4px rgba(var(--info-rgb),.12); }
```

**Giữ nguyên trị số alpha.** Chỉ đổi phần màu.

## 5.3. Danh sách đầy đủ các luật phải sửa

Tất cả trong `HubPage.module.css`:

| Dòng | Selector | Hex hiện có |
|---|---|---|
| 90 | `.statusDot` | `#e0b265` |
| 91 | `.completed` | `#5fc996` |
| 91 | `.running` | `#6fa8d6` + `rgba(111,168,214,.12)` |
| 105 | `.statTone-blue .overviewStatIcon` | `#5da9db` + `rgba(93,169,219,.13)` |
| 105 | `.statTone-violet .overviewStatIcon` | `#9b8ad8` + `rgba(155,138,216,.13)` |
| 119 | `.overviewAvatar` | `#d8eee0`, `#35795a` |
| 123 | `.ready` | `#52d6a0` → `var(--accent)` |
| 126 | `.activityMarker.running` | `#5da9db` |
| 126 | `.conversationMarker` | `#9b8ad8` |
| 140 | `.modalCard > svg` | `#e0b265` |
| 141 | `.toast.success svg` | `#5fc996` |
| 141 | `.toast.info svg` | `#6fa8d6` |
| 146 | `.onBadge,.offBadge` | `#5fc996` + `rgba(95,201,150,.14)` + `rgba(217,105,92,.14)` |
| 155 | `.connectionOk,.connectionFail` | `#5fc996` |
| 159 | `.status_completed,.status_approved` | `#5fc996` + `rgba(...,.12)` |
| 159 | `.status_waiting_review,.status_needs_revision` | `#e0b265` |
| 159 | `.status_in_progress` | `#6fa8d6` |
| 164 | `.progressRunning,.progressDone` | `#6fa8d6` |
| 164 | `.progressDone` | `#5fc996` |
| 164 | `.results > article > svg` | `#e0b265` |
| 171 | `.meetingConnected i` | `#5fc996` |
| 173 | `.systemMessage > strong` + `> div` | `#e0b265` + `rgba(224,178,101,.08)` |
| 173 | `.workflowProgress` | `#6fa8d6` + `rgba(111,168,214,.08)` |
| 174 | `.busyDot` | `#6fa8d6` |
| 176 | `.approvalCard` + `> header` | `#e0b265` + `rgba(224,178,101,.5)` + `rgba(224,178,101,.07)` |
| 176 | `.resolvedCard` | `#5fc996` |
| 4 | `:global(...:focus-visible)` | `#52d6a0` → `var(--accent)` |
| 5, 26 | `.hubRoot` `--accentStrong` / `--accentSoft` | xem 5.4 dưới |

### 5.4. Xử lý `--accentStrong` / `--accentSoft`

```css
.hubRoot { --accentStrong: #6be1b0; --accentSoft: rgba(82,214,160,.13); }
:global(body.light) .hubRoot { --accentStrong: #246f54; --accentSoft: #dceee5; }
```

`theme.css` đã có `--accent-strong` (`#6fe6b5` tối / `#237454` sáng) — **gần nhưng không
bằng** hai giá trị trên. Đây là hai hệ token song song cho cùng một khái niệm.

Đổi thành:

```css
.hubRoot { --accentStrong: var(--accent-strong); --accentSoft: color-mix(in srgb, var(--accent) 13%, transparent); }
```

và **xoá hẳn** khối `:global(body.light) .hubRoot` nếu sau khi sửa nó rỗng — vì
`--accent-strong` đã tự đổi theo theme rồi. Kiểm bằng mắt: sắc xanh hover có lệch không.
Nếu thấy lệch rõ thì báo lại thay vì tự chỉnh số.

## 5.5. Không được làm

- **Không** đụng nhóm sidebar (mục 0.3) — kể cả `#52d6a0` trong `.brand > span`,
  `.navActive`, `.sidebarHealth > span i`, `.online i,.offline i`, `.liveClock > span i`.
  Chúng nằm trên nền tối cố định.
- **Không** đụng `.themePreviewLight` / `.themePreviewDark`.
- **Không** đổi trị số alpha trong `rgba()`.
- **Không** động vào `.failed`, `.status_failed` — chúng **đã** dùng `var(--danger)`.

## 5.6. Kiểm chứng

```bash
cd frontend

# KỲ VỌNG: 0 (TRƯỚC khi sửa là 26). Các màu nâu-kem biến mất hoàn toàn khỏi HubPage.
# LƯU Ý: đừng nhắc lại mã hex cũ trong chú thích bạn viết thêm — grep này không
# phân biệt code với chú thích, viết "#5fc996" trong comment sẽ làm nó khác 0.
# Muốn ghi lại thì viết bằng chữ ("xanh thành công của bảng nâu-kem cũ").
grep -c '#5fc996\|#e0b265\|#6fa8d6\|#5da9db\|#9b8ad8\|#d8eee0\|#35795a' src/pages/hub/HubPage.module.css

# KỲ VỌNG: chỉ còn hex thuộc nhóm miễn trừ ở mục 0.3. Đối chiếu từng dòng.
grep -oE '#[0-9a-fA-F]{3,8}\b' src/pages/hub/HubPage.module.css | sort | uniq -c | sort -rn

# KỲ VỌNG: không còn rgba() với số nguyên thô cho các màu vừa đổi.
grep -c 'rgba(111,168,214\|rgba(95,201,150\|rgba(224,178,101\|rgba(93,169,219\|rgba(155,138,216' src/pages/hub/HubPage.module.css

npm run typecheck && npm run build
```

## 5.7. Kiểm chứng mắt — **ưu tiên theme SÁNG**, đây là nơi lỗi nằm

| Trang | Xem gì |
|---|---|
| `/hub` | Bốn thẻ chỉ số — icon xanh dương và tím phải đúng tông với phần còn lại. |
| `/hub/meeting` | Các ô "Hệ thống" (trước là màu kem nâu) nay phải hoà vào bảng màu chung. Thẻ chờ duyệt phải đọc được. |
| `/hub/tasks` | Các huy hiệu trạng thái: `status_completed`, `status_waiting_review`, `status_in_progress`. |
| `/hub/company-runner` | Ô tiến độ chạy quy trình. |

Chụp `/hub/meeting` ở theme **Sáng**, trước và sau.

## 5.8. CHỐT PHASE 5

```
style(ui): dọn nốt bảng màu nâu-kem trong HubPage

theme.css ánh xạ 49 token cũ về token chuẩn, nhưng chỗ nào ghi thẳng mã hex thì
lớp ánh xạ không với tới. Còn sót 4 màu của bảng cũ: #5fc996 (xanh thành công),
#e0b265 (vàng chờ duyệt), #6fa8d6 (xanh đang chạy), #5da9db/#9b8ad8 (tông thẻ).

Trên nền sáng #fffefa chúng đạt lần lượt ~2.0:1, ~1.9:1, ~2.6:1 — các ô "Hệ
thống" màu kem trong Phòng họp là từ đây. Thay bằng --accent/--warning/--info/
--purple-tone, và các rgba() dùng bộ ba RGB mà theme.css đã khai sẵn cho đúng
việc này. Trị số alpha giữ nguyên.

Gộp --accentStrong/--accentSoft (hệ token song song của .hubRoot) về
--accent-strong của theme.css.

Chừa nguyên nhóm màu trong sidebar và ô xem trước theme — sidebar luôn nền tối
ở cả hai theme nên chữ ở đó phải cố định sáng.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 6 — Biểu đồ trang Chi phí

## 6.1. Bối cảnh

`frontend/src/pages/hub/CostPage.tsx` dòng 53-54:

```js
borderColor: "#5b8f7f", backgroundColor: "rgba(91,143,127,.18)"
backgroundColor: ["#5b8f7f", "#a78bfa", "#e0935a", "#6fa8d6", "#d9695c", "#e0b265"]
```

`#5b8f7f` chính là `--accent` của bảng nâu-kem đã khai tử. Nặng hơn: trang này
**không truyền màu trục và nhãn** cho Chart.js, nên tick và grid dùng mặc định `#666` —
gần như vô hình trên nền tối `#0b1412`.

`OverviewPage.tsx` dòng 180-208 làm **đúng**: có nhánh `theme === "dark"` cho tooltip,
tick và grid. Đó là mẫu để làm theo.

## 6.2. Việc phải làm

### Bước 6.2.a — Nhập `useTheme`

`CostPage.tsx` hiện chưa nhập. Thêm, khớp cách `OverviewPage.tsx` đang làm:

```ts
import { useTheme } from "../../store/theme";
```

và trong component: `const { theme } = useTheme();`

### Bước 6.2.b — Bảng màu theo theme

Thay hai dòng 53-54. Bảng 6 màu phải lấy từ token đang có trong `theme.css`,
mỗi màu hai biến thể:

| Vị trí | Theme Tối | Theme Sáng | Token nguồn |
|---|---|---|---|
| 1 | `#52d6a0` | `#2c8462` | `--accent` |
| 2 | `#a78bfa` | `#7c5cd6` | `--purple-tone` |
| 3 | `#d7a95e` | `#ad7628` | `--warning` |
| 4 | `#5b9df0` | `#2f6fb8` | `--info` |
| 5 | `#e27b6f` | `#bd5048` | `--danger` |
| 6 | `#6fe6b5` | `#237454` | `--accent-strong` |

Đường xu hướng (`trendData`) dùng vị trí 1; nền tô dùng `rgba` của cùng màu với
alpha `.18` giữ nguyên.

> **Vì sao chép giá trị vào JS chứ không đọc `var()`:** Chart.js vẽ lên canvas,
> không hiểu CSS custom property. `OverviewPage.tsx` cũng chép giá trị — làm theo cho
> nhất quán. **Ghi chú ngay tại chỗ** rằng nếu đổi màu trong `theme.css` thì phải đổi
> cả ở đây.

### Bước 6.2.c — Cấu hình trục và tooltip

Cả hai biểu đồ hiện dùng `options={{ responsive: true, maintainAspectRatio: false }}`.
Thay bằng một object `chartOptions` tạo bằng `useMemo` phụ thuộc `[theme]`, **sao y
cấu trúc của `OverviewPage.tsx:180-208`**, gồm:

- `plugins.tooltip.backgroundColor` — tối `#172723`, sáng `#173b30`
- `scales.x.ticks.color` và `scales.y.ticks.color`
- `scales.y.grid.color`

### Bước 6.2.d — Sửa luôn một lỗi tương phản trong OverviewPage

`OverviewPage.tsx` dòng 197 và 203 dùng `#66746e` cho nhãn trục ở theme Sáng.
`theme.css` dòng 88 ghi chú rõ giá trị này **đã bị loại** vì chỉ đạt 4.47:1:

```
/* #66746e chỉ đạt 4.47:1 trên nền sáng — sát ngưỡng. Đậm thêm một nấc → 4.96:1 */
--muted: #5f6d67;
```

Đổi cả hai chỗ `#66746e` → `#5f6d67`.

### Bước 6.2.e — Biểu đồ tròn cần viền

Doughnut không có viền, các lát cạnh nhau dính vào nhau. Thêm vào `modelData.datasets[0]`:

```js
borderColor: theme === "dark" ? "#111d1a" : "#fffefa",   // = var(--surface)
borderWidth: 2,
```

## 6.3. Không được làm

- **Không** đổi logic tính `buckets`, `byModel`, `trendData.labels`, hay bất cứ gì
  liên quan tới số liệu. Phase này **chỉ đụng màu và cấu hình hiển thị**.
- **Không** đổi đường dẫn export `.xlsx`.
- **Không** đổi `formatDate` hay `money`.

## 6.4. Kiểm chứng

```bash
cd frontend

# KỲ VỌNG: 0. Màu accent của bảng nâu-kem phải biến mất.
grep -c '#5b8f7f\|#e0935a\|#d9695c' src/pages/hub/CostPage.tsx

# KỲ VỌNG: không in ra gì. Giá trị --muted đã bị loại không còn ở đâu.
grep -rn '#66746e' src/

# KỲ VỌNG: CostPage nay có nhánh theme, giống OverviewPage.
grep -c 'theme === "dark"' src/pages/hub/CostPage.tsx

npm run typecheck && npm run build
```

## 6.5. Kiểm chứng mắt

`/hub/cost` ở **cả hai theme**. Phải đọc được: nhãn trục X (ngày), nhãn trục Y (số tiền),
đường lưới ngang. Rê chuột lên điểm dữ liệu — tooltip phải có nền đục, đọc được.
Các lát của biểu đồ tròn phải tách nhau rõ.

So sánh cạnh nhau với `/hub` (Tổng quan) — hai biểu đồ phải trông cùng một hệ.

## 6.6. CHỐT PHASE 6

```
fix(ui): biểu đồ Chi phí theo theme, thôi dùng bảng màu đã khai tử

CostPage ghi cứng #5b8f7f — chính là --accent của bảng nâu-kem đã bỏ — và
không truyền màu trục/nhãn cho Chart.js, nên tick và grid dùng mặc định #666,
gần như vô hình trên nền tối #0b1412.

Làm theo đúng cách OverviewPage đã làm: bảng 6 màu có nhánh sáng/tối lấy từ
token của theme.css, cộng cấu hình tooltip/tick/grid theo theme. Giá trị chép
vào JS chứ không đọc var() vì Chart.js vẽ lên canvas, không hiểu custom
property — có ghi chú tại chỗ để đổi màu thì đổi cả hai nơi.

Kèm theo: OverviewPage dùng #66746e cho nhãn trục ở theme sáng, đúng giá trị
mà theme.css ghi chú là đã loại vì chỉ đạt 4.47:1 — đổi sang #5f6d67 (4.96:1).
Doughnut thêm viền màu nền để các lát không dính vào nhau.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 7 — Bong bóng chat Phòng họp

## 7.1. Bối cảnh

Hai nơi cùng render bằng component `<Markdown>` (`src/components/Markdown.tsx`):

| Nơi | Luật định dạng |
|---|---|
| Dạy AI — `.msg-bubble` (`WorkspacePage.module.css:287-326, 908`) | **20 luật**: `p code pre ul ol li strong em a h1-h6 blockquote hr table th td img` |
| Phòng họp — `.meetingMessage > div` (`HubPage.module.css:173`) | **0 luật** (chỉ `font-size` + `overflow-wrap`) |

Nên bảng, khối code, danh sách và **ảnh** trong tin nhắn Phòng họp không bị chặn kích
thước. `WorkspacePage.module.css:906` ghi rõ lý do phải chặn:

```
/* Ảnh học viên vẽ thử ngay trong buổi học. Ảnh gốc 1080x1350 nên không chặn lại
   là nó đẩy phồng cả khung chat. */
```

Phòng họp cũng nhận đúng loại ảnh đó (`MeetingsPage.tsx:469, 665, 888`) mà chưa có cái chặn.

## 7.2. Việc phải làm

Thêm vào `HubPage.module.css`, **ngay sau** luật `.meetingMessage > div,.agentMessage > div`
hiện có (dòng ~173), một khối luật mới. Selector phải phủ cả ba loại bong bóng
(`.meetingMessage`, `.agentMessage`, `.systemMessage`) **và** khối biên bản
(`.minutesText`, dùng ở `MeetingsPage.tsx:888`).

Đặt tiền tố chung, ví dụ:

```css
.meetingMessage > div,.agentMessage > div,.minutesText { /* ...các luật con... */ }
```

Danh sách luật con phải **đối chiếu 1-1** với `.msg-bubble` của WorkspacePage
(dòng 287-326 và 908-919). Chuyển sang token của Hub:

| Ở WorkspacePage | Ở HubPage |
|---|---|
| `var(--cyan)` | `var(--accent)` |
| `var(--bg3)` | `var(--surface3)` |
| `var(--border)` | `var(--border)` (như cũ) |
| `var(--muted)` | `var(--muted)` (như cũ) |
| `var(--text)` | `var(--text)` (như cũ) |

**Bắt buộc phải có, không được bỏ sót:**

```css
img  { max-width: min(360px, 100%); height: auto; border-radius: 10px; border: 1px solid var(--border); margin-top: 8px; display: block; }
pre  { overflow-x: auto; }          /* thiếu cái này là khối code đẩy phồng bong bóng */
table{ display: block; overflow-x: auto; max-width: 100%; border-collapse: collapse; }
```

Cỡ chữ trong các luật con dùng `calc(<px> * var(--fs-scale))` — Phase 3 đã đặt quy tắc này.

## 7.3. Không được làm

- **Không** sửa `src/components/Markdown.tsx`. Phase này thuần CSS.
- **Không** đổi `.msg-bubble` của WorkspacePage. Nó đang đúng; nó là bản mẫu.
- **Không** gom hai bộ luật thành một file dùng chung. Nghe hợp lý nhưng chúng là hai
  CSS module riêng biệt và việc gộp cần đổi kiến trúc — **ngoài phạm vi**. Nếu thấy
  đáng làm thì đề xuất riêng, đừng tự làm.
- **Không** thêm `overflow: hidden` cho bong bóng — nó sẽ cắt cụt tooltip và menu.

## 7.4. Kiểm chứng

```bash
cd frontend

# Bốn phần tử bắt buộc phải có luật trong khối bong bóng phòng họp.
# KỲ VỌNG: mỗi lệnh in ra ít nhất 1 dòng. Cách viết selector có thể khác nhau
# (dấu cách quanh `>`, gộp hay tách luật) nên ĐỌC output chứ đừng so con số.
grep -n 'meetingMessage[^{]*img'   src/pages/hub/HubPage.module.css
grep -n 'meetingMessage[^{]*pre'   src/pages/hub/HubPage.module.css
grep -n 'meetingMessage[^{]*table' src/pages/hub/HubPage.module.css
grep -n 'meetingMessage[^{]*code'  src/pages/hub/HubPage.module.css

# Nếu bạn viết luật con dạng lồng (`.meetingMessage > div { img {...} }`) thì các
# lệnh trên không bắt được — khi đó dán tay khối luật vừa thêm ra để người duyệt xem.

npm run typecheck && npm run build
```

## 7.5. Kiểm chứng mắt

Vào `/hub/meeting`, tạo cuộc họp, gửi tin nhắn chứa lần lượt:

1. Một bảng markdown 4 cột — phải cuộn ngang **trong** bong bóng, không đẩy phồng khung.
2. Một khối ```` ``` ```` code có dòng dài — phải cuộn ngang trong bong bóng.
3. Một danh sách gạch đầu dòng — phải có thụt lề, không dính sát mép.
4. Một ảnh (nhờ nhân viên tạo ảnh, hoặc dán markdown `![](url)`) — phải giới hạn 360px.

Đối chiếu với cùng bốn thứ đó ở `/hub/train` — hai khung chat phải trông như nhau.

## 7.6. CHỐT PHASE 7

```
feat(ui): bong bóng chat Phòng họp có định dạng markdown

Cả Phòng họp và Dạy AI cùng render bằng component <Markdown>, nhưng
.msg-bubble của Dạy AI có 20 luật cho p/code/pre/ul/table/img... còn
.meetingMessage của Phòng họp chỉ có font-size và overflow-wrap.

Hệ quả: bảng, khối code và ảnh trong tin nhắn Phòng họp không bị chặn kích
thước. WorkspacePage đã ghi rõ lý do phải chặn ("ảnh gốc 1080x1350 nên không
chặn lại là nó đẩy phồng cả khung chat") — Phòng họp nhận đúng loại ảnh đó.

Chép bộ luật sang, đổi token cho khớp hệ của Hub, phủ cả ba loại bong bóng và
khối biên bản. pre và table bắt buộc có overflow-x:auto.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 8 — Nhất quán đầu trang theo loại trang + dọn CSS chết

## 8.1. Phần A — Nguyên tắc đầu trang theo loại trang

Không ép cả 12 tab dùng cùng một `<h1>`. Hai loại trang có nhu cầu không gian khác
nhau và phải nhất quán trong chính loại của chúng:

| Loại trang | Tab | Nguyên tắc |
|---|---|---|
| Trang tài liệu/dashboard cuộn | Tổng quan, Nhân sự, Kỹ năng, Dự án, Bộ não AI, Chi phí, Tài sản, Cài đặt | Giữ nguyên hệ đầu trang theo ngữ cảnh nội dung; không xoá các `<h1>` đang có |
| Workspace lấp đầy màn hình | Phòng họp, Dạy AI, Quy trình, Tác vụ tự động | Không có `<h1>`/`.pageHeader` của Hub; dành chiều cao cho nội dung thao tác |

Sau Phase 2-TER, bốn workspace đều không có page header. Sidebar đã chỉ rõ tab đang
active, nên lặp lại tên tab không đem thêm ngữ cảnh đủ để bù chiều cao bị lấy mất.
Đặc biệt, chính cảnh báo cũ của Phase 8 đã xác nhận chèn header vào ba
`.tabPanelFull` sẽ ăn chiều cao phần nội dung; vì vậy bỏ hẳn hướng chèn header đó.

Trong nhóm cuộn, giữ các `<h1>` hiện có của Nhân sự, Kỹ năng, Dự án, Bộ não AI,
Chi phí, Tài sản và Cài đặt. Tổng quan tiếp tục dùng `.overviewHeader` gọn với đồng
hồ; Phase 8 **không** thêm `<h1>` vào đây. Mục tiêu của Phase 8 không còn là nâng số
đếm `<h1>`, mà là không làm header của loại trang này xâm lấn workspace.

### 8.1.a — Không được làm

- **Không** chèn `.pageHeader` vào `train` / `company-runner` / `auto-runner` trong
  `HubPage.tsx`.
- **Không** thêm `<h1>` vào `.overviewHeader`.
- **Không** bật lại topbar của WorkspacePage/TaskrunnerPage khi `embedded` — sẽ thành
  hai topbar chồng nhau.
- **Không** đổi `navigation[]` trong `HubPage.tsx`.
- **Không** thêm chuỗi tiếng Việt cứng vào JSX. Mọi chữ hiển thị đi qua `hubText()`
  hoặc nhánh `language === "vi" ? ... : ...` như code hiện có.

## 8.2. Phần B — Dọn CSS chết

### 8.2.a — 9 nhóm class chết trong `HubPage.module.css`

Đã đối chiếu: 0 tham chiếu trong mọi `.tsx`.

```
dashboardGrid   widePanel   statCard   statGrid   statIcon
statusDot       alertPanel  compactList  listRow
```

Đây là bộ thẻ chỉ số cũ, đã bị nhóm `overview*` thay thế mà quên dọn.

**Trước khi xoá, xác nhận lại từng cái:**

```bash
cd frontend
for n in dashboardGrid widePanel statCard statGrid statIcon statusDot alertPanel compactList listRow; do
  echo -n "$n: "; grep -rho "$n" --include=*.tsx src/ | wc -l
done
# KỲ VỌNG: tất cả bằng 0. Cái nào khác 0 thì GIỮ LẠI và báo.
```

Xoá cả các tham chiếu tới chúng **trong media query** (`.statGrid` và `.dashboardGrid`
xuất hiện trong cả khối 1000px lẫn 720px). Cẩn thận: `.statGrid,.costSummary{...}` —
chỉ bỏ `.statGrid`, **giữ** `.costSummary`.

> **Cảnh báo:** `.completed`, `.failed`, `.running`, `.status_*`, `.statTone-*` trông
> cũng như class chết vì chúng được ghép động (`c(`status_${x}`)`, `c(`statTone-${tone}`)`).
> **KHÔNG XOÁ.** Chúng khác với 9 cái trên.

### 8.2.b — 10 khối luật ID chết trong `TaskrunnerPage.module.css`

Trình soạn canvas tự viết đã được thay bằng React Flow. Các ID này không còn phần tử nào:

```
#editor-canvas  #canvas-viewport  #canvas-lines  #canvas-nodes  #toast-container
#zoom-controls  #zoom-select      #minimap       #minimap-content  #minimap-viewport
```

Xác nhận rồi mới xoá:

```bash
for id in editor-canvas canvas-viewport canvas-lines canvas-nodes toast-container zoom-controls zoom-select minimap minimap-content minimap-viewport; do
  echo -n "$id: "; grep -rl "id=\"$id\"" --include=*.tsx src/ 2>/dev/null | wc -l
done
# KỲ VỌNG: tất cả bằng 0.
```

**GIỮ LẠI** các ID còn dùng: `#topbar #page-wrap #grid-wrap #add-workflow-btn
#view-editor #editor-topbar #editor-body #node-palette #palette-categories
#canvas-wrap #node-inspector`.

Đặc biệt **giữ** khối `:global(#canvas-wrap) :global(.react-flow*)` (dòng 731-737) —
đó là phần tạo kiểu cho React Flow, đang có tác dụng.

### 8.2.c — `renderOutputContent` chết

`src/components/Markdown.tsx:19` được export nhưng không nơi nào gọi.
Xác nhận `grep -rn 'renderOutputContent' src/` chỉ ra đúng dòng định nghĩa, rồi xoá
cả hàm và hai hằng chỉ nó dùng (`IMAGE_PATH`, `IMAGE_MARKDOWN`) — **kiểm tra
`escapeHtml` có còn ai dùng không trước khi xoá nó**.

## 8.3. Kiểm chứng — bao gồm bài kiểm tra `c()`

```bash
cd frontend

# Không có tên class nào dùng trong TSX mà thiếu luật CSS.
# KỲ VỌNG: không in ra gì. (Đây là bài kiểm tra chống bẫy c() ở mục 0.6.)
cd src/pages/hub
grep -ohE 'c\("[a-zA-Z0-9_-]+"\)' *.tsx | sed -E 's/c\("([^"]+)"\)/\1/' | sort -u > /tmp/used.txt
grep -oE '\.[a-zA-Z][a-zA-Z0-9_-]*' HubPage.module.css | sed 's/^\.//' | sort -u > /tmp/have.txt
comm -23 /tmp/used.txt /tmp/have.txt
cd ../../..

npm run typecheck && npm run build
npm run verify:hub-integration
npm run verify:meeting-protocol
```

## 8.4. Kiểm chứng mắt

Đi hết 12 tab và kiểm theo loại trang:

- Bảy trang cuộn có `<h1>` hiện tại vẫn giữ đúng tiêu đề và phân cấp chữ; Tổng quan
  vẫn dùng header đồng hồ gọn, không bị chèn thêm `<h1>`.
- Bốn workspace `/hub/meeting`, `/hub/train`, `/hub/company-runner` và
  `/hub/auto-runner` không có `<h1>`/`.pageHeader` của Hub; nội dung bắt đầu cân mép
  và tận dụng đủ chiều cao còn lại.
- Chuyển qua lại giữa bốn workspace: không tab nào xuất hiện thêm một dải header làm
  nội dung bị nhảy xuống hoặc mất chiều cao.

Ở `/hub/train`: kiểm ô nhập tin nhắn ở đáy **vẫn thấy được**, không bị đẩy khỏi màn hình.
Ở `/hub/company-runner`: mở một quy trình, kiểm canvas React Flow còn nguyên, minimap
và nút zoom vẫn chạy (chúng do React Flow vẽ, không phải các ID vừa xoá).

## 8.5. CHỐT PHASE 8

```
refactor(ui): giữ đầu trang theo loại trang, dọn CSS chết

Bốn tab Phòng họp / Dạy AI / Quy trình / Tác vụ tự động là workspace lấp đầy
màn hình. Sidebar đã chỉ rõ tab active; thêm pageHeader chỉ lặp thông tin và ăn
chiều cao của nội dung thao tác. Giữ cả bốn workspace không có h1 của Hub.

Nhóm trang cuộn giữ hệ đầu trang hiện có; Tổng quan tiếp tục dùng header đồng hồ
gọn. Không còn mục tiêu ép cả 12 tab cùng có một h1.

Dọn kèm: 9 nhóm class chết trong HubPage (bộ thẻ chỉ số cũ đã bị nhóm overview*
thay thế, kể cả các luật responsive trỏ tới chúng), 10 khối luật ID chết trong
Taskrunner (canvas tự viết đã thay bằng React Flow), và hàm
renderOutputContent không nơi nào gọi.

Giữ nguyên các class ghép động (status_*, statTone-*, completed/failed/running)
và các ID còn render.
```

**DỪNG. Chờ duyệt.**

---

# PHASE 9 — Màn hình hẹp và dọn rò rỉ toàn cục

**Phase rủi ro nhất, để cuối. Nếu thời gian gấp thì hoãn phase này lại.**

## 9.1. Phần A — Gộp hai khối `@media(max-width:720px)` mâu thuẫn

`HubPage.module.css` có **hai** khối cùng breakpoint 720px, làm hai việc trái ngược:

- Dòng 180: `.hubRoot{grid-template-columns:60px minmax(0,1fr)}` + `display:none` cho
  nhãn nav — kiểu **thanh icon**.
- Dòng 188: `.hubRoot{grid-template-columns:minmax(0,1fr)}` + bật lại các nhãn đó —
  kiểu **ngăn kéo**.

Khối sau thắng nên ngăn kéo chạy đúng, nhưng khối trước là luật chết và chỉ bị vô hiệu
nhờ độ đặc hiệu (`.sidebar .navItem span` đè `.navItem span`). Commit `1ebe071` có ghi
phần ngăn kéo đến từ một phiên song song và được đưa vào nguyên vẹn — đây là dấu vết đó.

### Việc phải làm

Gộp thành **một** khối 720px. Giữ hành vi **ngăn kéo** (khối dòng 188). Từ khối dòng 180,
**giữ lại** những luật không liên quan tới sidebar:

```
.page  .statGrid/.costSummary/.settingsGrid/.formGrid/.reviewGrid/.skillPicker
.settingsWide  .pageHeader  .range  .topbar  .projectHeader
.splitView/.meetingLayout  .sideList/.meetingList  .meetingRoom
.meetingRoomHeader  .meetingMessage/.agentMessage  .proposalList
.typeChoices  .overviewCards  .overviewWide
```

**Bỏ** những luật thuộc kiểu thanh icon: `.hubRoot{...60px...}`,
`.brand strong,.navItem span,.collapseButton{display:none}`, `.brand,.navItem{justify-content:center}`,
`.sidebar{padding-inline:8px}`.

Sau khi bỏ, các luật ở khối ngăn kéo phải chạy được **mà không cần độ đặc hiệu cao hơn**.
Nếu vẫn cần `.sidebar .navItem span` để thắng — nghĩa là còn sót luật mâu thuẫn, tìm tiếp.

**Lưu ý `.statGrid` đã bị xoá ở Phase 8** — đừng chép lại nó.

## 9.2. Phần B — Media query cho trang Dạy AI

`WorkspacePage.module.css`: 963 dòng, **0 breakpoint**. Hub có 1200/1000/720,
Taskrunner có 900, Login có 860 — riêng trang này không.

Cả sau Phase 1, bố cục 240 + 1fr + 300 cộng sidebar hub 232px là **772px chiếm chỗ cố định**.
Dưới ~1100px khung chat giữa còn lại rất hẹp và không có gì gập nó lại.

### Việc phải làm — hai mốc, khớp với mốc đã có của Hub

```css
/* ≤1100px: giấu cột thông tin bên phải, chat có chỗ thở */
@media (max-width: 1100px) {
  .workspace { grid-template-columns: var(--ws-col-sessions) minmax(0, 1fr); }
  .info-panel { display: none; }
}

/* ≤720px: khớp mốc ngăn kéo của Hub — xếp dọc, chỉ còn chat */
@media (max-width: 720px) {
  .workspace { grid-template-columns: minmax(0, 1fr); }
  .sessions-panel { display: none; }
}
```

> **Cảnh báo nghiêm trọng:** `display:none` cho `.info-panel` là **giấu mất chức năng** —
> ô ghi bài học, nút "Hài lòng"/"Cần cải thiện", nút "Lưu bài học kinh nghiệm" đều nằm
> trong đó. Cùng lý do với `.sessions-panel` (không chọn được phiên khác).
>
> Đây **chưa** phải giải pháp tốt, nó chỉ ngăn bố cục vỡ. Giải pháp đúng là một
> cơ chế tab hoặc ngăn kéo cho hai panel biên. **Làm bản `display:none` trước,
> ghi rõ hạn chế này trong commit, và đề xuất phần tab như một việc riêng.**
> **Không tự ý xây cơ chế tab trong phase này.**

## 9.3. Phần C — Rò rỉ luật toàn cục (làm cẩn thận, dễ vỡ nhất)

Bốn CSS module đều khai luật toàn cục. Chunk CSS của route lazy nạp vào `<head>` rồi
**ở lại vĩnh viễn** — thứ tự thắng thua phụ thuộc thứ tự người dùng ghé thăm, không tất định.
Vì `/` luôn chuyển hướng về `/login`, reset của Login gần như chắc chắn có mặt mọi phiên.

| File | Luật | Xử lý |
|---|---|---|
| `HubPage.module.css:2` | `:global(body){ background:#0b1412; color:#f2f6f4 }` | **Xoá cả hai dòng 2 và 3.** `theme.css` đã đặt `background:var(--bg); color:var(--text)` cho `html,body` — đây là bản ghi cứng, thừa. |
| `HubPage.module.css:1` | `:global(*){box-sizing:border-box}` | **Chuyển sang `theme.css`.** Xoá ở HubPage. |
| `LoginPage.module.css:11` | `:global(*){margin:0;padding:0}` | **Chuyển sang `theme.css`.** ⚠ Xem cảnh báo dưới. |
| `LoginPage.module.css:12-15` | `:global(body){min-height:100vh; overflow:hidden; ...}` | `overflow:hidden` phải **bỏ khỏi body**, chuyển vào `.root` của Login. Nó đang rò sang mọi trang khác. |
| `LoginPage.module.css:152` | `@media(max-width:860px){ :global(body){overflow:auto} }` | Bỏ theo, vì `overflow` không còn ở body. |
| `TaskrunnerPage.module.css:23` | `:global(html),:global(body){height:100%; font-family:'Inter'}` | `font-family` **xoá** (theme.css đã đặt). `height:100%` chuyển sang `theme.css`. |
| `WorkspacePage.module.css:35-37` | `:global(body){font-family:'Inter'}` | **Xoá cả khối.** theme.css đã đặt. |
| `theme.css:81` | `:global(body.light),` (dòng đứng trước `body.light {`) | **Xoá đúng một dòng** — xem cảnh báo dưới. |

> ### ⚠ `:global(body.light)` trong theme.css — xoá NHẦM DÒNG là chết cả theme Sáng
>
> `theme.css` **không phải** CSS module (nhập toàn cục ở `main.tsx:17`), nên `:global()`
> ở đây là selector không hợp lệ. Phát hiện qua cảnh báo build:
> `[lightningcss minify] 'global' is not recognized as a valid pseudo-class`.
>
> lightningcss tách danh sách selector thành hai luật riêng trong bản build:
> ```css
> body.light{--bg:#f5f5ef; ...}            /* hợp lệ — đang gánh toàn bộ theme Sáng */
> :global(body.light){--bg:#f5f5ef; ...}   /* không hợp lệ — trình duyệt bỏ cả khối */
> ```
>
> **PHẢI XOÁ DÒNG `:global(body.light),`, GIỮ DÒNG `body.light {`.**
>
> Ngược lại là mất sạch 23 token của theme Sáng cùng lúc. Đây đúng loại bẫy Phase 1
> vừa gỡ: một selector chết đứng cạnh một selector sống, và bản sống trông như bản thừa.
>
> Kết quả đúng sau khi sửa:
> ```css
> body.light {
>   --bg: #f5f5ef;
> ```
> Kiểm ngay: `npm run build` phải **hết** cảnh báo lightningcss, và
> `grep -c '#f5f5ef' dist/assets/index-*.css` vẫn phải ra 1.

> ### ⚠ CẢNH BÁO VỀ `:global(*){margin:0;padding:0}`
>
> Luật này **đang có tác dụng ở mọi trang** (vì Login luôn được ghé qua). Chuyển nó vào
> `theme.css` giữ nguyên hành vi. Nhưng nếu **xoá hẳn** thì mọi `h1 h2 p ul ol` khắp app
> đột nhiên có lại margin mặc định của trình duyệt — **hàng chục chỗ bố cục lệch cùng lúc**.
>
> **PHẢI CHUYỂN, KHÔNG ĐƯỢC XOÁ.** Đặt vào `theme.css` ngay đầu file:
> ```css
> *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
> ```
> Sau khi chuyển, **đi hết 12 tab + /login** so sánh với ảnh chụp trước đó.

## 9.4. Phần D — ID trùng (chỉ ghi nhận, không sửa)

Hub giữ mọi tab đã ghé ở trạng thái mounted (`hidden`), mà `company-runner` và
`auto-runner` cùng render `TaskrunnerPage`. Ghé cả hai tab là DOM có hai bản của
`#page-wrap #grid-wrap #add-workflow-btn #view-editor #editor-topbar #node-palette
#canvas-wrap #node-inspector #palette-categories`. HTML không hợp lệ.

Hiện **chưa gây lỗi** vì không có `getElementById` nào ngoài `#root`.

**Trong phase này chỉ làm một việc:** thêm chú thích cảnh báo tại
`TaskrunnerPage.tsx` và `WorkflowEditor.tsx`, ghi rõ các ID này trùng khi cả hai
runner tab cùng mounted, và **không được** thêm code truy vấn DOM theo ID.

**Không đổi ID sang class trong phase này** — việc đó động vào ~40 luật CSS và
cần phase riêng với ngân sách kiểm thử riêng.

## 9.5. Kiểm chứng

```bash
cd frontend

# 1. Chỉ còn MỘT khối 720px trong HubPage. KỲ VỌNG: 1.
grep -c '@media(max-width:720px)' src/pages/hub/HubPage.module.css

# 2. WorkspacePage nay có breakpoint. KỲ VỌNG: 2.
grep -c '@media' src/pages/workspace/WorkspacePage.module.css

# 3. Không còn :global(body) / :global(html) / :global(*) trong CSS module của trang.
#    KỲ VỌNG: không in ra gì. (Dùng -rn chứ không -rc: -rc in một dòng "file:0" cho
#    MỌI file, rất khó đọc và dễ tưởng là còn sót.)
#    Các :global(#id) của Taskrunner KHÔNG nằm trong diện này — chúng vẫn còn.
grep -rn ':global(body)\|:global(html)\|:global(\*)' src/pages/

# 4. Reset đã về theme.css. KỲ VỌNG: có.
grep -n 'box-sizing' src/styles/theme.css

# 5. theme.css hết :global. KỲ VỌNG: không in ra gì.
grep -n ':global' src/styles/theme.css

# 6. Theme Sáng còn nguyên sau khi xoá dòng :global. KỲ VỌNG: 1.
grep -c '#f5f5ef' dist/assets/index-*.css

# 7. Build hết cảnh báo lightningcss. KỲ VỌNG: không in ra gì.
npm run build 2>&1 | grep -i 'lightningcss'

npm run typecheck && npm run build
npm run verify:graphs && npm run verify:workflow-protocol
npm run verify:meeting-protocol && npm run verify:hub-integration
```

Backend (chắc không vạ lây):

```bash
cd backend && python -m pytest -q     # KỲ VỌNG: 311 passed
```

## 9.6. Kiểm chứng mắt — kỹ nhất trong tất cả các phase

Ở **mỗi** bề rộng dưới đây, đi hết 12 tab + `/login`, ở **cả hai theme**:

| Bề rộng | Xem gì |
|---|---|
| 1920px | Mọi thứ như trước khi sửa. Đây là bài kiểm tra chống hồi quy chính. |
| 1280px | Dạy AI vẫn đủ ba cột. |
| 1100px | Dạy AI vừa bỏ cột thông tin. Chat rộng ra. |
| 900px | Sidebar Hub vẫn dạng cột đầy đủ. |
| 720px | Sidebar Hub thành ngăn kéo — bấm nút menu để mở/đóng. Dạy AI chỉ còn chat. |
| 380px | Không có gì tràn ngang. Không có thanh cuộn ngang ở `body`. |

**Đặc biệt kiểm sau khi chuyển reset `margin:0;padding:0`:** mở `/login` **đầu tiên**
rồi mới vào `/hub` (đúng đường đi thật của người dùng), và một lần nữa vào thẳng
`/hub` bằng cách gõ URL. **Hai lần phải giống hệt nhau.** Trước khi sửa, hai đường
này có thể cho kết quả khác nhau — đó chính là lỗi đang gỡ.

## 9.7. CHỐT PHASE 9

```
fix(ui): màn hình hẹp và dọn luật toàn cục rò rỉ giữa các trang

HubPage có hai khối @media 720px làm hai việc trái ngược — một kiểu thanh icon,
một kiểu ngăn kéo. Khối sau thắng nên ngăn kéo chạy đúng, nhưng khối trước là
luật chết chỉ bị vô hiệu nhờ độ đặc hiệu. Gộp thành một.

WorkspacePage có 963 dòng và 0 breakpoint; kể cả sau khi khôi phục bố cục ba
cột, 772px là chiều ngang chiếm chỗ cố định và không có gì gập nó lại. Thêm hai
mốc 1100/720 khớp mốc đã có của Hub.

HẠN CHẾ ĐÃ BIẾT: hai mốc này dùng display:none nên ở màn hẹp mất luôn ô ghi bài
học và bộ chọn phiên. Đây là biện pháp chặn vỡ bố cục, chưa phải giải pháp. Việc
đúng là cơ chế tab/ngăn kéo cho hai panel biên — đề xuất làm riêng.

Bốn CSS module đều khai :global(body)/:global(*); chunk CSS của route lazy nạp
vào head rồi ở lại vĩnh viễn nên thứ tự thắng thua phụ thuộc thứ tự người dùng
ghé thăm. Gom hết về theme.css. Riêng :global(*){margin:0;padding:0} được
CHUYỂN chứ không xoá — xoá hẳn là mọi h1/h2/p/ul khắp app có lại margin mặc
định cùng lúc.

theme.css có `:global(body.light), body.light {` — mà theme.css không phải CSS
module nên :global() ở đó là selector không hợp lệ; lightningcss tách đôi danh
sách và nửa :global bị trình duyệt bỏ. Theme Sáng vẫn chạy nhờ nửa còn lại,
nhưng bundle mang thêm ~600 byte CSS chết và ai đó xoá nhầm nửa đang sống là
mất cả 23 token theme Sáng. Xoá đúng dòng :global.

ID trùng khi cả hai runner tab cùng mounted: mới chỉ thêm chú thích cảnh báo.
Đổi sang class động vào ~40 luật CSS, cần phase riêng.
```

**DỪNG. Chờ duyệt.**

---

# PHỤ LỤC A — Bảng tra token

Nguồn duy nhất: `frontend/src/styles/theme.css`.

| Token | Tối | Sáng | Dùng cho |
|---|---|---|---|
| `--bg` | `#0b1412` | `#f5f5ef` | nền trang |
| `--surface` | `#111d1a` | `#fffefa` | nền thẻ/panel |
| `--surface2` | `#172723` | `#f0f3ec` | nền chìm cấp 1 |
| `--surface3` | `#1c2d28` | `#e7ede5` | nền chìm cấp 2 |
| `--sidebar` | `#06110f` | `#12382d` | **MÀU** nền sidebar (không phải bề rộng!) |
| `--text` | `#f2f6f4` | `#17201d` | chữ chính |
| `--text-soft` | `#cdd9d5` | `#3d4a45` | chữ phụ |
| `--muted` | `#9daea8` | `#5f6d67` | chữ mờ |
| `--border` | `#263832` | `#dfe5dc` | viền |
| `--border-strong` | `#32493f` | `#c8d2c6` | viền đậm |
| `--accent` | `#52d6a0` | `#2c8462` | màu nhấn |
| `--accent-strong` | `#6fe6b5` | `#237454` | nhấn đậm |
| `--on-accent` | `#08120f` | `#ffffff` | **chữ đặt trên nền accent** |
| `--danger` | `#e27b6f` | `#bd5048` | nguy hiểm |
| `--on-danger` | `#1a0d0b` | `#ffffff` | **chữ đặt trên nền danger** |
| `--warning` | `#d7a95e` | `#ad7628` | cảnh báo |
| `--info` | `#5b9df0` | `#2f6fb8` | **MÀU** xanh dương (không phải bề rộng!) |
| `--on-info` | `#06121f` | `#ffffff` | **chữ đặt trên nền info** (Phase 4 thêm) |
| `--purple-tone` | `#a78bfa` | `#7c5cd6` | tím |
| `--fs-scale` | `1.15` | `1.15` | hệ số cỡ chữ toàn app |

Bộ ba RGB cho `rgba()`: `--accent-rgb` `--danger-rgb` `--warning-rgb` `--info-rgb`
`--purple-rgb-base`. Bắt buộc dùng chúng — `rgba()` không nhận hex qua `var()`.

`theme.css` còn ánh xạ 49 tên cũ (`--ink --bg-card --gold --cyan --sky-ink ...`) về
token chuẩn. Đó là lớp bắc cầu, không phải đích đến; khi sửa vào một trang thì đổi
luôn sang tên chuẩn, nhưng **đừng đổi hàng loạt** ngoài phạm vi phase.

---

# PHỤ LỤC B — Bảng kiểm cuối, chạy sau khi Phase 1–10, 2-bis và 2-ter được duyệt

```bash
cd frontend
npm run typecheck
npm run build
npm run verify:graphs
npm run verify:workflow-protocol
npm run verify:meeting-protocol
npm run verify:hub-integration

cd ../backend && python -m pytest -q      # KỲ VỌNG: 311 passed
```

Kiểm mắt lần cuối: 12 tab × 2 theme × 2 ngôn ngữ × 3 bề rộng (1920 / 900 / 380).
Console phải **0 lỗi** ở mọi tổ hợp.

Đối chiếu số đo trước/sau:

| Chỉ số | Trước | Kỳ vọng sau |
|---|---|---|
| Cột của `.workspace` (Dạy AI) | 1 (sập) | 3 |
| `font:` shorthand không theo `--fs-scale` | 25 | 2 (ngoại lệ có chủ ý) |
| Khai báo `font-size` có `--fs-scale` | 259 | 282 |
| Chữ trắng trên nền màu | 11 | Thêm 1 dòng `.submit-btn` có nền `var(--accent)`; đây là nhóm miễn trừ thứ tư, không phải hồi quy cần sửa |
| Hex bảng nâu-kem trong HubPage | 26 | 0 |
| Media query trong WorkspacePage | 0 | 2 |
| Khối `@media 720px` trong HubPage | 2 | 1 |
| Nhóm class chết trong HubPage | 9 | 0 |
| Khối luật ID chết trong Taskrunner | 10 | 0 |
| `:global(body)` trong CSS module | 4 | 0 |
| Tab có `<h1>` — nhất quán theo loại trang | 8/12 (Phòng họp còn `<h1>`) | 7/12 sau Phase 2-TER: 7 trang cuộn giữ `<h1>`; 4 workspace không có; Tổng quan giữ header đồng hồ gọn |

---

# PHASE 10 — Menu tài khoản và đường đăng xuất nhanh trên topbar Hub

## 10.1. Bối cảnh

Chip tài khoản ở góc trên bên phải topbar Hub hiện chỉ hiển thị icon người và tên đăng nhập,
không có tương tác. Người dùng muốn bấm chip này để mở một menu có đúng một mục đăng xuất,
song song với nút đăng xuất đã có trong trang Cài đặt.

Có một bẫy CSS tại `HubPage.module.css`: luật `.topbarActions > button` ép mọi nút con trực
tiếp thành ô `34px × 34px`. Nếu đổi thẳng `.accountSummary` từ `span` thành `button`, tên người
dùng sẽ bị bóp mất. Menu cũng phải dùng đúng cơ chế phiên và chuỗi i18n hiện có, không tạo một
luồng đăng xuất thứ hai.

## 10.2. Việc phải làm

1. Trong `HubPage.tsx`, bọc chip tài khoản bằng `.accountMenu` và đổi `.accountSummary` thành
   nút mở/đóng dropdown. Nút phải có `aria-haspopup="menu"`; `aria-expanded` phản ánh đúng trạng
   thái thực tế.
2. Dropdown có `role="menu"`, neo ngay dưới chip, canh mép phải và chỉ có một nút
   `role="menuitem"`. Nhãn lấy từ `hubText(language, "common.logout")`.
3. Mục đăng xuất tái dùng nguyên mẫu đã có ở `SettingsPage.tsx`:
   `void sessionApi.logout().finally(() => navigate("/login", { replace: true }))`.
4. Bấm chip lần nữa phải đóng menu. Bấm ra ngoài hoặc nhấn `Escape` cũng phải đóng; mọi listener
   gắn trên `document` phải được tháo trong cleanup của `useEffect`.
5. Trong `HubPage.module.css`, đặt `.accountMenu { position: relative }` để nút tài khoản không
   còn là con trực tiếp của `.topbarActions`. Giữ nguyên luật `34px × 34px` cho nút đổi theme và
   `.mobileMenuButton`.
6. Dropdown dùng `right: 0` để không tràn mép phải ở màn hình hẹp. Giữ luật
   `.accountSummary strong { display: none }` tại breakpoint `720px`, để chip chỉ còn icon nhưng
   vẫn bấm và mở menu được.
7. Dùng `z-index: 21`: đây là đúng một cấp cao hơn z-index lớn nhất sẵn có trong file là sidebar
   `20` (scrim là `19`), đủ để menu không bị content, panel hay sidebar che.

## 10.3. Không được làm

- Không sửa bất kỳ file nào trong `backend/`.
- Không xoá hoặc thay đổi đường đăng xuất trong `SettingsPage.tsx`.
- Không đổi mảng `navigation[]` trong `HubPage.tsx`.
- Không sửa `--fs-scale` trong `theme.css`.
- Không tạo key i18n mới và không viết cứng chuỗi `Đăng xuất` trong JSX.
- Không dùng z-index rất lớn tùy ý; giữ `21` theo thang z-index hiện có.
- Không commit trong lượt thực thi này; dừng ở cổng kiểm mắt để người dùng duyệt.

## 10.4. Kiểm chứng máy

```bash
cd frontend

# 1. Chip tài khoản được bọc để né luật .topbarActions > button. KỲ VỌNG: 1.
grep -F -c 'className={c("accountMenu")}' src/pages/hub/HubPage.tsx

# 2. Nút khai báo menu và trạng thái mở. KỲ VỌNG: mỗi lệnh in 1.
grep -F -c 'aria-haspopup="menu"' src/pages/hub/HubPage.tsx
grep -F -c 'aria-expanded={accountMenuOpen}' src/pages/hub/HubPage.tsx

# 3. Dùng đúng key i18n có sẵn. KỲ VỌNG: 1.
grep -F -c 'hubText(language, "common.logout")' src/pages/hub/HubPage.tsx

# 4. Tái dùng đúng mẫu logout, gồm .finally và replace:true. KỲ VỌNG: 1.
grep -F -c 'void sessionApi.logout().finally(() => navigate("/login", { replace: true }))' src/pages/hub/HubPage.tsx

# 5. Listener ngoài menu và phím Escape đều có cleanup. KỲ VỌNG: mỗi lệnh in 2
#    (một addEventListener và một removeEventListener).
grep -F -c '"pointerdown", closeOnOutsideClick' src/pages/hub/HubPage.tsx
grep -F -c '"keydown", closeOnEscape' src/pages/hub/HubPage.tsx

# 6. Z-index theo đúng thang hiện có. KỲ VỌNG: z-index:21 ra 1; z-index:20 vẫn ra 1.
grep -F -c 'z-index:21' src/pages/hub/HubPage.module.css
grep -F -c 'z-index: 20' src/pages/hub/HubPage.module.css

# 7. Quy tắc ẩn tên ở màn hẹp còn nguyên. KỲ VỌNG: 1.
grep -F -c '.accountSummary strong{display:none}' src/pages/hub/HubPage.module.css

npm run typecheck
npm run build

# 8. Build chỉ sinh đúng một CSS chunk của HubPage. KỲ VỌNG: 1.
find dist/assets -maxdepth 1 -name 'HubPage-*.css' | wc -l

# 9. Backend trỏ đúng frontend/dist và mount assets từ đó. KỲ VỌNG: mỗi lệnh in 1.
cd ..
grep -F -c 'parents[2] / "frontend" / "dist"' backend/hub/server.py
grep -F -c 'frontend_assets = _frontend_dist_path / "assets"' backend/hub/server.py
```

## 10.5. Kiểm mắt

Hard refresh trình duyệt trước khi kiểm, rồi xác nhận:

- Ở tiếng Việt, chip hiện icon + tên tài khoản; bấm mở menu có đúng mục “Đăng xuất”.
- Ở tiếng Anh, cùng menu hiện đúng “Log out”; không còn chuỗi tiếng Việt trong menu.
- Bấm chip liên tiếp mở rồi đóng; bấm ra ngoài đóng; mở lại và nhấn `Escape` cũng đóng.
- Mục đăng xuất kết thúc phiên và chuyển tới `/login`, không để lại trang Hub trong history.
- Ở cả theme sáng và tối, menu có viền/nền/chữ rõ, nằm trên content và panel.
- Nút đổi theme và nút menu mobile vẫn giữ đúng ô `34px × 34px`, không đổi kiểu dáng.
- Ở `720px` và nhỏ hơn, tên tài khoản ẩn, icon vẫn bấm được; dropdown canh phải và không tràn
  khỏi mép màn hình. Kiểm thêm tại `380px` để chắc chắn không xuất hiện cuộn ngang.
- Nút đăng xuất trong trang Cài đặt vẫn còn và vẫn hoạt động.

## 10.6. CHỐT PHASE 10

```text
feat(hub): thêm menu đăng xuất trên chip tài khoản

Đổi chip tài khoản ở topbar thành nút mở dropdown có hỗ trợ aria, đóng khi bấm ra ngoài
hoặc nhấn Escape, và dọn listener đúng vòng đời. Menu dùng key common.logout hiện có và
tái sử dụng sessionApi.logout với điều hướng replace tới trang đăng nhập.

Bọc nút trong accountMenu để tránh luật .topbarActions > button ép thành ô 34px, giữ nguyên
kiểu dáng nút theme/mobile. Dropdown canh phải cho màn hẹp và dùng z-index 21, ngay trên
sidebar z-index 20 theo thang lớp sẵn có.
```

**DỪNG. Không commit. Chờ người dùng kiểm mắt và duyệt Phase 10.**

---

# PHASE 11 — Thu gọn và thiết kế lại thẻ quy trình Taskrunner

## 11.1. Bối cảnh

Tại `/hub/company-runner`, thẻ `.workflow-card` bị vỡ chữ và có cỡ chữ không đồng đều sau các phase
chuẩn hoá trước. Chẩn đoán phải được giữ lại đầy đủ vì đây không phải một lỗi đơn lẻ:

1. Nhãn `.wf-stat-label` đồng thời dùng `font-family:var(--mono)`, `text-transform:uppercase`,
   `letter-spacing:.6px` và `font-weight:700`. Riêng ba thuộc tính mono + uppercase + letter-spacing
   cộng dồn đã làm nhãn tiếng Việt dài gần gấp đôi; đây là bẫy dễ tái phạm. Hậu quả là “TỶ LỆ THÀNH
   CÔNG” và “LẦN CHẠY CUỐI” xuống dòng.
2. `.wf-stats` dùng `display:flex; justify-content:space-between` cho ba mục có độ dài khác nhau.
   Các cột không bằng nhau nên cột nhãn dài đẩy cột khác và làm giá trị như “2 ngày trước” xuống dòng.
3. `.wf-flow` chỉ có năm chấm màu nối bằng đường kẻ; ý nghĩa nằm trong thuộc tính `title`, nên người
   dùng phải rê chuột mới biết dãy chấm đại diện cho các bước.
4. `.wf-btn` dùng `font-size:clamp(9.5px,2.6cqw,12px)` theo container query. Ở thẻ rộng khoảng
   `380px`, cỡ thực tế chỉ khoảng `9.9px`, nhỏ hơn mọi chữ khác trên thẻ.
5. Phase 3 đã nhân mọi cỡ chữ với `--fs-scale`; các vị trí trước đó chỉ vừa khít vì dùng cỡ nhỏ nay bị
   tràn. Không được sửa ngược bằng cách thay `--fs-scale` hoặc tiếp tục bóp riêng chữ trong thẻ.

`WorkflowList.tsx` hiện dùng chuỗi tiếng Việt trực tiếp và không gọi hàm dịch. Phase này phải giữ đúng
quy ước đang có trong file, không tự tạo một cơ chế i18n mới chỉ cho vài nhãn.

## 11.2. Việc phải làm

1. Rút gọn đúng ba nhãn hiển thị: “Tỷ lệ thành công” thành “Thành công”, “Tổng lần chạy” thành
   “Lần chạy”, và “Lần chạy cuối” thành “Chạy cuối”.
2. Bỏ `font-family:var(--mono)`, uppercase và letter-spacing khỏi `.wf-stat-label`. Giữ
   `font-family:var(--mono)` cho hai giá trị số “Thành công” và “Lần chạy” để số liệu vẫn thẳng cột,
   dễ đọc. Giá trị chữ của “Chạy cuối” phải nối thêm class `muted`; biến thể có sẵn này thu chữ còn
   `calc(12px * var(--fs-scale))`, giảm độ đậm/màu và đặt `font-family:inherit` thay vì mono. Riêng
   thẻ quy trình gọi `cardRelativeTime()` để bỏ hậu tố “trước” khỏi các chuỗi phút/giờ/ngày vì nhãn
   “Chạy cuối” ngay phía trên đã hàm ý quan hệ thời gian. Không sửa `relativeTime()`: danh sách lịch sử
   chạy vẫn phải gọi hàm này trực tiếp và giữ chuỗi đầy đủ có “trước”, do ở đó không có nhãn hàm ý.
3. Đổi `.wf-stats` thành grid ba cột bằng nhau với
   `grid-template-columns:repeat(3,minmax(0,1fr))`. Thêm `white-space:nowrap` cho cả nhãn và giá trị;
   mỗi `.wf-stat` phải có `min-width:0` để cột grid co đúng cách. Giá trị có thêm
   `overflow:hidden;text-overflow:ellipsis` làm lưới an toàn cho dữ liệu dài bất ngờ.
4. Tính `const dots = flowDots(task)` đúng một lần cho mỗi thẻ, dùng cùng mảng đó để dựng chấm và
   hiển thị nhãn bên phải dạng `{dots.length} bước`. Chỉ thêm nhãn số bước, không biến dãy chấm thành
   sơ đồ chi tiết.
5. Đổi font nút sang `calc(12px * var(--fs-scale))`. Giữ nút “Chạy” là nút primary dùng
   `var(--on-accent)`. Cho riêng footer được xuống hàng khi thiếu chỗ để nhãn không bị bóp; nút xoá
   có kích thước theo nội dung và được đẩy sang mép phải.
6. Giữ container query của `.wf-footer`: sau khi kiểm tra, trong cùng footer vẫn còn `cqw` cho gap,
   padding và kích thước icon, nên `container-type`/`container-name` chưa phải CSS chết.
7. Thu `.workflow-card` từ `padding:18px; gap:12px` xuống `padding:16px; gap:10px`; đổi cột grid từ
   `minmax(300px,1fr)` thành `minmax(290px,1fr)`.
8. Giữ nguyên toàn bộ handler `onClick`, `stopPropagation`, lịch chạy `.wf-schedule` và các trạng thái
   `.wf-status.active`, `.paused`, `.draft`, `.failed`.

> ### ⚠ `nowrap` KHÔNG TỰ GIẢI QUYẾT CHỮ DÀI
>
> `white-space:nowrap` chỉ đổi lỗi xuống dòng thành lỗi tràn nếu nội dung vẫn rộng hơn cột và không có
> biện pháp thu gọn/cắt gọn. Riêng “Chạy cuối” là chữ do `relativeTime()` sinh ra, không phải số liệu
> cần canh bằng mono: phải dùng biến thể `.wf-stat-value.muted` nhỏ hơn, nhẹ hơn, font thường và giữ
> `overflow:hidden;text-overflow:ellipsis` làm lưới an toàn.
>
> `.wf-stat-value.muted` đã tồn tại sẵn trước Phase 11 nhưng chưa được nối vào `WorkflowList.tsx`.
> Sau khi class `muted` được gắn cho giá trị “Chạy cuối”, đây là **luật sống**, không được liệt kê hay
> xoá như CSS chết trong phase dọn dẹp về sau.
>
> Quyết định đã duyệt: chỉ trên thẻ quy trình, chuỗi tương đối bỏ hậu tố “trước” (`24 ngày trước` →
> `24 ngày`, `45 phút trước` → `45 phút`, `2 giờ trước` → `2 giờ`); “Vừa xong”, “Chưa chạy” và ngày
> tháng đầy đủ từ `toLocaleDateString()` giữ nguyên. Lý do là nhãn “Chạy cuối” đã hàm ý “trước”. Danh
> sách lịch sử là ngoại lệ bắt buộc: vẫn dùng `relativeTime()` và chuỗi đầy đủ vì không có nhãn đó.
>
> Đo lại bằng đúng Inter 500 ở `12px × 1.15 = 13.8px`, cộng tổng advance width không kerning: nhóm
> tương đối dài nhất là “24 ngày” `53.87px` (“45 phút” `50.89px`, “2 giờ” `32.51px`); nhóm trạng thái
> cố định dài nhất là “Chưa chạy” `70.71px` (“Vừa xong” `62.91px`); ngày mười ký tự như
> “13/08/2026” là `76.78px`. Ở thẻ `290px`, bề rộng mỗi cột là
> `(290 - 32 - 16) / 3 = 80.67px`. Cả ba nhóm đều lọt: biên còn lại lần lượt ít nhất `26.80px`,
> `9.96px` và `3.88px`. Vẫn giữ `overflow:hidden;text-overflow:ellipsis` làm lưới an toàn cho dữ liệu
> bất ngờ; không đổi bố cục ba cột.

## 11.3. Không được làm

- Không sửa file nào trong `backend/`.
- Không sửa `--fs-scale`, không hoàn tác kết quả Phase 3.
- Không đổi các trang ngoài `frontend/src/pages/taskrunner/`.
- Không mở rộng `.wf-flow` thành sơ đồ chi tiết, tooltip mới hoặc legend màu.
- Không đổi hành vi chạy, bật/tạm dừng, chỉnh sửa, lịch sử, xoá hay cơ chế chặn click nổi bọt ở footer.
- Không đổi `.wf-schedule` hoặc các biến thể status active/paused/draft/failed.
- Không hardcode chữ trắng trên nền màu; nếu đụng màu chữ phải dùng `--on-accent`, `--on-danger` hoặc
  `--on-info` theo Phase 4.
- Không tạo cơ chế song ngữ mới trong riêng `WorkflowList.tsx`; giữ quy ước chuỗi trực tiếp hiện có.
- Không commit trong lượt thực thi này; dừng ở cổng kiểm mắt để người dùng duyệt.

## 11.4. Kiểm chứng máy

```bash
cd frontend

# 1. Ba nhãn mới có mặt đúng một lần. KỲ VỌNG: mỗi lệnh in 1.
grep -F -c '>Thành công</span>' src/pages/taskrunner/WorkflowList.tsx
grep -F -c '>Lần chạy</span>' src/pages/taskrunner/WorkflowList.tsx
grep -F -c '>Chạy cuối</span>' src/pages/taskrunner/WorkflowList.tsx

# 2. Ba nhãn dài cũ đã biến mất. KỲ VỌNG: mỗi lệnh in 0.
grep -F -c '>Tỷ lệ thành công</span>' src/pages/taskrunner/WorkflowList.tsx
grep -F -c '>Tổng lần chạy</span>' src/pages/taskrunner/WorkflowList.tsx
grep -F -c '>Lần chạy cuối</span>' src/pages/taskrunner/WorkflowList.tsx

# 3. Stats là grid ba cột; label không còn mono/uppercase/tracking; hai số vẫn mono;
#    giá trị Chạy cuối dùng biến thể muted/font thường; mọi value có lưới an toàn ellipsis.
#    KỲ VỌNG: sáu lệnh đầu in 1; ba lệnh kiểm thuộc tính cũ in 0.
grep -F -c 'grid-template-columns:repeat(3,minmax(0,1fr))' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F -c '.wf-stat-label{font-size:calc(9px * var(--fs-scale));font-weight:700;color:var(--text3);white-space:nowrap}' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F -c 'font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F -c 'className={`${c("wf-stat-value")} ${c("muted")}`}' src/pages/taskrunner/WorkflowList.tsx
grep -F -c '.wf-stat-value.muted{color:var(--text2);font-size:calc(12px * var(--fs-scale));font-weight:500;font-family:inherit}' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F -c 'overflow:hidden;text-overflow:ellipsis' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F '.wf-stat-label' src/pages/taskrunner/TaskrunnerPage.module.css | grep -F -c 'font-family:var(--mono)'
grep -F '.wf-stat-label' src/pages/taskrunner/TaskrunnerPage.module.css | grep -F -c 'text-transform:uppercase'
grep -F '.wf-stat-label' src/pages/taskrunner/TaskrunnerPage.module.css | grep -F -c 'letter-spacing:.6px'

# 3b. Chỉ thẻ dùng chuỗi rút gọn; lịch sử vẫn gọi relativeTime trực tiếp. KỲ VỌNG: mỗi lệnh in 1.
grep -F -c 'function cardRelativeTime(value?: string): string' src/pages/taskrunner/WorkflowList.tsx
grep -F -c 'cardRelativeTime(task.runs[0]?.created_at)' src/pages/taskrunner/WorkflowList.tsx
grep -F -c '<small>{relativeTime(run.created_at)}</small>' src/pages/taskrunner/WorkflowList.tsx

# 4. flowDots chỉ được gọi một lần trong vòng lặp và nhãn dùng chính dots.length.
#    KỲ VỌNG: mỗi lệnh in 1.
grep -F -c 'const dots = flowDots(task);' src/pages/taskrunner/WorkflowList.tsx
grep -F -c '{dots.length} bước' src/pages/taskrunner/WorkflowList.tsx

# 5. Nút dùng cỡ cố định theo --fs-scale, footer được wrap và nút xoá nằm bên phải.
#    KỲ VỌNG: bốn lệnh đầu in 1; clamp font-size cũ in 0.
grep -A3 '^\.wf-btn{' src/pages/taskrunner/TaskrunnerPage.module.css | grep -F -c 'font-size:calc(12px * var(--fs-scale))'
grep -A2 '^\.wf-footer{' src/pages/taskrunner/TaskrunnerPage.module.css | grep -F -c 'flex-wrap:wrap'
grep -F -c '.wf-footer .wf-btn.danger{flex:0 0 auto;margin-left:auto}' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F -c 'container-type:inline-size;container-name:wf-footer' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F -c 'font-size:clamp(9.5px,2.6cqw,12px)' src/pages/taskrunner/TaskrunnerPage.module.css

# 6. Kích thước thẻ/grid đúng phương án. KỲ VỌNG: mỗi lệnh in 1.
grep -F -c 'minmax(290px,1fr)' src/pages/taskrunner/TaskrunnerPage.module.css
grep -F -c 'padding:16px;display:flex;flex-direction:column;gap:10px' src/pages/taskrunner/TaskrunnerPage.module.css

# 7. Hành vi bắt buộc còn nguyên. KỲ VỌNG: stopPropagation in 1; schedule/status đều có kết quả.
grep -F -c 'onClick={(event) => event.stopPropagation()}' src/pages/taskrunner/WorkflowList.tsx
grep -F -c 'task.schedule_enabled' src/pages/taskrunner/WorkflowList.tsx
grep -E -c '^\.wf-status\.(active|paused|draft|failed)' src/pages/taskrunner/TaskrunnerPage.module.css

npm.cmd run typecheck
npm.cmd run build

# 8. Build chỉ có đúng một CSS chunk của TaskrunnerPage. KỲ VỌNG: 1.
find dist/assets -maxdepth 1 -name 'TaskrunnerPage-*.css' | wc -l

# 9. Backend phục vụ đúng dist/assets vừa build. KỲ VỌNG: mỗi lệnh in 1.
cd ..
grep -F -c 'parents[2] / "frontend" / "dist"' backend/hub/server.py
grep -F -c 'frontend_assets = _frontend_dist_path / "assets"' backend/hub/server.py
```

## 11.5. Kiểm mắt

Hard refresh trình duyệt trước khi kiểm, rồi xác nhận tại `/hub/company-runner`:

- Nhãn “Thành công”, “Lần chạy”, “Chạy cuối” và mọi giá trị đều nằm trên một dòng; ba cột thẳng hàng.
- Dãy chấm có nhãn “N bước” bên phải, đúng với số chấm/bước đang hiển thị và không cần rê chuột mới
  hiểu ý nghĩa tổng quát.
- Chữ trên các nút không nhỏ hơn chữ xung quanh; nút “Chạy” nổi bật, nút xoá nằm tách ở bên phải;
  ở thẻ hẹp các nút xuống hàng gọn, không bị cắt chữ hay tràn thẻ.
- Kiểm cả thẻ có lịch chạy và thẻ không có lịch chạy: footer không nhảy lệch, khoảng cách trong thẻ gọn.
- Nếu tạo được dữ liệu, kiểm đủ status active, paused, draft và failed: chấm, màu và nhãn trạng thái giữ
  nguyên; nút bật/tạm dừng vẫn đúng trạng thái.
- Bấm thử thẻ và từng nút footer để xác nhận mở/chạy/bật-tạm dừng/chỉnh sửa/lịch sử/xoá vẫn giữ đúng
  hành vi, click nút không đồng thời mở thẻ.
- Kiểm ít nhất ở theme sáng và tối, cùng một bề rộng desktop và một bề rộng hẹp gần ngưỡng `290px`.

## 11.6. CHỐT PHASE 11

```text
fix(taskrunner): thu gọn và cân lại thẻ quy trình

Rút gọn nhãn thống kê, bỏ tổ hợp mono/uppercase/tracking trên nhãn và đổi hàng thống kê thành grid
ba cột không xuống dòng; giữ mono cho hai số, nối biến thể muted/font thường có sẵn cho “Chạy cuối”
và cắt ellipsis nếu gặp dữ liệu dài bất ngờ. Dùng cùng dữ liệu flowDots để thêm nhãn số bước cạnh dãy
chấm, giúp người dùng hiểu ý nghĩa mà không phải rê chuột.

Đưa cỡ chữ nút về calc() theo --fs-scale, cho footer xuống hàng khi thẻ hẹp, giữ nút Chạy là primary
và tách nút xoá sang phải. Đồng thời thu padding/gap của thẻ và giảm min-width cột grid xuống 290px;
giữ nguyên toàn bộ handler, lịch chạy, trạng thái và token tương phản Phase 4.
```

**DỪNG. Không commit. Hard refresh rồi chờ người dùng kiểm mắt và duyệt Phase 11.**

---

## Hàng đợi tinh chỉnh sau khi hoàn tất UI

- **2026-08-13:** Người dùng đánh giá thẻ quy trình sau Phase 11 chưa thật ưng nhưng chấp nhận để ưu
  tiên tiến độ. Cần quay lại tinh chỉnh sau khi hoàn tất toàn bộ UI. Chưa có chi tiết cụ thể nào được
  nêu, nên khi quay lại phải hỏi người dùng điểm nào còn lấn cấn.

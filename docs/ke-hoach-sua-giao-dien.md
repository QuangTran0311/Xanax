# Kế hoạch sửa giao diện Xanax — 9 phase

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

### 0.3. Ba màu KHÔNG được token hoá — để nguyên hex

Có ba nhóm mã hex trông "cần dọn" nhưng thực ra là **cố ý**. Đụng vào là hỏng:

| Nhóm | Vị trí | Vì sao phải giữ |
|---|---|---|
| Chữ/nền trong sidebar | `HubPage.module.css` các luật `.sidebar`, `.brand`, `.brand small`, `.navItem`, `.navItem:hover`, `.navActive`, `.sidebarHealth*`, `.collapseButton*` — gồm `#f2f6f4 #91aaa2 #a9bbb5 #dff8ec #8da79e #9fb1ab #fff #52d6a0 #d7a95e` | Sidebar **luôn** nền tối ở cả hai theme (`--sidebar` là `#06110f` ở tối và `#12382d` ở sáng). Chữ ở đây phải cố định sáng. Đổi sang `var(--text)` là chữ đen trên nền xanh đậm ở theme Sáng. |
| Ô xem trước theme | `.themePreviewLight`, `.themePreviewDark` (`#f4eee6 #fff #221e1a #2c2721`) | Đây là **mẫu màu minh hoạ** trong trang Cài đặt. Chúng phải trông giống theme mà chúng đại diện, bất kể theme đang bật. |
| Icon trên node | `TaskrunnerPage.module.css` `.flow-node .node-icon`, `.pick-node-item .node-icon`, `.inspector-header .node-icon`, `.se-card-icon`, `.editor-logo`, `.flow-node.node-running::before` (`#fff`) | Nền của các phần tử này do inline style đặt theo loại node, luôn là màu đậm bão hoà. |

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

Sau mỗi phase có sửa hiển thị, chạy `npm run dev` và tự mở, ở **cả hai theme**
(nút mặt trăng góc phải trên) và **cả hai ngôn ngữ** (Cài đặt → Ngôn ngữ):

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

Tại luật gộp `.primaryButton,.buttonDanger,.buttonGhost` (dòng ~134), **thêm** hai
thuộc tính vào cuối khối, giữ nguyên mọi thứ đang có:

```css
white-space: nowrap;
flex-shrink: 0;
```

Nút trong app này ở đâu cũng là nhãn ngắn (1-3 từ). Không có nút nào cần xuống dòng.
Sửa ở luật gộp thì mọi nút chính/nguy hiểm/phụ đều được, không phải vá từng chỗ.

### Bước 2.2.b — Cho tiêu đề phòng họp co được

Tiêu đề dài cũng góp phần ép nút. Tại `.meetingRoomHeader h2`, **thêm**:

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

- **Không** đổi `#fff` ở nhóm sidebar, ô xem trước theme, hay icon node —
  xem **mục 0.3**. Đó là 3 nhóm bất khả xâm phạm.
- **Không** đổi giá trị của `--accent`, `--danger` hay bất kỳ màu nền nào.
  Phase này chỉ đổi **màu chữ đặt trên** nền.

## 4.6. Kiểm chứng

```bash
cd frontend

# Quét lại đúng bằng script đã dùng khi khảo sát.
# KỲ VỌNG: chỉ còn các dòng thuộc 3 nhóm miễn trừ ở mục 0.3, và KHÔNG dòng nào
# có nền là var(--accent|cyan|blue|red|danger|info).
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
| `/login` | Nút "Đăng nhập" — chữ gần đen trên nền xanh. Bấm vào xem vòng xoay có thấy không. |
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

Chừa nguyên ba nhóm cố ý ghi cứng: chữ trong sidebar (sidebar luôn nền tối ở
cả hai theme), ô xem trước theme trong Cài đặt, và icon trên node của trình
soạn quy trình.
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

# PHASE 8 — Thống nhất đầu trang + dọn CSS chết

## 8.1. Phần A — Bốn tab không có tiêu đề

Hiện trạng 12 tab:

| Kiểu đầu trang | Tab |
|---|---|
| `.pageHeader` (h1 + phụ đề) | Nhân sự, Kỹ năng, Dự án, Phòng họp, Bộ não AI, Chi phí, Tài sản, Cài đặt |
| Chỉ có đồng hồ | Tổng quan (`OverviewPage.tsx:212`) |
| **Không có gì** | Dạy AI, Quy trình, Tác vụ tự động |

Ba tab cuối là trang standalone cũ được nhúng vào; header của chúng bị tắt khi
`embedded` (`WorkspacePage.tsx:390`, `TaskrunnerPage.tsx:91`) mà không có gì thay thế.
Chuyển tab là đổi hẳn ngôn ngữ thị giác.

### 8.1.a — Cách làm

Đặt tiêu đề ở **HubPage.tsx**, không phải trong từng trang con. Lý do: ba trang đó còn
route standalone riêng (`/workspace`, `/taskrunner`) và ở đó chúng dùng topbar của mình.
Sửa trong trang con sẽ làm hỏng bản standalone.

Trong `HubPage.tsx`, ở hàm `HubShell`, chỗ render `<section className={tabPanel...}>`:
với ba tab `train` / `company-runner` / `auto-runner`, chèn một header nhỏ **phía trên**
`<HubTabContent>`.

- Dùng đúng class `.pageHeader` đang có.
- Chuỗi lấy từ `hubText(language, "nav.train")` v.v. — **các key này đã có sẵn**
  trong `src/pages/hub/i18n.ts`, chính là nhãn đang hiện ở sidebar. **Không tạo key mới**
  cho tiêu đề; nếu muốn thêm phụ đề thì phải thêm key ở **cả hai** ngôn ngữ.
- Ba tab này dùng `.tabPanelFull` (`height:100%; overflow:hidden`). Chèn header vào sẽ
  ăn chiều cao của phần nội dung. **Phải** giữ phần nội dung ở `minmax(0, 1fr)` —
  kiểm bằng mắt là ô nhập tin nhắn ở đáy trang Dạy AI không bị đẩy ra khỏi màn hình.
  Nếu không cân được, **dừng lại và báo** thay vì tự đổi `.tabPanelFull`.

### 8.1.b — Tab Tổng quan

Thêm `<h1>` vào `.overviewHeader` cạnh đồng hồ. Key `hubText(language, "nav.home")` đã có.

### 8.1.c — Không được làm

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

Đi hết 12 tab. Mỗi tab **phải có một tiêu đề `<h1>` ở cùng vị trí, cùng cỡ chữ**.
Chuyển qua lại giữa `/hub/meeting` và `/hub/train` — không được thấy tiêu đề nhảy vị trí.

Ở `/hub/train`: kiểm ô nhập tin nhắn ở đáy **vẫn thấy được**, không bị đẩy khỏi màn hình.
Ở `/hub/company-runner`: mở một quy trình, kiểm canvas React Flow còn nguyên, minimap
và nút zoom vẫn chạy (chúng do React Flow vẽ, không phải các ID vừa xoá).

## 8.5. CHỐT PHASE 8

```
refactor(ui): thống nhất đầu trang 12 tab, dọn CSS chết

Ba tab Dạy AI / Quy trình / Tác vụ tự động là trang standalone cũ nhúng vào,
header của chúng bị tắt khi embedded mà không có gì thay thế; tab Tổng quan chỉ
có đồng hồ. Chuyển tab là đổi hẳn ngôn ngữ thị giác.

Đặt tiêu đề ở HubPage.tsx chứ không trong từng trang con, vì ba trang đó còn
route standalone riêng và ở đó chúng dùng topbar của mình. Chuỗi lấy từ key
nav.* đã có sẵn, không thêm key mới.

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

# PHỤ LỤC B — Bảng kiểm cuối, chạy sau khi cả 9 phase được duyệt

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
| Chữ trắng trên nền màu | 11 | 0 ngoài 3 nhóm miễn trừ |
| Hex bảng nâu-kem trong HubPage | 26 | 0 |
| Media query trong WorkspacePage | 0 | 2 |
| Khối `@media 720px` trong HubPage | 2 | 1 |
| Nhóm class chết trong HubPage | 9 | 0 |
| Khối luật ID chết trong Taskrunner | 10 | 0 |
| `:global(body)` trong CSS module | 4 | 0 |
| Tab có `<h1>` | 8/12 | 12/12 |

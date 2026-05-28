# BỘ CÂU HỎI KIỂM CHỨNG (multi-turn, tích lũy)

> Node tâm điểm **X** do script `build_answers.py` xác định (deterministic).
> Chạy script đó trước để biết X là node nào trong graph của bạn.
> **KHÔNG có đáp án trong file này** — đáp án do máy tự sinh, xem `build_answers.py`.

Đưa cho LLM **từng câu một, theo thứ tự**, mỗi câu kèm đúng MỘT biểu diễn
(`view_flat.txt` HOẶC `view_toc.txt` HOẶC `view_graph.txt`). Lượt sau giữ lại
lịch sử hỏi-đáp của lượt trước (đây là phần "tích lũy").

Yêu cầu LLM trả lời **chỉ bằng danh sách tên node**, mỗi dòng một tên, không giải thích.

---

**Q1 — tra cứu trực tiếp (tĩnh):**
Node X gọi TRỰC TIẾP những node nào? Liệt kê tên các node.

**Q2 — lọc theo điều kiện (dùng lại Q1):**
Trong các node vừa liệt kê ở Q1, node nào LẠI gọi tiếp từ 2 node trở lên?

**Q3 — bắc cầu + vòng (dùng lại Q2):**
Lần theo TIẾP từ các node ở Q2, những node nào nằm trong một VÒNG phụ thuộc
(cycle — tức có đường đi vòng lại chính nó)?

**Q4 — hội tụ (dùng lại Q2):**
Tập hợp TẤT CẢ các node mà các node ở Q2 gọi trực tiếp (bước kế tiếp) là gì?

---

## Quy tắc đo token (để so 3 biểu diễn công bằng)
- Cả 3 view dùng CÙNG bộ node. Khác biệt duy nhất: ToC bỏ cạnh, Graph giữ cạnh.
- Lượt 1: gửi nguyên view + câu hỏi. Đếm token đầu vào.
- Lượt 2–4: gửi lịch sử hỏi-đáp tích lũy + câu hỏi (KHÔNG gửi lại nguyên view).
  Với Flat/ToC, nếu LLM cần thêm ngữ cảnh node để suy ra quan hệ thì phần đó
  cũng tính vào token — đó chính là cái giá của việc không có cạnh.
- Ghi lại token_in mỗi lượt cho mỗi view → vẽ đường tích lũy.

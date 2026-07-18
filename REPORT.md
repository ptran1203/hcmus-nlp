# Báo cáo đồ án: Xây dựng ngữ liệu song song Hán – Việt chuyên ngành lịch sử Việt Nam

> Tài liệu này tổng hợp toàn bộ thông tin, số liệu và phân tích thu thập được trong quá trình xây dựng pipeline, theo đúng cấu trúc báo cáo yêu cầu, để làm cơ sở cho việc viết báo cáo hoàn chỉnh.

## 1. Giới thiệu

### Mục tiêu của đồ án
Xây dựng ngữ liệu song song (parallel corpus) Hán – Việt cho các văn bản lịch sử Việt Nam, phục vụ nghiên cứu NLP (dịch máy, học biểu diễn xuyên ngôn ngữ, v.v.) trong lĩnh vực lịch sử. Với mỗi tác phẩm, sản phẩm cuối cùng là tập hợp các cặp câu Hán – Việt đã được dóng hàng (aligned) kèm điểm tin cậy.

### Bài toán được giao
Theo đề bài gốc (mục "1. Requirements" trong `README.md`):
- Đầu vào dạng **Ảnh**: yêu cầu OCR → tách câu → dóng hàng.
- Đầu vào dạng **Text**: yêu cầu tách câu → dóng hàng.

Nhóm không bị giới hạn công cụ/mô hình, có thể chủ động lựa chọn hoặc kết hợp các phương pháp (OCR, tách câu, NER, dóng hàng bằng embedding/LLM...) miễn đạt chất lượng dữ liệu tốt nhất.

### Phạm vi dữ liệu và kết quả mong đợi
4 tác phẩm được giao (file Hán dạng `.txt`, file Việt dạng `.pdf`, tải từ Google Drive):

| Tác phẩm | Đầu vào Hán | Đầu vào Việt |
|---|---|---|
| Chiến Quốc Sách | Text (.txt) | **Ảnh quét, không có lớp text** |
| Liệt Nữ Truyện | Text (.txt) | PDF có lớp text |
| Sử Ký Tư Mã Thiên | Text (.txt) | PDF có lớp text |
| Tam Quốc Chí (三國志 — bản sử ký của Trần Thọ, không phải tiểu thuyết Tam Quốc Diễn Nghĩa) | Text (.txt) | PDF có lớp text |

Kết quả mong đợi cho mỗi tác phẩm: bộ 3 file sản phẩm cuối theo đúng định dạng yêu cầu (`<mã_tác_phẩm>_raw.txt`, `<mã_tác_phẩm>_parallel.tsv`, `<mã_tác_phẩm>_parallel.xlsx`) và báo cáo chất lượng tự động (`report.json`).

Link kết quả: https://drive.google.com/drive/folders/1xWxeJtNbRz1VZgQ4W1UHaTjeHzFCsuJF?usp=drive_link

## 2. Dữ liệu và công cụ sử dụng

### Mô tả dữ liệu đầu vào
- **Phía Hán**: file `.txt`, văn bản Hán cổ/văn ngôn đã có dấu câu (。！？，；：) khá đầy đủ do là bản phiên âm/đã biên tập (không phải văn bản gốc không dấu câu).
- **Phía Việt**: file `.pdf` là bản dịch tiếng Việt hiện đại. Một số PDF có lớp text nhúng sẵn (trích xuất trực tiếp được), một số là ảnh quét thuần túy (không có lớp text — cần OCR).

### Nguồn dữ liệu
Toàn bộ file được cung cấp qua Google Drive (link trong bảng dữ liệu của đề bài), tải tự động bằng script `00_download.py`.

### Các công cụ, thư viện, mô hình được sử dụng
| Công đoạn | Công cụ / thư viện |
|---|---|
| Tải dữ liệu | `gdown` (Google Drive) |
| Trích xuất text từ PDF | `PyMuPDF` (fitz) |
| OCR (khi PDF là ảnh quét, không có lớp text) | **EasyOCR** (phát hiện vùng chứa chữ, chạy trên GPU qua PyTorch) + **VietOCR** (nhận dạng ký tự, model Transformer huấn luyện riêng cho tiếng Việt — xem mục 3 và 5 về lý do không dùng PaddleOCR cho khâu này) |
| Tách câu tiếng Việt | `underthesea` (`sent_tokenize`) |
| Tách câu Hán | Luật tách dựa trên dấu câu `。！？` (tự viết, không cần model — xem phần 3) |
| Biểu diễn ngữ nghĩa câu (embedding) | `sentence-transformers`, hỗ trợ nhiều model và **ensemble** nhiều model cùng lúc: `paraphrase-multilingual-MiniLM-L12-v2` (mặc định, ~470MB), `sentence-transformers/LaBSE` (~1.8GB), `intfloat/multilingual-e5-large` (~2.2GB), `BAAI/bge-m3` (~2.3GB), `paraphrase-multilingual-mpnet-base-v2` (~1.1GB) |
| Thuật toán dóng hàng | Quy hoạch động (Dynamic Programming) đơn điệu theo phong cách Vecalign/Bertalign, tự cài đặt, có giới hạn băng (banded) để chạy được ở quy mô sách thật |
| Xuất kết quả | `pandas` + `openpyxl` (xuất `.xlsx`), `csv` (xuất `.tsv`) |

## 3. Quy trình thực hiện

### Mô tả tổng quan quy trình
Pipeline gồm 5 bước độc lập, mỗi bước là 1 script Python, đọc output của bước trước và ghi ra thư mục riêng dưới `dataset/`:

```
00_download → 01_clean → 02_segment → 03_align → 04_export
(tải file)    (làm sạch)  (tách câu)   (dóng hàng)  (xuất kết quả)
```

### Các bước thực hiện chính

**Bước 0 — Tải dữ liệu (`00_download.py`)**: tải `han.txt`/`viet.pdf` từ Google Drive cho từng tác phẩm, bỏ qua nếu đã tải, tự nhận diện loại file thực tế từ nội dung (kiểm tra header `%PDF`) thay vì tin vào header `Content-Disposition` của Drive (từng gây lỗi vì thư viện `gdown` cũ không xử lý được định dạng header mới của Drive — đã khắc phục bằng cách nâng cấp `gdown`).

**Bước 1 — Làm sạch (`01_clean.py`)**:
- Hán: thử nhiều encoding, chuẩn hóa Unicode, loại bỏ số trang lạc, tách đoạn theo dòng trống.
- Việt: trích xuất text từng trang PDF bằng PyMuPDF, làm sạch tương tự, giữ lại số trang gốc.
- **OCR tự động khi cần**: nếu một trang PDF không có lớp text (ảnh quét thuần túy — trường hợp của *Chiến Quốc Sách*), tự động OCR trang đó thay vì bỏ trống. Quy trình: (1) cắt bỏ 8% lề mỗi cạnh trước khi OCR (giảm nhiễu từ tiêu đề/số trang/mép đóng gáy); (2) **EasyOCR** phát hiện các vùng chứa dòng chữ trên trang; (3) mỗi vùng được cắt ảnh riêng và đưa qua **VietOCR** để nhận dạng ký tự (xem mục 5 về lý do chọn tổ hợp này thay vì PaddleOCR). Kết quả OCR của cả cuốn được lưu cache vào `<slug>/viet_raw.txt` cạnh file PDF gốc — vừa là sản phẩm `raw.txt` theo yêu cầu đề bài, vừa tránh phải chạy lại OCR (bước chậm nhất) mỗi lần chạy lại pipeline.
- **Loại trùng lặp (dedup)**: phát hiện và loại bỏ các đoạn văn bị lặp lại y hệt — phát hiện quan trọng: file `han.txt` của *Liệt Nữ Truyện* có khoảng 104 đoạn (tương ứng ~15% nội dung) bị lặp lại nguyên văn do lỗi từ công cụ trích xuất/OCR gốc tạo ra file. Đã xác minh bằng cách so sánh trực tiếp: cùng một câu mở đầu xuất hiện 15 lần, cách đều nhau ~7.643 ký tự trong phần đầu file.

**Bước 2 — Tách câu (`02_segment.py`)**: ghép toàn bộ các đoạn của một tác phẩm thành một chuỗi liên tục trước khi tách câu (tránh bug câu bị cắt ngang tại ranh giới trang PDF), sau đó tách câu theo ngôn ngữ:
- Hán: tách theo dấu câu kết thúc `。！？` — do văn bản đã có dấu câu dày đặc và nhất quán, không cần model.
- Việt: dùng `underthesea` — **không** tách theo dấu `.` đơn giản vì tiếng Việt dùng `.` cho nhiều mục đích khác (viết tắt, số thập phân/hàng nghìn, tên miền URL — từng gặp bug `underthesea` tự tách `nuduc.com` thành `nuduc.` / `com`), cần một tokenizer chuyên biệt để phân biệt.

**Bước 3 — Dóng hàng (`03_align.py`)**:
- Biểu diễn mỗi câu (và mỗi cụm tối đa 2 câu liên tiếp gộp lại) thành vector embedding bằng model đa ngôn ngữ.
- Hỗ trợ **ensemble** nhiều model: nối (concatenate) các vector embedding đã chuẩn hóa của từng model rồi chuẩn hóa lại — về mặt toán học tương đương lấy trung bình độ tương đồng cosine của từng model riêng lẻ, giúp giảm rủi ro một model bị "mù" ở trường hợp nào đó.
- Dùng **quy hoạch động đơn điệu** (monotonic DP) để tìm đường đi chi phí thấp nhất qua lưới Hán×Việt, cho phép ghép 1-1, 1-2, 2-1, 2-2 câu, hoặc bỏ qua (skip) câu không có tương ứng ở phía kia.
- **Giới hạn băng (banded DP)**: chỉ tính toán trong một dải quanh đường chéo kỳ vọng (câu Hán thứ *i* nên tương ứng khoảng vị trí *i×(m/n)* bên Việt) thay vì toàn bộ lưới *n×m* — bắt buộc phải làm vì một cuốn sách thật có hàng chục nghìn câu, bảng quy hoạch động đầy đủ cần hàng chục GB RAM (không khả thi).
- **Lọc kết quả** qua 3 tầng tự động: (1) điểm tương đồng dưới ngưỡng `--min-score`; (2) văn bản một trong hai phía quá ngắn (< 5 ký tự); (3) tỉ lệ độ dài Việt/Hán lệch quá 2 độ lệch chuẩn so với trung bình của chính tác phẩm đó.
- Xuất `dataset/aligned/<slug>.tsv` (đầy đủ cột: id câu, text, điểm số) và `report.json` (số liệu chất lượng tự động, xem mục 5).

**Bước 4 — Xuất kết quả (`04_export.py`)**: chuyển từ định dạng nội bộ sang đúng định dạng sản phẩm yêu cầu của đề bài (xem mục 4).

## 4. Kết quả đạt được

### Khối lượng dữ liệu xử lý (số liệu cụ thể, lấy từ `report.json` sau khi chạy đầy đủ pipeline cho cả 4/4 tác phẩm)

**Liệt Nữ Truyện**:
- Hán: 334 đoạn thô → loại 104 đoạn trùng lặp → 230 đoạn sạch → **2.604 câu**.
- Việt: 622 trang/đoạn (không trùng lặp) → **3.758 câu**. Tỉ lệ Hán:Việt ~0,69:1 (hợp lý, sau khi loại trùng lặp — trước đó là ~11:1 bất thường).
- Dóng hàng: **1.077 cặp giữ lại** / 841 cặp bị loại (769 do điểm thấp, 13 do quá ngắn, 59 do tỉ lệ độ dài bất thường). Điểm trung bình **0,6278** (khoảng 0,50–0,88).
- Kiểu ghép chủ yếu: 1-2 (1.154 lần), 2-2 (686 lần); hầu như không có câu Hán nào bị bỏ qua hoàn toàn (chỉ 28 câu Việt bị bỏ qua).

**Sử Ký Tư Mã Thiên**:
- Hán: **32.121 câu**. Việt: **6.063 câu** — tỉ lệ ~5,3:1, lệch nhiều hơn hẳn 2 tác phẩm còn lại.
- Dóng hàng: **3.619 cặp giữ lại** / 22.439 cặp bị loại (22.255 do điểm thấp — chiếm áp đảo). Điểm trung bình **0,622**.
- Kiểu ghép: gần như tuyệt đối chỉ có 2 dạng — **"2-1" xảy ra đúng 6.063 lần** (tức *mọi* câu Việt đều được ghép với đúng 2 câu Hán, không hơn không kém) và **"1-0" xảy ra 19.995 lần** (gần 62% tổng số câu Hán bị bỏ qua hoàn toàn, không ghép được với câu Việt nào). Đây là phát hiện đáng chú ý: mẫu hình đều tăm tắp "luôn luôn đúng 2 câu Hán" cho thấy giới hạn ghép tối đa `MAX_MERGE=2` đang là nút thắt thực sự với tác phẩm này — nhiều khả năng tương ứng thật cần gộp nhiều hơn 2 câu Hán cho một câu Việt, nhưng thuật toán bị chặn ở mức 2 nên đành bỏ qua phần dư thay vì ghép đúng.

**Tam Quốc Chí**:
- Hán: **36.337 câu**. Việt: **28.524 câu** — tỉ lệ ~1,27:1, cân đối hơn nhiều so với Sử Ký.
- Dóng hàng: **9.802 cặp giữ lại** / 8.488 cặp bị loại (8.065 do điểm thấp, 402 do tỉ lệ độ dài bất thường, 21 do quá ngắn). Điểm trung bình **0,6128**.
- Kiểu ghép đa dạng hơn Sử Ký: 2-2 (10.214 lần), 2-1 (7.833 lần), chỉ 82 câu Hán bị bỏ qua hoàn toàn.

**Chiến Quốc Sách** (file `viet.pdf` là ảnh quét thuần túy — PyMuPDF trích xuất được 0 ký tự trực tiếp, phải qua OCR — xem mục 3 và 5):
- Hán: **8.028 câu**. Việt (qua OCR): **4.771 câu** — tỉ lệ ~1,68:1.
- Dóng hàng: **2.619 cặp giữ lại** / 1.399 cặp bị loại (1.306 do điểm thấp, 78 do tỉ lệ độ dài bất thường, 15 do quá ngắn). Điểm trung bình **0,6509** — cao nhất trong 4 tác phẩm dù dữ liệu đầu vào đi qua OCR (không phải text gốc), một tín hiệu tích cực cho chất lượng OCR sau khi khắc phục vấn đề dấu thanh (mục 5).
- Kiểu ghép: chủ yếu 2-1 (3.257 lần), 2-2 (753 lần); **không có câu Hán nào bị bỏ qua hoàn toàn** — mọi câu Hán và câu Việt đều được dùng hết trong các cặp đã ghép.
- *Lưu ý*: lần chạy này dùng ngưỡng lọc `--min-score=0,6` (ngưỡng mặc định đã được nhóm điều chỉnh tăng so với 0,5 dùng cho 3 tác phẩm trước), nên điểm trung bình không hoàn toàn so sánh 1:1 với 3 tác phẩm kia.

**Tổng hợp cả 4/4 tác phẩm**: **17.117 cặp câu Hán–Việt** giữ lại sau lọc (14.498 từ 3 tác phẩm text gốc + 2.619 từ Chiến Quốc Sách qua OCR).

### Các sản phẩm đầu ra đã tạo
Theo đúng định dạng yêu cầu của đề bài, mỗi tác phẩm (khi đủ điều kiện) có 3 file trong `dataset/deliverables/`:
- `<mã_tác_phẩm>_raw.txt`: text thô trích xuất từ PDF trước khi làm sạch — với PDF có lớp text là trích xuất trực tiếp, với PDF ảnh quét (Chiến Quốc Sách) là kết quả OCR thô (EasyOCR + VietOCR).
- `<mã_tác_phẩm>_parallel.tsv`: cột `pair_id`, `han_sentence`, `viet_sentence`.
- `<mã_tác_phẩm>_parallel.xlsx`: cùng dữ liệu, định dạng Excel.

### Ví dụ minh họa kết quả
Một cặp câu dóng hàng đúng (Liệt Nữ Truyện, quyển 1 — chuyện Nga Hoàng/Nữ Anh):
- Hán: `有虞二妃者，帝堯之二女也。`
- Việt: (câu mở đầu truyện, mô tả hai người vợ vua Thuấn là con gái vua Nghiêu)

Một cặp câu **lỗi** được phát hiện thủ công khi rà soát nhanh kết quả (dùng làm ví dụ để cải tiến bộ lọc, xem mục 5):
- Hán: `號趙姬。` (chỉ 4 ký tự — một mảnh câu kiểu "được gọi là Triệu Cơ")
- Việt: `Triệu Cơ khuyên Triệu Thôi đón Triệu Thuẫn và mẹ về cùng sống chung. Triệu Thôi kiên quyết từ chối...` (một câu dài, nội dung không liên quan)
- Điểm số: 0,5303 — chỉ vừa vượt ngưỡng lọc mặc định 0,5, cho thấy ngưỡng điểm đơn thuần chưa đủ để loại các cặp vô lý về mặt cấu trúc.

## 5. Đánh giá và thảo luận

### Cách đánh giá kết quả
Theo yêu cầu của nhóm, việc đánh giá được thực hiện **hoàn toàn tự động** (không có bước rà soát thủ công theo mẫu), thông qua 3 nhóm chỉ số tính sẵn trong `report.json` cho từng tác phẩm và tổng hợp:
1. **`score_stats`**: phân phối điểm tương đồng cosine của các cặp câu giữ lại (min/median/mean/p10/p90/max) — cho biết độ tin cậy tổng thể và giúp chọn ngưỡng `--min-score` có căn cứ dữ liệu thay vì đoán.
2. **`merge_pattern_counts`**: thống kê các câu được ghép theo kiểu nào (1-1, 1-2, 2-1, 2-2, hoặc bị bỏ qua "1-0"/"0-1") — tỉ lệ ghép/bỏ qua cao bất thường là dấu hiệu cảnh báo vấn đề ở bước tách câu phía trước.
3. **`length_ratio_stats`**: tỉ lệ độ dài ký tự Việt/Hán của từng cặp — bản dịch thật thường nằm trong một khoảng tỉ lệ khá ổn định; cặp lệch xa mức trung bình là dấu hiệu tự động (không cần đọc hiểu nội dung) để nghi ngờ cặp bị dóng sai.

Ngoài 3 chỉ số thống kê trên, pipeline còn áp dụng **3 tầng lọc tự động** để loại các cặp khả nghi trước khi xuất kết quả cuối: điểm thấp, văn bản quá ngắn, và tỉ lệ độ dài bất thường (chi tiết ở mục 3).

### Kết quả đánh giá
Cả 4 tác phẩm đều cho điểm trung bình khá gần nhau (0,61–0,65 trên thang cosine similarity), kể cả tác phẩm duy nhất đi qua OCR — tín hiệu tích cực rằng OCR không làm giảm rõ rệt chất lượng dóng hàng so với các tác phẩm có text gốc:

| Tác phẩm | Câu Hán | Câu Việt | Tỉ lệ Hán:Việt | Cặp giữ lại | Điểm TB | % câu Hán bị bỏ qua hoàn toàn |
|---|---|---|---|---|---|---|
| Liệt Nữ Truyện | 2.604 | 3.758 | 0,69:1 | 1.077 | 0,628 | ~0% |
| Sử Ký Tư Mã Thiên | 32.121 | 6.063 | 5,3:1 | 3.619 | 0,622 | ~62% |
| Tam Quốc Chí | 36.337 | 28.524 | 1,27:1 | 9.802 | 0,613 | ~0,2% |
| Chiến Quốc Sách (qua OCR) | 8.028 | 4.771 | 1,68:1 | 2.619 | 0,651* | 0% |

*\* dùng ngưỡng lọc `--min-score=0,6` (cao hơn 0,5 dùng cho 3 tác phẩm kia), nên không hoàn toàn so sánh 1:1 — nhưng ngay cả điểm sàn (min) của tác phẩm này là 0,6, vẫn cao hơn median của 2 tác phẩm kia, nên tín hiệu "OCR không làm giảm chất lượng" vẫn đáng tin.*

Phát hiện đáng chú ý nhất: **Sử Ký Tư Mã Thiên** có tỉ lệ câu Hán:Việt lệch mạnh nhất (5,3:1) và cũng là tác phẩm duy nhất có tỉ lệ câu Hán bị bỏ qua hoàn toàn rất cao (~62%). Mẫu hình ghép của tác phẩm này gần như tuyệt đối chỉ gồm 2 dạng "2 Hán–1 Việt" hoặc "bỏ qua", không có ghép 1-1, 1-2, hay 2-2 nào — dấu hiệu rõ ràng cho thấy giới hạn ghép tối đa 2 câu (`MAX_MERGE=2`) không đủ để biểu diễn đúng tương ứng thực tế ở tác phẩm này. Ngược lại, *Tam Quốc Chí* và *Chiến Quốc Sách* có tỉ lệ câu cân đối hơn (1,27:1 và 1,68:1) nên tận dụng được nhiều kiểu ghép hơn (2-2, 2-1) và hầu như không bỏ qua câu Hán nào.

### OCR cho Chiến Quốc Sách: hành trình và lựa chọn công cụ
Đây là phần việc phát sinh nhiều nhất ngoài dự kiến ban đầu, đáng ghi nhận riêng:
1. **Thử PaddleOCR trước** (công cụ tham khảo trong đề bài) — vượt qua được nhiều lỗi tương thích phiên bản API (`show_log`, tham số `cls`, hàm `predict()`), nhưng khi chạy thật lại cho ra văn bản **thiếu dấu thanh/dấu phụ tiếng Việt tràn lan** (vd. "được" → "đưc", "của" → "ca", "Chiến Quốc" → "Chin Quc") — không phải lỗi ngẫu nhiên mà là hạn chế thực sự của model tiếng Việt trong PaddleOCR ở bản scan này.
2. **Chuyển sang VietOCR** (model Transformer huấn luyện chuyên biệt cho tiếng Việt, được cộng đồng NLP tiếng Việt đánh giá cao về độ chính xác dấu thanh) để làm khâu nhận dạng ký tự, giữ PaddleOCR chỉ để phát hiện vùng chứa chữ (khâu này không đòi hỏi hiểu tiếng Việt nên vẫn dùng được).
3. Quá trình cài đặt GPU cho PaddleOCR kéo theo một chuỗi lỗi xung đột thư viện (numpy 2.x không tương thích ngược với các extension biên dịch sẵn của `matplotlib`, `pycocotools`; rồi bản thân `paddleocr`/`paddlepaddle` không tương thích phiên bản với nhau) — nguyên nhân gốc: `paddleocr` bản mới kéo theo cả framework `paddlex` rất nặng và không liên quan (huấn luyện mô hình phân loại ảnh, phát hiện bất thường...), dễ vỡ.
4. **Quyết định cuối**: bỏ hẳn PaddleOCR, chuyển khâu phát hiện vùng chữ sang **EasyOCR** (dựa trên PyTorch — framework đã có sẵn và hoạt động ổn định trong pipeline nhờ bước dóng hàng bằng embedding), giữ VietOCR cho khâu nhận dạng. Tổ hợp này tránh hoàn toàn hệ sinh thái PaddlePaddle.
5. Sau khi đổi engine, còn phát hiện thêm: OCR đọc luôn cả tiêu đề đầu trang/lề sách (nhiễu không liên quan nội dung) → khắc phục bằng cách cắt bỏ 8% lề mỗi cạnh trước khi OCR.

Về ví dụ cụ thể ở mục 4: cặp lỗi "號趙姬。" minh họa rằng ngưỡng điểm đơn thuần chưa đủ để loại các cặp vô lý về mặt cấu trúc — sau khi bổ sung bộ lọc độ dài tối thiểu và tỉ lệ bất thường, các trường hợp lỗi rõ ràng dạng này đã bị loại tự động (riêng Liệt Nữ Truyện: 13 cặp bị loại vì quá ngắn, 59 cặp vì tỉ lệ độ dài bất thường).

### Những vấn đề gặp phải
1. Một số PDF tiếng Việt là ảnh quét, không trích xuất được text trực tiếp — cần OCR (đã giải quyết, xem mục "OCR cho Chiến Quốc Sách" ở trên); công cụ OCR ban đầu chọn (PaddleOCR) cho kết quả thiếu dấu thanh tiếng Việt nghiêm trọng, phải đổi engine.
2. File nguồn tiếng Hán của một tác phẩm (Liệt Nữ Truyện) có nội dung bị lặp lại do lỗi từ quá trình tạo file gốc.
3. Số lượng câu Hán và câu Việt sau tách câu không cân xứng (một câu Việt thường tương ứng nhiều câu/mệnh đề Hán) — mức độ lệch khác nhau rõ rệt giữa các tác phẩm (0,69:1 đến 5,3:1).
4. Một bảng quy hoạch động đầy đủ (không giới hạn) không khả thi về bộ nhớ/thời gian ở quy mô một cuốn sách thật.
5. Một số cặp câu được dóng hàng dù điểm số vượt ngưỡng lọc vẫn không hợp lý về nội dung khi kiểm tra nhanh bằng mắt.
6. Với *Sử Ký Tư Mã Thiên* (tỉ lệ Hán:Việt lệch nhất, 5,3:1), gần 62% số câu Hán bị thuật toán bỏ qua hoàn toàn, mẫu hình ghép gần như chỉ có đúng 1 dạng cố định ("2 Hán–1 Việt") — cho thấy giới hạn ghép tối đa 2 câu không đủ để biểu diễn đúng tương ứng thực tế của tác phẩm này.
7. Chưa có tập mẫu đã được kiểm chứng thủ công (gold sample) để tính được một con số độ chính xác (precision) thực sự — các chỉ số hiện tại chỉ mang tính tương đối/tự đối chiếu (self-consistency), không phải con số đã được hiệu chuẩn.

### Phân tích nguyên nhân
1. Ảnh quét: do bản số hóa gốc của một số tác phẩm chỉ là ảnh chụp/scan trang sách, không có lớp văn bản đi kèm. Việc PaddleOCR cho kết quả thiếu dấu thanh tiếng Việt là do model tiếng Việt tổng quát của PaddleOCR chưa đủ mạnh cho font/chất lượng scan của tác phẩm này — khắc phục bằng cách dùng VietOCR, model huấn luyện chuyên biệt cho tiếng Việt.
2. Nội dung trùng lặp: xác minh trực tiếp cho thấy một đoạn văn bản (câu mở đầu truyện đầu tiên) lặp lại y hệt 15 lần, cách đều nhau về khoảng cách ký tự — nhiều khả năng do một vòng lặp lỗi trong công cụ trích xuất/OCR ban đầu (không phải lỗi từ pipeline của nhóm).
3. Mất cân xứng số câu: do quy ước dấu câu của Hán cổ (`。`) được dùng để ngăn cách mệnh đề nhiều hơn là ngăn cách câu hoàn chỉnh theo kiểu phương Tây, trong khi bản dịch tiếng Việt thường gộp nhiều mệnh đề Hán thành một câu hoàn chỉnh, mạch lạc hơn. Mức độ này khác nhau theo văn phong từng tác phẩm/dịch giả — Sử Ký (văn phong cô đọng, nhiều mệnh đề ngắn) lệch nhiều hơn Tam Quốc Chí.
4. Giới hạn bộ nhớ/thời gian: một bảng quy hoạch động kích thước *n×m* với *n, m* ở mức hàng chục nghìn cần bộ nhớ tỉ lệ thuận *n×m* — vượt xa khả năng máy tính thông thường.
5. Cặp lỗi vượt ngưỡng điểm: bộ lọc theo điểm tương đồng đơn thuần không đủ để phát hiện các cặp mất cân đối cấu trúc rõ rệt (một mảnh câu 4 ký tự ghép với một câu dài gấp hơn 30 lần); ngoài ra, việc phạt (penalty) cho hành động "bỏ qua một câu" trong thuật toán từng được đặt hơi cao, khiến thuật toán có xu hướng luôn cố ghép mọi câu Hán vào đâu đó thay vì bỏ qua khi không có tương ứng thật sự.
6. Sử Ký Tư Mã Thiên bỏ qua nhiều câu Hán: khi tỉ lệ Hán:Việt thực tế của một đoạn vượt quá mức 2:1 mà `MAX_MERGE` cho phép, thuật toán buộc phải chọn giữa ghép sai (gộp chỉ 2 trong số nhiều câu Hán cần thiết) hoặc bỏ qua phần dư — với văn phong cô đọng của Sử Ký, tình huống này xảy ra rất thường xuyên, dẫn đến tỉ lệ bỏ qua cao bất thường so với 2 tác phẩm còn lại.
7. Thiếu tập mẫu kiểm chứng: do phạm vi thời gian của đồ án và lựa chọn ưu tiên đánh giá tự động, chưa dành thời gian tạo một mẫu nhỏ được gán nhãn thủ công để hiệu chuẩn các chỉ số tự động về một con số độ chính xác thực sự.

## 6. Kết luận và hướng phát triển

### Những nội dung đã hoàn thành
- Xây dựng hoàn chỉnh pipeline 5 bước (tải dữ liệu → làm sạch (kèm OCR tự động khi cần) → tách câu → dóng hàng → xuất kết quả), chạy thành công từ đầu đến cuối cho **cả 4/4 tác phẩm** được giao — tổng cộng **17.117 cặp câu Hán–Việt** đã được dóng hàng và xuất ra.
- Xây dựng khâu OCR cho tác phẩm có đầu vào ảnh (Chiến Quốc Sách): phát hiện vùng chữ bằng EasyOCR, nhận dạng ký tự bằng VietOCR (model chuyên biệt cho tiếng Việt) sau khi phát hiện PaddleOCR cho kết quả thiếu dấu thanh; kết quả OCR được cache thành file `raw.txt` để không phải chạy lại.
- Tự động xử lý các vấn đề chất lượng dữ liệu phát sinh: mã hóa văn bản không đồng nhất, nội dung trùng lặp, câu bị cắt ngang tại ranh giới trang.
- Xây dựng module tách câu có thể thay thế được (Hán: luật dấu câu; Việt: `underthesea`).
- Xây dựng thuật toán dóng hàng dựa trên embedding + quy hoạch động đơn điệu, có giới hạn băng để chạy được ở quy mô thật, hỗ trợ dùng nhiều model cùng lúc (ensemble).
- Xây dựng hệ thống đánh giá chất lượng tự động (không cần rà soát thủ công) và 3 tầng lọc cặp câu khả nghi.
- Xuất kết quả đúng định dạng yêu cầu của đề bài cho cả 4 tác phẩm.

### Những hạn chế còn tồn tại
- Chưa có tập mẫu đã kiểm chứng thủ công để hiệu chuẩn độ chính xác thực sự của các chỉ số tự động — kể cả độ chính xác của chính bước OCR (chỉ kiểm tra bằng mắt một số trang, chưa đo tỉ lệ lỗi ký tự có hệ thống).
- Giới hạn ghép tối đa 2 câu mỗi phía (`MAX_MERGE=2`) là nút thắt rõ rệt với các tác phẩm có văn phong Hán cô đọng — thể hiện rõ nhất ở Sử Ký Tư Mã Thiên, nơi gần 62% câu Hán bị bỏ qua hoàn toàn vì tương ứng thực tế cần gộp nhiều hơn 2 câu.
- Hướng cải tiến tiềm năng đã xác định nhưng chưa triển khai: tách văn bản theo cấu trúc chương/mục có sẵn (ví dụ Liệt Nữ Truyện có ~104 mục truyện đánh số rõ ràng) để dóng hàng theo từng mục nhỏ trước, giúp giảm cả vấn đề mất cân xứng số câu lẫn giới hạn tài nguyên tính toán — tuy nhiên cấu trúc này không đồng nhất giữa các tác phẩm nên cần xử lý riêng cho từng cuốn; cũng có thể cân nhắc tăng `MAX_MERGE` (đánh đổi thời gian chạy) riêng cho các tác phẩm văn phong cô đọng như Sử Ký.
- Thuật toán quy hoạch động giới hạn băng (banded DP) có thể bỏ sót một số trường hợp dóng hàng đúng nếu nội dung thực sự cần "nhảy" xa khỏi đường chéo tỉ lệ kỳ vọng (ví dụ một khối nội dung lớn chỉ có ở một phía ngôn ngữ).

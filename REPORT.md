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

| Tác phẩm | Đầu vào Hán | Đầu vào Việt | Tình trạng |
|---|---|---|---|
| Chiến Quốc Sách | Text (.txt) | **Ảnh quét, không có lớp text** | Bị chặn — cần OCR (chưa triển khai) |
| Liệt Nữ Truyện | Text (.txt) | PDF có lớp text | Đã chạy hết pipeline (end-to-end) |
| Sử Ký Tư Mã Thiên | Text (.txt) | PDF có lớp text | Mới tải/làm sạch, chưa rà soát kỹ |
| Tam Quốc Chí (三國志 — bản sử ký của Trần Thọ, không phải tiểu thuyết Tam Quốc Diễn Nghĩa) | Text (.txt) | PDF có lớp text | Mới làm sạch xong (bước Clean), chưa tách câu/dóng hàng |

Kết quả mong đợi cho mỗi tác phẩm: bộ 3 file sản phẩm cuối theo đúng định dạng yêu cầu (`<mã_tác_phẩm>_raw.txt`, `<mã_tác_phẩm>_parallel.tsv`, `<mã_tác_phẩm>_parallel.xlsx`) và báo cáo chất lượng tự động (`report.json`).

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

### Khối lượng dữ liệu xử lý (số liệu cụ thể)

**Liệt Nữ Truyện** (đã chạy hết pipeline):
- Hán: 334 đoạn thô → loại 104 đoạn trùng lặp → 230 đoạn sạch → **2.604 câu** sau tách câu.
- Việt: 622 trang/đoạn (không có trùng lặp) → **3.758 câu** sau tách câu.
- Tỉ lệ câu Hán:Việt trước khi loại trùng lặp: ~11:1 (bất thường); sau khi loại trùng lặp: ~0,7:1 (hợp lý hơn nhiều).
- Kết quả dóng hàng (trước khi bổ sung 2 bộ lọc mới ở bước 3): 1.149–1.314 cặp câu giữ lại tùy cấu hình model, điểm trung bình ~0,59–0,63 (thang tương đồng cosine, không phải % chính xác).

**Tam Quốc Chí** (mới xong bước Clean):
- Hán: 155 đoạn thô → loại 10 đoạn trùng lặp → 145 đoạn (văn bản có cấu trúc đoạn rất thô — trung bình ~6.700 ký tự/đoạn, vì đây là các khối văn bản lớn như biểu tấu/lời tựa/truyện dài, khác hẳn kiểu chia đoạn nhỏ của Liệt Nữ Truyện).
- Việt: 1.451 trang → loại 6 đoạn trùng lặp → 1.445 đoạn.
- *Lưu ý*: số đoạn Hán/Việt chênh lệch lớn (145 so với 1.445) không phải là dấu hiệu lỗi — chỉ phản ánh cách chia đoạn khác nhau giữa 2 định dạng nguồn (file text chia theo dòng trống thô, PDF chia theo trang); điểm so sánh có ý nghĩa thực sự là **số câu** sau bước tách câu, giống trường hợp Liệt Nữ Truyện.
- Chưa chạy bước tách câu và dóng hàng.

**Chiến Quốc Sách**: bị chặn hoàn toàn ở bước dữ liệu đầu vào — file `viet.pdf` là ảnh quét thuần túy (xác minh: PyMuPDF trích xuất được 0 ký tự trên toàn bộ trang), cần OCR mà pipeline hiện chưa triển khai.

**Sử Ký Tư Mã Thiên**: đã đưa vào lệnh chạy cùng đợt với Tam Quốc Chí nhưng số liệu cụ thể chưa được kiểm tra/ghi nhận trong quá trình làm việc này.

### Các sản phẩm đầu ra đã tạo
Theo đúng định dạng yêu cầu của đề bài, mỗi tác phẩm (khi đủ điều kiện) có 3 file trong `dataset/deliverables/`:
- `<mã_tác_phẩm>_raw.txt`: text thô trích xuất từ PDF (trước khi làm sạch) — chỉ xuất khi PDF thực sự có lớp text; nếu là ảnh quét (chưa OCR) sẽ cảnh báo và bỏ qua thay vì ghi file rỗng.
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
Với *Liệt Nữ Truyện* (ví dụ số liệu điển hình, trước khi bổ sung 2 bộ lọc mới): điểm trung bình các cặp giữ lại ~0,6277 (thang cosine similarity, khoảng dao động thường gặp cho cặp dịch thật là 0,5–0,9); phần lớn cặp được ghép theo kiểu 1-2 hoặc 2-2 (do một câu Hán thường ngắn/rời rạc hơn một câu Việt tương ứng); có tới 59 cặp lệch tỉ lệ độ dài quá 2 độ lệch chuẩn — sau khi bổ sung bộ lọc độ dài tối thiểu và tỉ lệ bất thường, các trường hợp lỗi rõ ràng như ví dụ "號趙姬。" ở mục 4 đã bị loại tự động.

### Những vấn đề gặp phải
1. Một số PDF tiếng Việt là ảnh quét, không trích xuất được text trực tiếp.
2. File nguồn tiếng Hán của một tác phẩm (Liệt Nữ Truyện) có nội dung bị lặp lại do lỗi từ quá trình tạo file gốc.
3. Số lượng câu Hán và câu Việt sau tách câu không cân xứng (một câu Việt thường tương ứng nhiều câu/mệnh đề Hán).
4. Một bảng quy hoạch động đầy đủ (không giới hạn) không khả thi về bộ nhớ/thời gian ở quy mô một cuốn sách thật.
5. Một số cặp câu được dóng hàng dù điểm số vượt ngưỡng lọc vẫn không hợp lý về nội dung khi kiểm tra nhanh bằng mắt.
6. Chưa có tập mẫu đã được kiểm chứng thủ công (gold sample) để tính được một con số độ chính xác (precision) thực sự — các chỉ số hiện tại chỉ mang tính tương đối/tự đối chiếu (self-consistency), không phải con số đã được hiệu chuẩn.

### Phân tích nguyên nhân
1. Ảnh quét: do bản số hóa gốc của một số tác phẩm chỉ là ảnh chụp/scan trang sách, không có lớp văn bản đi kèm.
2. Nội dung trùng lặp: xác minh trực tiếp cho thấy một đoạn văn bản (câu mở đầu truyện đầu tiên) lặp lại y hệt 15 lần, cách đều nhau về khoảng cách ký tự — nhiều khả năng do một vòng lặp lỗi trong công cụ trích xuất/OCR ban đầu (không phải lỗi từ pipeline của nhóm).
3. Mất cân xứng số câu: do quy ước dấu câu của Hán cổ (`。`) được dùng để ngăn cách mệnh đề nhiều hơn là ngăn cách câu hoàn chỉnh theo kiểu phương Tây, trong khi bản dịch tiếng Việt thường gộp nhiều mệnh đề Hán thành một câu hoàn chỉnh, mạch lạc hơn.
4. Giới hạn bộ nhớ/thời gian: một bảng quy hoạch động kích thước *n×m* với *n, m* ở mức hàng chục nghìn cần bộ nhớ tỉ lệ thuận *n×m* — vượt xa khả năng máy tính thông thường.
5. Cặp lỗi vượt ngưỡng điểm: bộ lọc theo điểm tương đồng đơn thuần không đủ để phát hiện các cặp mất cân đối cấu trúc rõ rệt (một mảnh câu 4 ký tự ghép với một câu dài gấp hơn 30 lần); ngoài ra, việc phạt (penalty) cho hành động "bỏ qua một câu" trong thuật toán từng được đặt hơi cao, khiến thuật toán có xu hướng luôn cố ghép mọi câu Hán vào đâu đó thay vì bỏ qua khi không có tương ứng thật sự.
6. Thiếu tập mẫu kiểm chứng: do phạm vi thời gian của đồ án và lựa chọn ưu tiên đánh giá tự động, chưa dành thời gian tạo một mẫu nhỏ được gán nhãn thủ công để hiệu chuẩn các chỉ số tự động về một con số độ chính xác thực sự.

## 6. Kết luận và hướng phát triển

### Những nội dung đã hoàn thành
- Xây dựng hoàn chỉnh pipeline 5 bước (tải dữ liệu → làm sạch → tách câu → dóng hàng → xuất kết quả), chạy được từ đầu đến cuối cho ít nhất 1 tác phẩm (Liệt Nữ Truyện).
- Tự động xử lý các vấn đề chất lượng dữ liệu phát sinh: mã hóa văn bản không đồng nhất, nội dung trùng lặp, câu bị cắt ngang tại ranh giới trang.
- Xây dựng module tách câu có thể thay thế được (Hán: luật dấu câu; Việt: `underthesea`).
- Xây dựng thuật toán dóng hàng dựa trên embedding + quy hoạch động đơn điệu, có giới hạn băng để chạy được ở quy mô thật, hỗ trợ dùng nhiều model cùng lúc (ensemble).
- Xây dựng hệ thống đánh giá chất lượng tự động (không cần rà soát thủ công) và 3 tầng lọc cặp câu khả nghi.
- Xuất kết quả đúng định dạng yêu cầu của đề bài.

### Những hạn chế còn tồn tại
- **OCR chưa được triển khai** → Chiến Quốc Sách (và có thể một phần các tác phẩm khác) chưa thể xử lý được.
- Sử Ký Tư Mã Thiên và Tam Quốc Chí chưa được chạy hết pipeline / rà soát kỹ trong phạm vi công việc này.
- Chưa có tập mẫu đã kiểm chứng thủ công để hiệu chuẩn độ chính xác thực sự của các chỉ số tự động.
- Giới hạn ghép tối đa 2 câu mỗi phía (`MAX_MERGE=2`) vẫn chưa đủ với các đoạn hội thoại có nhiều lượt lời ngắn liên tiếp phía Hán.
- Hướng cải tiến tiềm năng đã xác định nhưng chưa triển khai: tách văn bản theo cấu trúc chương/mục có sẵn (ví dụ Liệt Nữ Truyện có ~104 mục truyện đánh số rõ ràng) để dóng hàng theo từng mục nhỏ trước, giúp giảm cả vấn đề mất cân xứng số câu lẫn giới hạn tài nguyên tính toán — tuy nhiên cấu trúc này không đồng nhất giữa các tác phẩm nên cần xử lý riêng cho từng cuốn.
- Thuật toán quy hoạch động giới hạn băng (banded DP) có thể bỏ sót một số trường hợp dóng hàng đúng nếu nội dung thực sự cần "nhảy" xa khỏi đường chéo tỉ lệ kỳ vọng (ví dụ một khối nội dung lớn chỉ có ở một phía ngôn ngữ).


## 1. Requirements:
**HVB**

Xây dựng ngữ liệu song song Hán - Việt chuyên ngành lịch sử VN
- a. Đầu vào Ảnh: Yêu cầu OCR, tách câu, dóng hàng
- b. Đầu vào Text: Yêu cầu tách câu và dóng hàng

## 2. Tools:
Không giới hạn công cụ, mô hình hay phương pháp thực hiện. Nhóm có thể
chủ động lựa chọn, kết hợp hoặc đề xuất các giải pháp phù hợp nhằm đạt chất
lượng dữ liệu tốt nhất. Một số công cụ tham khảo:
● OCR: KanDianGuJi, PaddleOCR, Google Vision OCR, ChatGPT,
Gemini...
● Hiệu đính OCR: ChatGPT, Gemini, DeepSeek, Qwen...
● Tách câu: Underthesea, VnCoreNLP... hoặc các phương pháp dựa trên
LLM.
● NER: PhoBERT, HanLP, CKIP hoặc các mô hình LLM...
● Dóng hàng: BERTAlign, LaBSE, Vecalign, SimAlign hoặc các phương
pháp dựa trên embedding/LLM.

## 3. Dataset:

| Book | Han | Vietnamese |
|------|-----|------------|
| Chiến Quốc Sách | [Han](https://drive.google.com/file/d/1mI0pRTRAKs9uOY16vPo5PJBtNeB1vO5N/view) | [Viet](https://drive.google.com/file/d/1lPYxr1j7dy5rziCDyd94uWNPWbFXE2YM/view?usp=drive_link) |
| Liệt Nữ Truyện | [Han](https://drive.google.com/file/d/1sUM_MNpThyFammF7BC45XdCINemgu8eK/view) | [Viet](https://drive.google.com/file/d/10bXyKWCuGFqZQjybfuUbI1R6sEM6rTg0/view?usp=drive_link) |
| Sử Ký Tư Mã Thiên | [Han](https://drive.google.com/file/d/1S5ijemxpcQulqKFPIl0VC2_reZQXN3kM/view) | [Viet](https://drive.google.com/file/d/1AF87BbpWObUDdS4vIyDXVJnvAZmS0OYg/view?usp=drive_link) |
| Tam Quốc Chí | [Han](https://drive.google.com/file/d/1-RuBLkFIsIdk9_rbH9LQtnNn2n0hdEmk/view) | [Viet](https://drive.google.com/file/d/1yAHRP3x-sXDtleikiThq_ntAIKK5IllH/view?usp=drive_link) |


## Works

### Person 1 — Data Collection & Cleaning

Collect Han + Viet parallel text sources (historical domain)
Clean raw text: remove noise, normalize encoding (UTF-8), fix formatting
Deliverable: clean raw text pairs

### Person 2 — Sentence Segmentation

Split Han text into sentences (HanLP / CKIP / LLM)
Split Viet text into sentences (Underthesea / VnCoreNLP / LLM)
NER tagging to assist alignment accuracy
Deliverable: segmented sentence lists for both languages

### Person 3 — Alignment & Evaluation

Align Han-Viet sentence pairs (LaBSE / Vecalign / BERTAlign)
Filter low-confidence pairs, manually review edge cases
Export final corpus (TSV/JSON) + quality metrics
Deliverable: final parallel dataset + evaluation report

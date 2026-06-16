# UGC Backend — API & Logic nghiệp vụ

Đây là service **backend** của NodeZ Hub — trung tâm xử lý nghiệp vụ và là nguồn dữ liệu cho toàn hệ thống. Frontend và agents đều làm việc thông qua API của backend.

Backend điều phối toàn bộ vòng đời nội dung UGC: từ lúc creator soạn bài, qua kiểm duyệt, đến nghiệm thu và sẵn sàng thanh toán.

## Backend quản lý những gì

### Người dùng & phân quyền
- Bốn vai trò: **Quản trị cấp cao, Quản trị viên, Nhà kiểm duyệt (QC), Nhà sáng tạo (Creator)**.
- Đăng ký, đăng nhập, phân quyền chi tiết theo vai trò.
- Hồ sơ creator (thông tin cá nhân, giấy tờ, tài khoản ngân hàng) phục vụ nghiệm thu & thanh toán.

### Nội dung & bài viết
- Quản lý không gian làm việc (workspace) và bài viết của creator.
- Vòng đời bài viết: *nháp → chờ duyệt → có góp ý → đã sửa → được duyệt / bị từ chối*.
- **Tự động lấy số liệu từ link bài đăng** (lượt xem, thích, bình luận, chia sẻ) trên các nền tảng mạng xã hội — không cần nhập tay.

### Kiểm duyệt (QC)
- Hàng chờ kiểm duyệt, cơ chế nhận bài về cho từng QC.
- Hệ thống góp ý gắn theo vị trí trong bài, trao đổi qua lại giữa QC và creator.
- Công bố vòng góp ý, quyết định duyệt / từ chối (kèm lý do).
- Kết nối dịch vụ AI để chấm bài theo bộ tiêu chí.

### Biên bản nghiệm thu (BBNT) & thanh toán
- Tạo biên bản nghiệm thu theo kỳ (tháng) cho từng creator, dựa trên các bài đã được duyệt.
- Tính toán tài chính: đơn giá, số lượng bài, thuế, số tiền cuối cùng — kết xuất ra file Word theo mẫu.
- Vòng đời báo cáo: *nháp → creator nộp ảnh & gửi duyệt → admin chốt → bản chính*.
- **Quy tắc tính thưởng linh hoạt:** admin định nghĩa quy tắc (qua dịch vụ AI biên dịch) để điều chỉnh thưởng theo hiệu quả bài viết.

### Thông báo & email
- Thông báo trong ứng dụng cho các sự kiện quan trọng (có góp ý, được duyệt, bị từ chối, creator gửi lại bài).
- Gửi email tự động cho creator khi bài được công bố góp ý, được duyệt hoặc bị từ chối.

### Thống kê
- Tổng hợp số liệu phục vụ dashboard của admin: số bài theo trạng thái, khối lượng & hiệu suất từng QC, hoạt động theo creator/sản phẩm/thời gian.

### Tích hợp AI
- Tiếp nhận và lưu kết quả từ service **agents**: gợi ý kiểm duyệt theo tiêu chí, và biên dịch quy tắc nghiệm thu do admin viết.

## Vai trò & quyền truy cập

| Vai trò | Làm được gì |
|---|---|
| **Quản trị cấp cao** | Toàn quyền hệ thống |
| **Quản trị viên** | Quản lý người dùng, tạo & chốt báo cáo, cấu hình quy tắc, xem thống kê |
| **Nhà kiểm duyệt (QC)** | Kiểm duyệt bài, góp ý, duyệt/từ chối |
| **Nhà sáng tạo (Creator)** | Soạn bài, gửi duyệt, phản hồi góp ý, xem báo cáo của mình |

## Luồng nghiệp vụ end-to-end

```
1. Creator soạn bài → nộp link → gửi duyệt
2. QC nhận bài → góp ý → công bố
3. Creator sửa → gửi lại
4. QC duyệt / từ chối  (gửi email cho creator)
5. Hệ thống lấy số liệu bài đã đăng
6. Admin tạo Biên bản nghiệm thu theo kỳ (áp dụng quy tắc thưởng)
7. Creator nộp ảnh chứng minh & xem báo cáo
8. Admin chốt báo cáo → sẵn sàng thanh toán
```

## Liên kết trong hệ thống

Backend phục vụ dữ liệu cho **frontend** và là nguồn số liệu cho **agents**.

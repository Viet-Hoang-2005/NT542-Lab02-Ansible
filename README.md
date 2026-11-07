# Lab Ansible với hai router MikroTik trên EVE-NG

Lab dùng Ansible để cấu hình hai router CHR, thu thập cấu hình và đo tài nguyên, độ trễ và mất gói. Control node là Ubuntu 20.04; router chạy RouterOS 7.16.1 trong EVE-NG.

```text
 Ubuntu / Ansible 192.168.126.131
              |
   VMnet8 / EVE Management Cloud0
        |                |
 R1 ether1           R2 ether1
 192.168.126.11      192.168.126.12
        |                |
 R1 ether2 ---------- R2 ether2
 10.12.0.1/30        10.12.0.2/30
 lo 10.255.0.1/32    lo 10.255.0.2/32
```

Mỗi router có route tĩnh tới loopback của router kia qua `ether2`. Ping giữa hai loopback sử dụng loopback nguồn để kiểm tra cả tuyến đi lẫn tuyến về. Ping từ Ubuntu tới `ether1` kiểm tra mạng quản lý.

## Chuẩn bị

1. Bật EVE-NG, Ubuntu và hai router; nối `ether2` của R1 với `ether2` của R2 trong EVE. Xác nhận Ubuntu ping và SSH được tới `192.168.126.11` và `192.168.126.12`.
2. Trên Ubuntu, đồng bộ code bằng Git và kích hoạt venv (xem [INSTALL.md](INSTALL.md)):

   ```bash
   cd ~/Downloads/NT542-Lab02-Ansible
   git pull --ff-only
   source .venv-ansible/bin/activate
   python -m pip install -r requirements.txt
   ansible-galaxy collection install -r requirements.yml
   ```

3. Đăng nhập thủ công `ssh admin@192.168.126.11` và `.12` một lần, xác minh fingerprint trước khi chấp nhận host key. Inventory không chứa mật khẩu; Ansible sẽ hỏi mật khẩu SSH qua `-k`.
4. Kiểm tra không có xung đột địa chỉ `10.12.0.0/30` và `10.255.0.0/32`–`10.255.0.2/32`; địa chỉ minh họa có thể điều chỉnh trong `host_vars/`.

Ansible dùng tên đăng nhập `admin+cet1024w`: phần `+cet1024w` là tùy chọn terminal của RouterOS, giúp tránh màu và xuống dòng giữa dữ liệu JSON; tài khoản thực vẫn là `admin`.

## Chạy toàn bộ

Từ thư mục dự án Ubuntu, sau khi kích hoạt venv:

```bash
ansible-inventory --graph
ansible-playbook --syntax-check site.yml
ansible-playbook site.yml -k
```

Chuỗi chạy: kiểm tra điều kiện → export trước → cấu hình → export sau → thu thập → tạo báo cáo. Nếu preflight phát hiện một router lỗi hoặc xung đột, playbook bỏ qua cấu hình cả hai router, tiếp tục thu thập phần có thể đọc và báo cáo lỗi. Thao tác cấu hình chạy lần lượt từng router; chạy lại không tạo IP hoặc route trùng.

## Chạy từng bước

Dùng cùng `lab_run_id` để các bước ghi vào một thư mục. ID phải duy nhất cho mỗi lượt mới:

```bash
LAB_RUN_ID="$(date -u +%Y%m%dT%H%M%S.%NZ)"
ansible-playbook playbooks/preflight.yml -k -e "lab_run_id=$LAB_RUN_ID"
ansible-playbook playbooks/backup.yml -k -e "lab_run_id=$LAB_RUN_ID" -e backup_phase=before
ansible-playbook playbooks/configure.yml -k -e "lab_run_id=$LAB_RUN_ID"
ansible-playbook playbooks/backup.yml -k -e "lab_run_id=$LAB_RUN_ID" -e backup_phase=after
ansible-playbook playbooks/collect.yml -k -e "lab_run_id=$LAB_RUN_ID"
ansible-playbook playbooks/report.yml -e "lab_run_id=$LAB_RUN_ID"
```

`configure.yml` tự chạy lại preflight để các bước riêng lẻ cũng an toàn. Không đặt `lab_run_id` thì mỗi lệnh độc lập tạo lượt mới. `--syntax-check` chỉ kiểm tra cú pháp; không dùng `--check` để thay thế kiểm thử cấu hình vì module CLI không hỗ trợ đầy đủ check mode.

## Kết quả và cách đọc

Thư mục `artifacts/<run_id>/` gồm export `R1/R2-before.rsc`, `-after.rsc`, `-collected.rsc`, JSON thông số và đầu ra CLI gốc, `summary.csv` cùng `report.md`. Nếu chạy riêng `collect.yml`, chỉ có bản `-collected.rsc`. Nếu một router không phản hồi, phần thu thập vẫn lưu kết quả của router còn lại; báo cáo thể hiện dữ liệu thiếu và kiểm tra tổng thể thất bại.

Facts cho biết CPU, uptime, RAM và đĩa tại thời điểm đo. Mỗi ping gửi 5 gói, báo số gửi/nhận, mất gói và RTT min/avg/max (ms). Đây không phải phép đo băng thông hay giám sát liên tục. So sánh export trước/sau để trình bày thay đổi; dữ liệu không chứng minh Ansible làm router nhanh hơn.

Export `/export` không dùng `show-sensitive`, nên không chứa đầy đủ mật khẩu và không thay thế binary backup. File kết quả có thể chứa IP hoặc thông tin mạng, được đặt quyền riêng tư và bị Git bỏ qua.

## Cấu trúc và kiểm thử

- `inventory.ini`, `group_vars/`, `host_vars/`: thiết bị và giá trị mong muốn.
- `site.yml` và `playbooks/`: điều phối các play, nhóm máy và thứ tự chạy; mỗi playbook vẫn có thể chạy riêng.
- `roles/preflight/`: kiểm tra control node và router, thực thi điều kiện an toàn trước khi cấu hình.
- `roles/router_backup/`, `roles/router_config/`, `roles/router_collect/`: sao lưu, cấu hình và thu thập thông số.
- `roles/lab_report/`: tạo báo cáo và chứa template Markdown/CSV.
- `filter_plugins/`: phân tích ping và kiểm tra xung đột cấu hình.
- `tests/`: kiểm thử bộ phân tích và phát hiện xung đột.

```bash
python -m unittest discover -s tests -v
```

Playbook không tự sửa cáp trong EVE. Nếu mạng quản lý mất kết nối, kiểm tra bridge `pnet0` và kết nối tới Ubuntu trước khi chạy lại.

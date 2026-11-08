<div align="center">

# NT542.R11 - Bài tập Ansible
## Cấu hình, Thu thập Cấu hình và Đo lường Mô hình Router trên EVE-NG

</div>

Bài lab này triển khai giải pháp để tự động hóa thu thập cấu hình và đo tài nguyên, độ trễ và mất gói bằng **Ansible Core** để quản trị mô hình gồm hai Router **MikroTik RouterOS (CHR)** chạy trên nền tảng giả lập **EVE-NG**. 

Hệ thống đáp ứng đầy đủ các yêu cầu kỹ thuật:
- **Tự động cấu hình (Configuration):** Nạp địa chỉ IP liên kết, địa chỉ Loopback, định tuyến tĩnh và Hostname với nguyên lý **Bất biến (Idempotent)**
- **Thu thập cấu hình (Collection):** Xuất cấu hình running-config dạng văn bản an toàn (`/export`), trích xuất Facts tài nguyên phần cứng (CPU, RAM, Uptime, Disk).
- **Kiểm thử & Đo lường (Verification & Observability):** Thực hiện đo lường độ trễ mạng (Ping 5 gói) cả trên đường truyền quản lý (Out-of-band) và đường truyền dữ liệu liên router (In-band Loopback to Loopback).
- **Tự động báo cáo (Reporting):** Tự động sinh báo cáo tổng hợp trực quan dạng Markdown (`report.md`) và dữ liệu máy đọc dạng CSV (`summary.csv`).

---

## 1. Kiến trúc tổng quan

Mô hình lab được phân tách độc lập giữa **Hệ thống điều khiển (Management / Control Plane)** và **Hạ tầng mạng giả lập (Data / Network Infrastructure Plane)**:

```text
                          +-----------------------------------+
                          |      Ubuntu 20.04 Control Node    |
                          |           192.168.126.131         |
                          |  Python 3.12 | Ansible Core 2.20  |
                          +-----------------+-----------------+
                                            |
                                            | SSH (Port 22 - Out-of-band)
                                            |
                          +-----------------v-----------------+
                          |     EVE Management Cloud0 (pnet0) |
                          |         192.168.126.0/24          |
                          +--------+-----------------+--------+
                                   |                 |
        ether1: 192.168.126.11/24  |                 |  ether1: 192.168.126.12/24
                                   |                 |
             +---------------------v---+         +---v---------------------+
             |        Router R1        |         |        Router R2        |
             |  (MikroTik CHR 7.16.1)  |         |  (MikroTik CHR 7.16.1)  |
             |                         |  ether2 |                         |
             | ether2: 10.12.0.1/30    |<------->| ether2: 10.12.0.2/30    |
             | lo:     10.255.0.1/32   |  Data   | lo:     10.255.0.2/32   |
             |                         |  Link   |                         |
             | Route: 10.255.0.2/32    | 10.12.0 | Route: 10.255.0.1/32    |
             |        via 10.12.0.2    |  .0/30  |        via 10.12.0.1    |
             +-------------------------+         +-------------------------+
```

### Chi tiết các thành phần:

| Thành phần | Vai trò kỹ thuật | Địa chỉ IP / Thông số |
| :--- | :--- | :--- |
| **Ubuntu 20.04 LTS** | **Ansible Control Node** thực thi playbook, chạy Python 3.12 trong môi trường ảo `.venv-ansible`, điều khiển thiết bị qua SSH. | `192.168.126.131` |
| **EVE-NG Community** | Môi trường giả lập mạng (Network Hypervisor), lưu trữ và chạy các máy ảo router. | `192.168.126.133` |
| **Management(Cloud0)** | Cầu nối mạng ảo (Bridge ra VMware VMnet8), cung cấp đường truyền Out-of-band cho Ansible SSH vào router. | Dải mạng `192.168.126.0/24` |
| **Router R1** | Router biên 1 (MikroTik RouterOS 7.16.1), quản lý qua cổng `ether1`, nối sang R2 qua `ether2`. | Mgmt: `192.168.126.11/24`<br/>Link: `10.12.0.1/30`<br/>Loopback: `10.255.0.1/32` |
| **Router R2** | Router biên 2 (MikroTik RouterOS 7.16.1), quản lý qua cổng `ether1`, nối sang R1 qua `ether2`. | Mgmt: `192.168.126.12/24`<br/>Link: `10.12.0.2/30`<br/>Loopback: `10.255.0.2/32` |
| **Đường liên kết R1–R2** | Tuyến truyền dữ liệu trực tiếp nối giữa 2 cổng `ether2`. | Mạng `10.12.0.0/30` |

---

## 2. Cấu trúc Thư mục Dự án Ansible

Toàn bộ dự án được tổ chức theo chuẩn module hóa (Role-based) của Ansible:

```text
NT542-Lab02-Ansible/
├── ansible.cfg                   # Cấu hình Ansible Core (timeout, inventory path, plugin)
├── inventory.ini                 # Khai báo danh sách các router (R1, R2)
├── requirements.txt              # Thư viện Python đã ghim phiên bản (ansible-core, pylibssh)
├── requirements.yml              # Ansible Collections chính thức (community.routeros, netcommon)
├── site.yml                      # Playbook điều phối toàn diện 6 giai đoạn (All-in-one)
│
├── group_vars/
│   └── routeros.yml              # Cấu hình SSH chung (driver libssh, terminal admin+cet1024w)
├── host_vars/
│   ├── R1.yml                    # Thông số mạng mong muốn cho Router R1 (IP, Loopback, Route)
│   └── R2.yml                    # Thông số mạng mong muốn cho Router R2 (IP, Loopback, Route)
│
├── playbooks/
│   ├── init.yml                  # Khởi tạo định danh lượt chạy duy nhất (UTC lab_run_id)
│   ├── preflight.yml             # Kiểm tra điều kiện môi trường & phát hiện xung đột cấu hình
│   ├── backup.yml                # Xuất cấu hình văn bản (/export) trước và sau thay đổi
│   ├── configure.yml             # Nạp IP, Loopback, Route, Hostname (đảm bảo Idempotent)
│   ├── collect.yml               # Thu thập Facts phần cứng và đo lường Ping 2 chiều
│   └── report.yml                # Tổng hợp số liệu và render báo cáo tự động
│
├── roles/
│   ├── preflight/                # Role kiểm tra controller và routers trước khi cấu hình
│   ├── router_backup/            # Role sao lưu cấu hình an toàn (.rsc)
│   ├── router_config/            # Role nạp cấu hình và xác minh sự hội tụ
│   ├── router_collect/           # Role lấy facts, raw CLI và thực hiện phép đo ping
│   └── lab_report/               # Role sinh báo cáo tự động từ template Jinja2
│       └── templates/
│           ├── report.md.j2      # Mẫu báo cáo định dạng Markdown
│           └── summary.csv.j2    # Mẫu bảng dữ liệu tóm tắt CSV
│
├── filter_plugins/
│   └── lab_metrics.py            # Bộ lọc tùy biến: tính % RAM, bóc tách ping, chống xung đột
├── tests/
│   └── test_lab_metrics.py       # Bộ Unit Test (7 test cases) kiểm thử logic filter_plugins
├── artifacts/                    # Thư mục chứa kết quả đo và file export theo từng <run_id>
├── README.md                     # Tài liệu tổng quan kiến trúc bài lab
└── INSTALL.md                    # Cẩm nang hướng dẫn chi tiết từng câu lệnh từ A-Z
```

### Các thành phần chính cần chú ý:
- **`inventory.ini` & `group_vars/routeros.yml`:** Khai báo thiết bị sạch, tuyệt đối không lưu mật khẩu. Sử dụng hậu tố `admin+cet1024w` để ép RouterOS xuất dữ liệu dạng dumb terminal (không mã màu ANSI, không ngắt trang, chiều rộng 1024 ký tự để giữ nguyên vẹn cấu trúc JSON). Danh sách `lab_tested_routeros_versions` chỉ chứa các phiên bản đã kiểm thử; hiện tại là `7.16.1`.
- **`filter_plugins/lab_metrics.py`:** Bộ xử lý số liệu đo lường. Xử lý chính xác các đơn vị nano/micro/mili-giây, không làm tròn gượng ép `<1ms` về số 0, phát hiện xung đột mạng trước khi nạp.
- **`roles/router_config/`:** Kiểm tra đối chiếu trước khi thực thi. Nếu cấu hình đã tồn tại chính xác, tác vụ sẽ tự bỏ qua, đảm bảo kết quả **`changed=0`** ở các lần chạy sau.

---

## 3. Tổng quan các Bước Thiết lập Cơ bản

> [!TIP]
> **Hướng dẫn chi tiết:** Vui lòng xem tài liệu chuyên sâu tại [**`INSTALL.md`**](INSTALL.md). Dưới đây là tóm tắt quy trình 4 giai đoạn chính để hoàn thành bài lab:

### Giai đoạn 1: Cài đặt EVE-NG Community trên VMware
- Tạo máy ảo Ubuntu 64-bit trên VMware Workstation Pro (chế độ mạng **NAT - VMnet8**).
- **Bắt buộc bật:** Virtualize Intel VT-x/EPT để cấp ảo hóa lồng nhau cho Router. *(Nếu gặp lỗi xung đột Hyper-V/VBS `Monitor Mode: ULM`, thực hiện theo hướng dẫn tắt VBS ở Phần 2 trong `INSTALL.md`)*.
- Khởi động máy ảo EVE-NG từ file ISO và hoàn tất Wizard cấu hình mạng ban đầu.

### Giai đoạn 2: Nạp Image MikroTik RouterOS (CHR 7.16.1)
- Tải file ảnh đĩa `chr-7.16.1.img.zip` từ trang chủ MikroTik trực tiếp vào EVE-NG.
- Giải nén và chuyển đổi định dạng đĩa sang QEMU QCOW2: `/opt/unetlab/addons/qemu/mikrotik-7.16.1/hda.qcow2`.
- Chạy lệnh phân quyền hệ thống: `/opt/unetlab/wrappers/unl_wrapper -a fixpermissions`.

### Giai đoạn 3: Dựng Topology và Cấu hình Sơ bộ Router
- Trên giao diện Web EVE-NG (`HTML5 console`), tạo bài lab và thêm:
  - 02 Router MikroTik (`R1`, `R2` cấp 256MB RAM).
  - 01 Network loại `Management(Cloud0)`.
- **Nối dây:**
  - Cổng `ether1` của R1 và R2 cắm vào đám mây `Net (Cloud0)`.
  - Cổng `ether2` của R1 cắm trực tiếp sang `ether2` của R2.
- **Bật Router & Gán IP quản lý ban đầu:**
  - Đặt mật khẩu quản trị `admin`.
  - Gán IP tĩnh cổng `ether1`: R1 là `192.168.126.11/24`, R2 là `192.168.126.12/24`.
  - Xóa dịch vụ DHCP client mặc định (`/ip dhcp-client remove [find]`).
  - Kiểm tra kết nối từ máy thật hoặc Ubuntu qua lệnh `ping` và `ssh`.

### Giai đoạn 4: Chạy Toàn bộ Playbook Ansible (All-in-One)
Trên máy ảo **Ubuntu Control Node** (`192.168.126.131`), sau khi kích hoạt môi trường ảo:

```bash
cd ~/Downloads/NT542-Lab02-Ansible
source .venv-ansible/bin/activate

# Chạy kiểm thử tự động bộ lọc trước khi chạy lab
python -m unittest discover -s tests -v

# Chạy toàn bộ kịch bản cấu hình, thu thập và báo cáo
ansible-playbook site.yml -k
```

Khi được hỏi `SSH password: `, nhập mật khẩu của tài khoản `admin` Router.

Ansible sẽ tự động thực thi tuần tự 6 bước:
1. **Preflight:** Kiểm tra phiên bản, SSH và phát hiện xung đột cấu hình.
2. **Backup Before:** Xuất bản cấu hình ban đầu trước khi can thiệp.
3. **Configure:** Tự động nạp IP đường truyền `10.12.0.0/30`, Loopback `10.255.0.0/32`, Static Route và đổi tên router.
4. **Backup After:** Xuất bản cấu hình sau khi đã áp dụng thay đổi.
5. **Collect:** Thu thập số liệu phần cứng, Uptime và đo lường 2 tuyến ping (5 gói/tuyến).
6. **Report:** Tự động tổng hợp kết quả thành file báo cáo Markdown và bảng tổng hợp CSV.

---

## 4. Kết quả Đạt được

Sau khi playbook kết thúc, toàn bộ kết quả minh chứng phục vụ viết báo cáo học phần nằm trong thư mục **`artifacts/<run_id>/`**:
- **`<router>-before.rsc` & `<router>-after.rsc`:** Dữ liệu cấu hình văn bản trước và sau khi tự động hóa.
- **`<router>-metrics.json`:** Toàn bộ thông số đo lường có cấu trúc (CPU, RAM, Uptime, kết quả ping chi tiết RTT min/avg/max).
- **`report.md`:** Bản báo cáo tổng hợp Markdown chứa sẵn biểu bảng, phân tích mô hình và độ trễ mạng — sẵn sàng đưa vào báo cáo nghiệm thu đồ án.
- **`summary.csv`:** Tệp dữ liệu số liệu phục vụ phân tích hoặc vẽ biểu đồ.

*(Để kiểm tra tính Idempotent, bạn chỉ cần gõ lại lệnh `ansible-playbook playbooks/configure.yml -k`, hệ thống sẽ trả về `changed=0` chứng minh không có cấu hình thừa nào bị ghi đè)*.

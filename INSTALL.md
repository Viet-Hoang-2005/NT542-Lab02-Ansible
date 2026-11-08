# Hướng dẫn Cài đặt EVE-NG Community & Thiết lập Lab Tự Động Hóa Mạng với Ansible

Tài liệu này hướng dẫn chi tiết toàn bộ quy trình từ cài đặt nền tảng [EVE-NG Community 6.2.0-4](https://www.eve-ng.net/index.php/download) trên [VMware Workstation Pro](https://www.vmware.com/products/desktop-hypervisor/workstation-and-fusion), nạp image Router MikroTik, thiết lập sơ đồ mạng (Topology), chuẩn bị máy chủ điều khiển (Ansible Control Node) cho đến các bước thực thi Playbook tự động hóa cấu hình và thu thập dữ liệu mạng.

---

## Phần 1: Tạo máy ảo mới trong VMware Workstation Pro

1. Mở **VMware Workstation Pro**.
2. Chọn menu **File** $\rightarrow$ **New Virtual Machine...** (hoặc phím tắt `Ctrl + N`).
3. Tại cửa sổ Wizard:
   - Chọn **Custom (advanced)** $\rightarrow$ Bấm **Next**.
   - **Hardware compatibility:** Để mặc định (Workstation mới nhất) $\rightarrow$ **Next**.
4. **Guest OS Installation:**
   - ⚠️ **LƯU Ý QUAN TRỌNG:** Chọn mục **"I will install the operating system later"** (Không chọn nạp file ISO ở bước này để tránh VMware kích hoạt chế độ Easy Install tự động làm lỗi kịch bản cài đặt của EVE-NG).
   - Bấm **Next**.
5. **Select a Guest Operating System:**
   - **Guest operating system:** Chọn **Linux**.
   - **Version:** Chọn **Ubuntu 64-bit**.
   - Bấm **Next**.
6. **Name the Virtual Machine:**
   - **Virtual machine name:** Đặt tên, ví dụ `EVE-NG-Community`.
   - **Location:** Chọn thư mục lưu máy ảo trên ổ cứng còn trống tối thiểu 40 - 50 GB (ưu tiên ổ SSD).
   - Bấm **Next**.
7. **Processor Configuration:**
   - **Number of processors:** `1`
   - **Number of cores per processor:** Tối thiểu `4` (khuyến nghị 4 - 8 cores tùy CPU máy thật).
   - Bấm **Next**.
8. **Memory for the Virtual Machine:**
   - Cấp tối thiểu **4096 MB (4 GB)**.
   - Khuyến nghị: **6144 MB (6 GB)** hoặc **8192 MB (8 GB)** nếu máy tính có từ 16 GB RAM trở lên.
   - Bấm **Next**.
9. **Network Type:**
   - Chọn **Use network address translation (NAT)**.
   - Bấm **Next**.
10. **I/O Controller & Disk Type:**
    - I/O Controller: Để mặc định (**LSI Logic**).
    - Disk Type: Để mặc định (**SCSI**).
    - Bấm **Next**.
11. **Select a Disk & Disk Capacity:**
    - Chọn **Create a new virtual disk** $\rightarrow$ **Next**.
    - **Maximum disk size (GB):** Đặt từ **40.0 GB đến 60.0 GB** (để đủ dung lượng chứa hệ điều hành, các image Router và file cấu hình sau này).
    - Tích chọn **Store virtual disk as a single file** (giúp tăng tốc độ đọc ghi đĩa ảo).
    - Bấm **Next** $\rightarrow$ **Next**.
12. **Gắn file ISO và bật ảo hóa CPU (CỰC KỲ QUAN TRỌNG):**
    - Tại màn hình tóm tắt cuối cùng, nhấn vào nút **Customize Hardware...**:
      - Chọn mục **Processors**:
        - Tích chọn **Virtualize Intel VT-x/EPT or AMD-V/RVI** để cấp ảo hóa lồng nhau cho EVE-NG, phục vụ các router QEMU dùng KVM.
        - Để **Virtualize CPU performance counters** ở trạng thái bỏ tích.
      - Chọn mục **New CD/DVD (SATA)**:
        - Tích chọn **Connect at power on**.
        - Chọn **Use ISO image file:** $\rightarrow$ Bấm **Browse...** $\rightarrow$ Trỏ tới file `eve-ce-prod-6.2.0-4-full.iso`.
    - Nhấn **Close** $\rightarrow$ Nhấn **Finish**.

---

## Phần 2: Cấu hình Windows để chạy lab với ảo hóa lồng nhau (Khắc phục lỗi ULM / Hyper-V)

### 1. Hiện tượng và Nguyên nhân
Khi bật tính năng **Virtualize Intel VT-x/EPT or AMD-V/RVI** trong VMware trên Windows bật Hyper-V/VBS, máy ảo có thể không khởi động được và báo lỗi:
```text
Hyper-V detected by CPUID
Monitor Mode: ULM
ULM: Failed to set up partition, res 0xc0350005.
Module 'ULM' power on failed.
```
Đây là hạn chế được Broadcom ghi nhận khi dùng ảo hóa lồng nhau cùng Hyper-V/VBS trên máy thật ([Tài liệu Broadcom KB 313547](https://knowledge.broadcom.com/external/article/313547)).

> [!CAUTION]
> Việc tắt VBS làm giảm các lớp bảo vệ dựa trên ảo hóa của Windows. Tắt Virtual Machine Platform cũng khiến WSL2 và Docker Desktop tạm thời không hoạt động trong suốt thời gian làm lab.

### 2. Các bước cấu hình chi tiết (Chạy bằng PowerShell với quyền Administrator)

#### Bước 1: Tắt tự động khởi chạy hypervisor của Windows
```powershell
bcdedit /set hypervisorlaunchtype off
```

#### Bước 2: Tắt Memory integrity (Tính năng bảo vệ dùng VBS)
- Mở **Windows Security** $\rightarrow$ **Device security** $\rightarrow$ **Core isolation details** và gạt tắt **Memory integrity**.
- *Ý nghĩa:* Tắt tính năng bảo vệ dùng VBS ([Tài liệu Microsoft](https://learn.microsoft.com/en-us/windows/security/hardware-security/enable-virtualization-based-protection-of-code-integrity)).

#### Bước 3: Bỏ tích Virtual Machine Platform trong Windows Features
- Mở cửa sổ **Windows Features** (gõ `optionalfeatures` hoặc tìm *Turn Windows features on or off*).
- Bỏ tích chọn **Virtual Machine Platform** $\rightarrow$ Nhấn OK.

#### Bước 4: Tắt Virtual Secure Mode (VSM) cho Windows hiện tại
```powershell
bcdedit /set "{current}" vsmlaunchtype off
```

#### Bước 5: Đặt cấu hình VBS tổng về 0
```powershell
# 1. Sao lưu nhánh Registry DeviceGuard trước khi chỉnh sửa
reg export "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard" "$env:USERPROFILE\DeviceGuard-before-EVE.reg" /y

# 2. Đặt cấu hình VBS tổng về 0
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard" /v EnableVirtualizationBasedSecurity /t REG_DWORD /d 0 /f
```

#### Bước 6: Tắt tính năng Virtual Machine Platform bằng lệnh DISM
```powershell
DISM /Online /Disable-Feature /FeatureName:VirtualMachinePlatform /NoRestart
```

#### Bước 7: Tắt cấu hình VBS của Windows Hello (Enhanced Sign-in Security)
- Vào **Settings** $\rightarrow$ **Accounts** $\rightarrow$ **Sign-in options**.
- Tắt mục: **“For improved security, only allow Windows Hello sign-in for Microsoft accounts on this device”**.

```powershell
# 1. Sao lưu cấu hình nhánh Windows Hello
reg export "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\WindowsHello" "$env:USERPROFILE\WindowsHello-before-EVE.reg" /y

# 2. Tắt nhánh cấu hình VBS của Windows Hello
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\WindowsHello" /v Enabled /t REG_DWORD /d 0 /f
```

### 3. Khởi động lại máy & Kiểm tra trạng thái thực tế
Sau khi hoàn tất các bước trên, tiến hành **Restart máy tính**. Mở PowerShell để kiểm tra:

```powershell
# 1. Kiểm tra Hypervisor (kết quả mong muốn: False)
Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent

# 2. Kiểm tra trạng thái VBS (kết quả mong muốn: 0)
Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard | Select-Object VirtualizationBasedSecurityStatus
```

- **Kết quả đạt được:** VM EVE-NG khởi động với tính năng ảo hóa lồng nhau bật thành công (log hiển thị `Monitor Mode: CPL0`), KVM hoạt động trơn tru và chạy được đầy đủ các router cần cho bài lab.

---

## Phần 3: Tiến hành cài đặt EVE-NG từ đĩa ISO

1. Chọn máy ảo `EVE-NG-Community` vừa tạo và nhấn **Power on this virtual machine**.
2. **Menu khởi động cài đặt:**
   - Màn hình boot của EVE-NG xuất hiện, chọn **Install EVE-NG** (hoặc nhấn **Enter**).
3. **Cài hệ điều hành nền:** Chọn `English`, bàn phím `English (US)` và tiếp tục theo trình cài. Nếu được hỏi ổ đĩa đích, chọn đúng đĩa ảo 60 GB vừa tạo.
4. Xác nhận phân vùng đĩa (**Confirm destructive action**): Dùng phím mũi tên chuyển sang **`[ Continue ]`** và nhấn **Enter**.
5. **Chờ cài EVE-NG:** Máy tự động cài đặt các gói và khởi động lại vào hệ điều hành EVE-NG.

---

## Phần 4: Chạy Setup Wizard lần đầu & Truy cập Web UI

1. Sau khi máy ảo khởi động lại, đăng nhập dòng lệnh:
   - **Username:** `root`
   - **Password:** `eve` *(mật khẩu mặc định ban đầu)*
2. Màn hình Wizard màu xanh sẽ xuất hiện để hoàn thiện cấu hình mạng:
   - **Root password / Confirm:** Gõ lại mật khẩu `eve` $\rightarrow$ Enter.
   - **Hostname:** Giữ nguyên `eve-ng` $\rightarrow$ Enter.
   - **Domain:** Giữ nguyên `example.com` $\rightarrow$ Enter.
   - **IP Allocation:** Chọn **DHCP** $\rightarrow$ Enter.
   - **NTP Server:** Để trống $\rightarrow$ Enter.
   - **Connection type:** Chọn **Direct connection** $\rightarrow$ Enter.
3. Máy ảo khởi động lại dịch vụ và hiển thị địa chỉ IP Web (ví dụ: `http://192.168.126.133/`).
4. Mở trình duyệt Web trên máy Windows (Chrome/Edge), truy cập vào địa chỉ IP trên:
   - **Username:** `admin`
   - **Password:** `eve`
   - **Console:** Chọn **`HTML5 console`** (để mở console trực tiếp trên tab trình duyệt, tránh lỗi popup ứng dụng Telnet bên ngoài).
   - Bấm **Sign in**.

---

## Phần 5: Nạp Image Router MikroTik RouterOS (CHR) vào EVE-NG

Thực hiện tải và nạp trực tiếp image RouterOS phiên bản 7.16.1 vào EVE-NG thông qua terminal:

1. Mở PowerShell trên Windows và SSH vào EVE-NG (hoặc gõ trực tiếp trên console máy ảo EVE-NG):
   ```bash
   ssh root@192.168.126.133
   # Mật khẩu: eve
   ```

2. Chạy khối lệnh sau để tải, giải nén, chuyển đổi định dạng đĩa sang QCOW2 và cấp quyền:
   ```bash
   # 1. Tạo thư mục chứa image MikroTik chuẩn theo quy tắc EVE-NG
   mkdir -p /opt/unetlab/addons/qemu/mikrotik-7.16.1

   # 2. Di chuyển vào thư mục vừa tạo
   cd /opt/unetlab/addons/qemu/mikrotik-7.16.1

   # 3. Tải file Raw Disk Image từ trang chủ MikroTik
   wget https://download.mikrotik.com/routeros/7.16.1/chr-7.16.1.img.zip

   # 4. Giải nén file
   unzip chr-7.16.1.img.zip

   # 5. Chuyển đổi sang định dạng đĩa hda.qcow2 cho QEMU
   /opt/qemu/bin/qemu-img convert -f raw -O qcow2 chr-7.16.1.img hda.qcow2

   # 6. Dọn dẹp file nén và file raw tạm
   rm -f chr-7.16.1.img*

   # 7. Phân quyền chuẩn cho EVE-NG
   /opt/unetlab/wrappers/unl_wrapper -a fixpermissions
   ```

---

## Phần 6: Thiết lập Topology và Cấu hình Ban đầu cho Router

### 1. Tạo Lab và Thêm Thiết bị trên Web UI EVE-NG
1. Tại màn hình **File manager**, bấm biểu tượng **Add new lab** (tờ giấy thứ 2 từ trái sang).
   - Đặt tên Lab: `NT542_Ansible_Mikrotik` $\rightarrow$ Bấm **Save**.
2. **Thêm 2 Router MikroTik:**
   - Click chuột phải vào màn hình canvas $\rightarrow$ Chọn **+ Node**.
   - Chọn **MikroTik RouterOS** (chữ hiển thị màu xanh).
   - Thiết lập thông số:
     - `Number of nodes to add`: `2`
     - `Name/prefix`: `R` (sẽ tự động sinh ra `R1` và `R2`)
     - `RAM (MB)`: `256`
     - `Ethernets`: `4`
     - Các thông số khác: Để mặc định $\rightarrow$ Bấm **Save**.
3. **Thêm Mạng Quản lý (Management Cloud):**
   - Click chuột phải $\rightarrow$ Chọn **+ Network**.
   - `Type`: Chọn **`Management(Cloud0)`** (Cầu nối trực tiếp ra card `VMnet8 192.168.126.0/24`).
   - `Name`: `Net` $\rightarrow$ Bấm **Save**.

### 2. Nối dây mạng (Cabling)
- **Mạng Quản lý (Management):**
  - Kéo từ đầu cắm của **R1** sang đám mây **Net**: Chọn cổng `ether1` $\rightarrow$ Save.
  - Kéo từ đầu cắm của **R2** sang đám mây **Net**: Chọn cổng `ether1` $\rightarrow$ Save.
- **Mạng Dữ liệu liên kết giữa 2 Router (Inter-router Data Link):**
  - Kéo từ đầu cắm của **R1** sang **R2**: Chọn cổng `ether2` trên R1 nối với `ether2` trên R2 $\rightarrow$ Save.

### 3. Bật nguồn và Cấu hình Ban đầu cho Router
Khởi động cả 2 router bằng cách click chuột phải vào từng router $\rightarrow$ Chọn **Start** (hoặc dùng nút *Start all nodes* ở thanh công cụ bên trái).

#### Cấu hình trên Router 1 (R1):
1. Click vào **R1** để mở terminal Console HTML5.
2. Đăng nhập: `admin` / Password: nhấn Enter (bỏ trống).
3. Khi hỏi xem license (`[Y/n]`): Nhấn `n`.
4. Nhập mật khẩu mới cho admin (ví dụ: `admin123`, nhập 2 lần).
5. Chạy các lệnh cấu hình IP và dọn dẹp DHCP client:
   ```routeros
   # 1. Gán IP tĩnh mạng quản lý cho cổng ether1
   /ip address add address=192.168.126.11/24 interface=ether1

   # 2. Tắt/Xóa DHCP Client mặc định (nếu có) để tránh nhận IP động trùng lặp
   /ip dhcp-client remove [find]

   # 3. Đặt định danh tên cho Router
   /system identity set name=R1
   ```

#### Cấu hình trên Router 2 (R2):
1. Click vào **R2** để mở Console HTML5.
2. Đăng nhập và đặt mật khẩu tương tự như R1.
3. Chạy các lệnh cấu hình:
   ```routeros
   # 1. Gán IP tĩnh mạng quản lý cho cổng ether1
   /ip address add address=192.168.126.12/24 interface=ether1

   # 2. Tắt/Xóa DHCP Client mặc định
   /ip dhcp-client remove [find]

   # 3. Đặt định danh tên cho Router
   /system identity set name=R2
   ```

### 4. Kiểm tra Kết nối Mạng từ Host Windows
Mở **PowerShell** trên Windows và kiểm tra kết nối tới cả 2 router:
```powershell
# 1. Kiểm tra Ping
ping 192.168.126.11
ping 192.168.126.12

# 2. Thử đăng nhập SSH từ PowerShell
ssh admin@192.168.126.11
ssh admin@192.168.126.12
```
Nếu cả hai lệnh đều phản hồi thành công và đăng nhập được SSH thì mô hình mạng đã sẵn sàng 100%!

---

## Phần 7: Chuẩn bị Môi trường Ansible Control Node (Máy ảo Ubuntu 20.04)

Sử dụng máy ảo độc lập **Ubuntu 20.04** trên VMware Workstation (cùng chế độ mạng NAT VMnet8) làm máy chủ điều khiển tự động hóa (Ansible Control Node):

1. Khởi động máy ảo **Ubuntu 20.04**.
2. Mở terminal trên Ubuntu, kiểm tra kết nối mạng sang 2 Router:
   ```bash
   ping -c 3 192.168.126.11
   ping -c 3 192.168.126.12
   ```
3. Cài pyenv và các thư viện cần để biên dịch Python 3.12:
   ```bash
   sudo apt update
   sudo apt install -y build-essential git curl ca-certificates libssl-dev zlib1g-dev \
     libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev xz-utils tk-dev \
     libffi-dev liblzma-dev
   ```

   ```bash
   # Chỉ clone nếu ~/.pyenv chưa tồn tại
   git clone https://github.com/pyenv/pyenv.git "$HOME/.pyenv"

   export PYENV_ROOT="$HOME/.pyenv"
   export PATH="$PYENV_ROOT/bin:$PATH"
   eval "$(pyenv init - bash)"
   ```
4. Trong thư mục dự án, tạo venv riêng và cài các phiên bản đã ghim:
   ```bash
   MAKE_OPTS='-j2' pyenv install -s 3.12.16
   cd ~/Downloads/NT542-Lab02-Ansible
   pyenv local 3.12.16
   python -m venv .venv-ansible
   source .venv-ansible/bin/activate
   python -m pip install -r requirements.txt
   ansible-galaxy collection install -r requirements.yml
   ansible --version
   ```
   *(Python hệ thống vẫn giữ nguyên. Ansible Core 2.20.11 chạy trong venv Python 3.12; dùng `deactivate` khi muốn thoát venv)*.

---

## Phần 8: Hướng dẫn Thực thi Playbook Ansible

Toàn bộ thao tác thực thi dưới đây được thực hiện trong Terminal của máy **Ubuntu Control Node**

### Bước 1: Kích hoạt môi trường ảo & Chấp nhận SSH Host Key
```bash
# 1. Di chuyển vào thư mục dự án và kích hoạt venv
cd ~/Downloads/NT542-Lab02-Ansible
source .venv-ansible/bin/activate

# 2. Cập nhật mã nguồn mới nhất từ Git
git pull --ff-only

# 3. Chấp nhận fingerprint SSH của 2 router vào known_hosts (chỉ cần làm 1 lần đầu)
ssh -o StrictHostKeyChecking=accept-new admin@192.168.126.11 "exit"
ssh -o StrictHostKeyChecking=accept-new admin@192.168.126.12 "exit"
```

### Bước 2: Kiểm tra cú pháp và Unit Tests
Trước khi chạy lên thiết bị thật, luôn kiểm tra cú pháp và logic bộ lọc:
```bash
# 1. Hiển thị cấu trúc cây Inventory
ansible-inventory --graph

# 2. Kiểm tra cú pháp playbook
ansible-playbook --syntax-check site.yml

# 3. Chạy kiểm thử tự động cho bộ lọc số liệu và phát hiện xung đột
python -m unittest discover -s tests -v
```

### Bước 3: Chạy Toàn bộ Kịch bản
Lệnh All-in-One chạy toàn bộ chuỗi tác vụ theo thứ tự chuẩn:
```bash
ansible-playbook site.yml -k
```
- Khi terminal hiển thị `SSH password: `, nhập mật khẩu của tài khoản `admin` Router (ví dụ: `admin123`).
- **Chuỗi tiến trình tự động diễn ra:**
  1. **Preflight:** Kiểm tra phiên bản Ansible, collection, trạng thái kết nối và phát hiện xung đột IP/Route.
  2. **Backup Before:** Xuất bản cấu hình gốc trước khi thay đổi (`<router>-before.rsc`).
  3. **Configure:** Tự động nạp IP `ether2`, IP Loopback `lo`, Static Route và đổi Hostname `R1`, `R2`.
  4. **Backup After:** Xuất bản cấu hình sau khi đã áp dụng thay đổi (`<router>-after.rsc`).
  5. **Collect:** Thu thập số liệu phần cứng, tài nguyên và thực hiện đo lường ping 2 chiều.
  6. **Report:** Tự động tổng hợp và sinh ra báo cáo `report.md` cùng `summary.csv`.

### Bước 4: Chạy Từng bước Độc lập
Nếu muốn chạy từng playbook riêng biệt nhưng vẫn lưu chung vào một thư mục kết quả:
```bash
# Tạo Run ID theo giờ Việt Nam (ví dụ: 2026-11-08_10-45-00)
LAB_RUN_ID="$(TZ='Asia/Ho_Chi_Minh' date +%Y-%m-%d_%H-%M-%S)"

# 1. Chạy Preflight kiểm tra điều kiện
ansible-playbook playbooks/preflight.yml -k -e "lab_run_id=$LAB_RUN_ID"

# 2. Sao lưu cấu hình trước thay đổi
ansible-playbook playbooks/backup.yml -k -e "lab_run_id=$LAB_RUN_ID" -e backup_phase=before

# 3. Thực thi cấu hình mạng
ansible-playbook playbooks/configure.yml -k -e "lab_run_id=$LAB_RUN_ID"

# 4. Sao lưu cấu hình sau thay đổi
ansible-playbook playbooks/backup.yml -k -e "lab_run_id=$LAB_RUN_ID" -e backup_phase=after

# 5. Thu thập thông số đo lường
ansible-playbook playbooks/collect.yml -k -e "lab_run_id=$LAB_RUN_ID"

# 6. Tạo báo cáo tổng hợp
ansible-playbook playbooks/report.yml -e "lab_run_id=$LAB_RUN_ID"
```

### Bước 5: Kiểm tra tính Bất biến (Idempotency)
Để chứng minh với giảng viên rằng Ansible không ghi đè cấu hình trùng lặp:
```bash
# Chạy lại playbook cấu hình lần thứ 2
ansible-playbook playbooks/configure.yml -k
```
**Kết quả quan sát:** Toàn bộ tác vụ đều báo trạng thái `ok` (màu xanh lá), tóm tắt kết thúc báo **`changed=0`**.

### Bước 6: Đọc Kết quả trong Thư mục `artifacts/<run_id>/`
Sau khi chạy xong, toàn bộ minh chứng nằm tại thư mục `artifacts/<run_id>/`:
- `<router>-before.rsc` & `<router>-after.rsc`: Dùng lệnh `diff` để so sánh trực quan cấu hình thay đổi:
  ```bash
  diff -u artifacts/<run_id>/R1-before.rsc artifacts/<run_id>/R1-after.rsc
  ```
- `report.md`: Báo cáo chi tiết định dạng Markdown chứa bảng biểu mô hình, phần cứng và độ trễ ping.
- `summary.csv`: Tệp dữ liệu số liệu phục vụ vẽ biểu đồ hoặc phân tích bảng tính.

---

## Phần 9: Khôi phục Windows sau khi hoàn thành lab

> [!WARNING]
> Chỉ thực hiện phần này khi bạn đã hoàn thành và nộp xong toàn bộ bài lab NT542, muốn khôi phục lại các tính năng bảo mật Windows (VBS, Memory Integrity) cũng như sử dụng lại **WSL2** và **Docker Desktop**. 

Mở **PowerShell (Run as Administrator)** và thực hiện:

#### Bước 1: Bật lại Hypervisor và Virtual Secure Mode trong BCD
```powershell
bcdedit /set hypervisorlaunchtype auto
bcdedit /set "{current}" vsmlaunchtype auto
```

#### Bước 2: Kích hoạt lại tính năng Virtual Machine Platform
```powershell
DISM /Online /Enable-Feature /FeatureName:VirtualMachinePlatform /All /NoRestart
```

#### Bước 3: Khôi phục lại cấu hình Registry từ các file sao lưu
Nhập lại 2 file `.reg` đã sao lưu:
```powershell
reg import "$env:USERPROFILE\DeviceGuard-before-EVE.reg"
reg import "$env:USERPROFILE\WindowsHello-before-EVE.reg"
```

#### Bước 4: Bật lại Memory integrity trong Windows Security
1. Mở **Windows Security** $\rightarrow$ **Device security** $\rightarrow$ **Core isolation details**.
2. Gạt bật **Memory integrity** về trạng thái **On**.

#### Bước 5: Bật lại tùy chọn đăng nhập Windows Hello
- Vào **Settings** $\rightarrow$ **Accounts** $\rightarrow$ **Sign-in options**.
- Bật lại mục: **“For improved security, only allow Windows Hello sign-in for Microsoft accounts on this device”**.

#### Bước 6: Khởi động lại máy & Kiểm tra
Khởi động lại máy tính (Restart) và kiểm tra lại:
```powershell
Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent
# Kết quả mong muốn: True
```

---

## Tài liệu tham khảo & Đối chiếu:
- [Broadcom KB 313547: Giới hạn ảo hóa lồng nhau khi Hyper-V hoạt động trên máy thật](https://knowledge.broadcom.com/external/article/313547)
- [EVE-NG Howto: Cài đặt MikroTik RouterOS trên EVE-NG](https://www.eve-ng.net/index.php/documentation/howtos/howto-add-mikrotik-routeros/)
- [Ansible Galaxy: community.routeros collection](https://galaxy.ansible.com/ui/repo/published/community/routeros/)
- [Microsoft: BCDedit set options](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/bcdedit--set)
- [Microsoft: Memory Integrity and Virtualization-based Security](https://learn.microsoft.com/en-us/windows/security/hardware-security/enable-virtualization-based-protection-of-code-integrity)

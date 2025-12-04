# 🚔 CẢNH SÁT VIỆT REALM - Discord Moderation Bot

Bot quản lý máy chủ Discord chuyên nghiệp với các tính năng kiểm duyệt tự động, phát hiện spam, chống lừa đảo và hệ thống cảnh báo thông minh.

---

## 📋 Mục Lục
1. [Giới Thiệu](#giới-thiệu)
2. [Tính Năng](#tính-năng)
3. [Các Lệnh](#các-lệnh)
4. [Cấu Hình](#cấu-hình)
5. [Cài Đặt](#cài-đặt)
6. [Cấu Trúc Tệp](#cấu-trúc-tệp)
7. [Hướng Dẫn Chi Tiết](#hướng-dẫn-chi-tiết)
8. [Dữ Liệu & JSON](#dữ-liệu--json)

---

## 🎯 Giới Thiệu

**CẢNH SÁT VIỆT REALM** là một Discord moderation bot mạnh mẽ giúp bạn:
- ✅ Quản lý thành viên server (Ban, Mute, Warn, Kick)
- ✅ Phát hiện và chặn spam, lừa đảo, token logger
- ✅ Tự động điều chỉnh hành động dựa trên cảnh báo
- ✅ Ghi nhật ký tất cả hành động quản lý
- ✅ Quản lý linh hoạt qua lệnh slash Discord

**Công nghệ**: Python + discord.py v2.0+

---

## 🎁 Tính Năng

### 1. **Quản Lý Thành Viên** (Moderation)
- **Ban**: Cấm vĩnh viễn hoặc theo thời gian
- **Mute**: Cắt tiếng qua Discord timeout + gán role muted
- **Warn**: Cảnh báo với hệ thống 3 cấp độ
- **UnBan/UnMute/UnWarn**: Gỡ hành động quản lý

### 2. **Kiểm Duyệt Tự Động** (Auto Moderation)
- **Từ Khóa Bị Chặn**: Tự động cấm/cắt tiếng/cảnh báo khi phát hiện
- **Hệ Thống Cảnh Báo 3 Cấp**:
  - Cảnh báo 1/3 → Chỉ cảnh báo
  - Cảnh báo 2/3 → Tự động mute 10 phút
  - Cảnh báo 3/3 → Tự động ban 1 ngày
- **Tự Động Gỡ Hành Động**: Tự động Unban/Unmute khi hết thời gian

### 3. **Chống Spam** (Anti-Spam Detection)
Phát hiện các loại spam:
- **Spam tin nhắn**: 5+ tin nhắn trong 5 giây
- **Spam emoji**: 10+ emoji trong 1 tin nhắn
- **Spam mention**: 5+ mention trong 1 tin nhắn
- **Nhảy kênh**: Gửi tin nhắn ở 5+ kênh liên tục
- **Tin nhắn trùng lặp**: Gửi cùng nội dung 3 lần liên tiếp
- **Tin nhắn quá dài**: >2000 ký tự
- **Rate limit**: 10+ tin nhắn trong 5 giây

**Hành động**: Xóa tin nhắn + Cảnh báo/Mute (chỉ gửi 1 thông báo duy nhất)

### 4. **Chống Lừa Đảo & Token Logger** (Anti-Scam)
- **Phát Hiện Token Discord**: Bans ngay lập tức
- **Phát Hiện Scam Domain**: Ban 7 ngày
- **Phát Hiện Nội Dung Lừa Đảo**: 
  - "Free nitro", "Discord nitro free"
  - "Claim your gift", "Free steam gift"
  - "Airdrop", "Crypto giveaway"
  - **Hành động**: Mute 1 giờ + Ghi log

### 5. **Chống Link** (Anti-Link)
- **Link Bị Chặn**: Xóa + Cảnh báo (tùy chỉnh trong JSON)
- **Danh Sách Đen Link**: Cấu hình trong `ban-mute-BlockWord.json`

### 6. **Hệ Thống Ghi Nhật Ký** (Logging)
- Ghi tất cả hành động quản lý vào kênh được chỉ định
- **Thông tin ghi log**: Người dùng, người thực hiện, lý do, thời gian, hành động

### 7. **Hệ Thống Bypass**
Cho phép một số đối tượng không bị ảnh hưởng bởi auto-mod:
- **Bypass User**: Người dùng cụ thể
- **Bypass Role**: Vai trò cụ thể (VD: Moderator)
- **Bypass Channel**: Kênh cụ thể (VD: bot-spam)
- Admin luôn bypass tự động

### 8. **Hệ Thống Phân Quyền**
- Chỉ người dùng trong `authorized_users.json` mới dùng lệnh quản lý
- Kiểm tra role: Không thể action người có role >= bạn
- Ephemeral responses (chỉ bạn thấy thông báo)

---

## 📡 Các Lệnh

### 🔨 Lệnh Quản Lý (Moderation Commands)

| Lệnh | Mô Tả | Tham Số | Ví Dụ |
|------|-------|--------|-------|
| `/vrban` | Cấm người dùng | `user`, `duration?`, `reason?` | `/vrban @user 7d Spam` |
| `/vrUnban` | Gỡ cấm | `user_id`, `reason?` | `/vrUnban 123456789 Appeal` |
| `/vrmute` | Tắt tiếng (timeout + role) | `user`, `duration?`, `reason?` | `/vrmute @user 1h Spam` |
| `/vrUnmute` | Gỡ Tắt tiếng | `user`, `reason?` | `/vrUnmute @user Appeal` |
| `/vrwarn` | Cảnh báo người dùng | `user`, `reason?` | `/vrwarn @user Spam` |
| `/vrUnwarn` | Xóa 1 cảnh báo | `user`, `reason?` | `/vrUnwarn @user Appeal` |

### ⚙️ Lệnh Cấu Hình (Configuration Commands)

| Lệnh | Mô Tả | Tham Số |
|------|-------|--------|
| `/vrsetlog` | Đặt kênh ghi nhật ký | `channel` |
| `/vrsetmutedrole` | Đặt role cho người bị cắt tiếng | `role` |
| `/vrbypass` | Thêm bypass cho role/user/channel | `role?`, `user?`, `channel?` |
| `/vrunbypass` | Xóa bypass cho role/user/channel | `role?`, `user?`, `channel?` |

### 📊 Lệnh Thông Tin (Info Commands)

| Lệnh | Mô Tả |
|------|-------|
| `/vrhelp` | Hiển thị danh sách tất cả lệnh |
| `/vrstatus` | Kiểm tra trạng thái bot & cấu hình server |

---

## ⏱️ Định Dạng Thời Lượng

Sử dụng cho các tham số `duration`:

| Ký Hiệu | Ý Nghĩa | Ví Dụ |
|---------|--------|-------|
| `s` | Giây | `30s` = 30 giây |
| `m` | Phút | `10m` = 10 phút |
| `h` | Giờ | `1h` = 1 giờ |
| `d` | Ngày | `7d` = 7 ngày |
| `w` | Tuần | `2w` = 2 tuần |
| `mo` | Tháng | `1mo` = 1 tháng (~30 ngày) |
| (trống) | Vĩnh viễn | Ban vĩnh viễn, Mute tối đa 28 ngày |

---

## 🔧 Cấu Hình

### Thiết Lập Kênh Log

```
/vrsetlog #moderation-log
```
Bot sẽ gửi tất cả hành động quản lý đến kênh này.

### Thiết Lập Role Muted

```
/vrsetmutedrole @Muted
```
Khi mute người dùng, bot sẽ gán role này cho họ.

### Quản Lý Bypass

```
/vrbypass user:@User               # Thêm bypass cho user (chọn từ danh sách)
/vrbypass role:@Role               # Thêm bypass cho role (chọn từ danh sách)
/vrbypass channel:#channel         # Thêm bypass cho channel (chọn từ danh sách)
```

Xóa bypass:
```
/vrunbypass user:@User             # Xóa bypass cho user
/vrunbypass role:@Role             # Xóa bypass cho role
/vrunbypass channel:#channel       # Xóa bypass cho channel
```

---

## 💾 Cài Đặt

### 1. Yêu Cầu
- **Python** 3.11+
- **pip** hoặc hệ thống package manager
- **Discord Bot Token** (từ [Discord Developer Portal](https://discord.com/developers/applications))

### 2. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

Hoặc sử dụng uv/poetry:

```bash
pip install aiofiles discord-py>=2.6.4 python-dotenv>=1.2.1
```

### 3. Cấu Hình Token

**Biến Môi Trường (Require)**

Tạo tệp `.env` trong thư mục gốc:
```env
DISCORD_BOT_TOKEN=your_bot_token_here
```

Thêm vào Secrets với key `DISCORD_BOT_TOKEN`

### 4. Thiết Lập Authorized Users

Chỉnh sửa `data/authorized_users.json`:
```json
{
  "authorized_users": [
    123456789012345678,
    987654321098765432
  ],
  "description": "Danh sách ID người dùng được phép sử dụng lệnh quản lý"
}
```

Tìm ID người dùng: Right-click → Copy User ID (bật Developer Mode)

### 5. Tạo Role & Channel

Trong Discord Server:
1. Tạo role `Muted` (remove send messages permission)
2. Tạo channel `#moderation-log` (chỉ admins xem)
3. Chạy: `/vrsetlog #moderation-log` và `/vrsetmutedrole @Muted`

### 6. Chạy Bot

```bash
python main.py
```

Hoặc nếu sử dụng Replit:
```bash
python main.py
```

---

## 📁 Cấu Trúc Tệp

```
MODERATION-BOT-DISCORD/
├── main.py                          # Điểm khởi động, khởi tạo bot
├── pyproject.toml                   # Phụ thuộc dự án
├── README.md                        # Tài liệu này
├── .env                             # Token (không push lên git)
├── src/
│   ├── __init__.py
│   ├── moderation.py                # Lệnh quản lý (ban, mute, warn, etc)
│   ├── automod.py                   # Kiểm duyệt tự động & cảnh báo
│   ├── antispam.py                  # Phát hiện spam
│   ├── antilink.py                  # Chống link & scam & token
│   └── utils.py                     # Tiện ích chung
└── data/
    ├── config.json                  # Cấu hình server (log channel, role, etc)
    ├── authorized_users.json        # Danh sách mod được phép
    ├── ban-mute.json                # Hồ sơ cấm/mute
    ├── ban-mute-BlockWord.json      # Từ bị chặn & domain scam
    └── warn.json                    # Hồ sơ cảnh báo
```

---

## 📖 Hướng Dẫn Chi Tiết

### Ví Dụ 1: Ban người dùng vì spam

```
/vrban @Spammer 7d Spam liên tục
```

**Kết quả**:
- Xóa tất cả tin nhắn của người dùng
- Ban 7 ngày (auto Unban)
- Ghi log vào `#moderation-log`
- Auto Unban sau 7 ngày

### Ví Dụ 2: Cảnh báo người dùng

```
/vrwarn @User Profanity
```

**Kết quả** (tuỳ lần cảnh báo):
- Lần 1/3: Chỉ cảnh báo
- Lần 2/3: Tự động mute 10 phút + cảnh báo
- Lần 3/3: Tự động ban 1 ngày + cảnh báo

### Ví Dụ 3: Bypass role từ auto-mod

```
/vrbypass role:@Helper
```

Kết quả:
- Helper không bị kiểm duyệt tự động
- Sử dụng `/vrunbypass role:@Helper` để xóa bypass

### Ví Dụ 4: Kiểm tra trạng thái

```
/vrstatus
```

**Hiển thị**:
- Bot latency (ping)
- Log channel được cấu hình
- Muted role được cấu hình
- Số user/role/channel bypass
- Tổng cảnh báo trên server

---

## 📊 Dữ Liệu & JSON

### `authorized_users.json`

Danh sách người dùng có quyền dùng lệnh quản lý:

```json
{
  "authorized_users": [123456789012345678, 987654321098765432],
  "description": "Danh sách ID người dùng được phép sử dụng lệnh quản lý"
}
```

### `config.json`

Cấu hình server (tự tạo khi dùng lệnh `/vrsetlog`, `/vrsetmutedrole`, `/vrbypass`):

```json
{
  "guilds": {
    "123456789": {
      "log_channel": 987654321,
      "muted_role": 555555555,
      "bypass_users": [111111111],
      "bypass_roles": [222222222],
      "bypass_channels": [333333333]
    }
  }
}
```

### `ban-mute-BlockWord.json`

Từ khóa bị chặn và domain lừa đảo:

```json
{
  "blocked_words": {
    "badword1": {"action": "warn", "time": null},
    "badword2": {"action": "mute", "time": "10m"},
    "badword3": {"action": "ban", "time": "1d"}
  },
  "blocked_links": ["scamsite.com", "phishing.net"],
  "scam_domains": ["nitro-free.gg", "discord-gift.scam"]
}
```

**action**: `warn` | `mute` | `ban`
**time**: Duration hoặc `null` (vĩnh viễn)

### `warn.json`

Hồ sơ cảnh báo:

```json
{
  "warnings": {
    "123456789": {
      "987654321": [
        {
          "reason": "Spam",
          "moderator_id": 111111111,
          "timestamp": "2024-12-04T10:30:00.000000",
          "auto": true
        }
      ]
    }
  }
}
```

### `ban-mute.json`

Hồ sơ cấm/mute:

```json
{
  "bans": {
    "123456789": {
      "987654321": {
        "moderator_id": 111111111,
        "reason": "Spam",
        "duration": "7d",
        "expiry": "2024-12-11T10:30:00.000000",
        "timestamp": "2024-12-04T10:30:00.000000"
      }
    }
  },
  "mutes": {...}
}
```

---

## ⚙️ Tính Năng Nâng Cao

### Auto Moderation Flow

```
Tin nhắn người dùng
    ↓
[Bypass check] → Bypass? → Return
    ↓
[Blocked words check] → Phát hiện? → Delete + Action
    ↓
[Anti-scam check] → Scam? → Delete + Ban/Mute
    ↓
[Anti-spam check] → Spam? → Delete + Mute/Warn/RateLimit
    ↓
[Anti-link check] → Banned link? → Delete + Warn
    ↓
Normal message processing
```

### Cảnh Báo Auto-Action

```
User cảnh báo 1/3 → Chỉ ghi log
User cảnh báo 2/3 → Tự động mute 10 phút + log
User cảnh báo 3/3 → Tự động ban 1 ngày + log + xóa tin nhắn
```

### Rate Limiting

Khi phát hiện rate limit (10+ tin nhắn trong 5 giây):
- Người dùng bị giới hạn gửi 1 tin nhắn/phút
- Nhận DM cảnh báo
- Hết 1 phút tự động hết hạn

---

## 🐛 Troubleshooting

### Bot không phản hồi
- Kiểm tra token trong `.env`
- Kiểm tra bot có được invite vào server không
- Kiểm tra bot permissions (Administrator)

### Lệnh không hiển thị
- Chạy bot lại để sync slash commands
- Kiểm tra bot permissions trong server settings

### Auto-mod không hoạt động
- Kiểm tra `bypass_*` có chứa user ID không
- Kiểm tra config.json có `log_channel` không
- Kiểm tra authorized_users.json (chỉ cảnh báo auto-trigger, không cần auth)

### Không thể cấm/mute người
- Kiểm tra bot role có cao hơn target role không
- Kiểm tra bot có permission "Ban Members" / "Moderate Members"

---



## 📞 Hỗ Trợ & Đóng Góp

Tìm bug hoặc có đề xuất? Vui lòng tạo issue hoặc pull request.

---

## 📜 License

MIT License - Tự do sử dụng cho mục đích cá nhân và thương mại.

---

**Bot được phát triển với ❤️ cho cộng đồng Discord Việt**

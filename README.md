# 🎯 Okey Match — API Endpoint Test Suite

Okey Match backend API'sinin otomatik test paketi. Tüm endpoint'leri test eder, profesyonel HTML raporu oluşturur ve spec uyumluluk analizi sunar.

### 🌐 [📊 Canlı Test Raporu →](https://kolaytech.github.io/okey-match-api-test/api_test_report.html)

## 📊 Son Test Sonuçları

| Metrik | Değer |
|---|---|
| Toplam Endpoint | 36 |
| ✅ Başarılı | 23 |
| ❌ Başarısız | 13 |
| Başarı Oranı | **%64** |

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Python 3.8+
- İnternet bağlantısı (API sunucusuna erişim)

### Test Çalıştırma

```bash
python3 test_api.py
```

Bu komut:
1. Tüm endpoint'leri sırasıyla test eder
2. `results.json` dosyasına sonuçları yazar
3. `api_test_report.html` interaktif raporu oluşturur

### Raporu Görüntüleme

```bash
open api_test_report.html    # macOS
xdg-open api_test_report.html  # Linux
```

## 📁 Dosya Yapısı

```
okey-match-api-test/
├── test_api.py              # Ana test scripti
├── api_test_report.html     # İnteraktif HTML test raporu
├── results.json             # Ham test sonuçları (JSON)
├── test_endpoints.sh        # Shell script alternatifi
└── README.md
```

## 🔧 Yapılandırma

Test scripti içindeki değişkenler:

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `BASE_URL` | `http://94.138.209.132:8080` | API sunucu adresi |
| `TEST_PHONE` | `+905551234567` | Test telefon numarası |
| `TEST_PASSWORD` | `Test123456!` | Test şifresi |

## 📋 Test Edilen Modüller

| Modül | Endpoint Sayısı | Durum |
|---|---|---|
| 🔐 Auth | 5 | Login, Register, OTP, Refresh |
| 📋 Listings | 8 | CRUD + Filtreleme + Geo |
| 📩 Applications | 5 | Apply, Accept, Reject |
| 🔔 Notifications | 5 | List, Read, Device Token |
| 💳 Payments | 3 | Process, 3D Secure |
| ⭐ Ratings | 2 | Create, List |
| 🏠 Rooms | 2 | Get, Confirm Attendance |
| 💎 Subscriptions | 5 | Plans, Create, Cancel, Boost |

## 📊 Rapor Özellikleri

HTML raporu şu bölümleri içerir:

- **Özet Kartları** — Toplam, başarılı, başarısız, oran
- **Spec Uyumluluk Analizi** — Eksik endpoint'ler, format farkları, DTO uyumsuzlukları
- **Endpoint Detayları** — Her endpoint için request/response body
- **Hata Analizi** — Başarısız endpoint'ler için sebep ve çözüm önerisi
- **Filtreleme** — Tümü / Başarılı / Başarısız görünüm

## 🔗 İlgili Repolar

- [okey_match](https://github.com/kolaytech/okey_match) — Flutter mobil uygulama

## 📝 Lisans

Bu proje [kolaytech](https://github.com/kolaytech) organizasyonuna aittir.

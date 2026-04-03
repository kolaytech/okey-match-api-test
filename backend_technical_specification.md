# Backend Technical Specification — Okey Match

> Bu doküman, mevcut Okey Match Flutter mobil uygulamasının analizi sonucunda hazırlanmıştır. .NET backend geliştiricisinin implementasyona doğrudan başlayabileceği seviyede detay içerir. Tüm endpoint, DTO, entity ve iş kuralı tanımları uygulamadaki mevcut yapıyla birebir uyumludur.

---

## 1. Project Overview

### 1.1 Uygulamanın Amacı

Okey Match, okey oyuncularının birbirlerini bulmasını, masa kurmasını ve oyun organizasyonu yapmasını sağlayan bir sosyal eşleştirme platformudur. Kullanıcılar ilan oluşturabilir, mevcut ilanlara başvurabilir, maç odalarında buluşabilir ve birbirlerini puanlayabilir.

### 1.2 Backend'in Sorumlulukları

| Alan | Sorumluluk |
|------|-----------|
| **Kimlik doğrulama** | Telefon + OTP tabanlı auth, JWT token yönetimi |
| **Kullanıcı yönetimi** | Profil CRUD, onboarding, profil doğrulama |
| **İlan yönetimi** | İlan oluşturma, listeleme, filtreleme, durum yönetimi |
| **Başvuru yönetimi** | İlanlara başvuru, kabul/red akışları |
| **Maç odası yönetimi** | Oda oluşturma, katılım onayı, durum takibi |
| **Puanlama sistemi** | Maç sonrası puanlama, güven skoru hesaplama |
| **Dosya yönetimi** | Profil fotoğrafı ve selfie upload |
| **Bildirim sistemi** | Push notification altyapısı |
| **Analytics desteği** | User property senkronizasyonu, subscription/auth event verileri |

### 1.3 Mobil Uygulama ile Backend İlişkisi

```
┌─────────────┐      HTTPS/REST       ┌─────────────────┐
│  Flutter App │ ◄──────────────────► │  .NET Web API    │
│  (Riverpod)  │    JSON + JWT Bearer  │  (Clean Arch.)   │
└─────────────┘                       └────────┬────────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │                     │
                              ┌─────┴─────┐       ┌──────┴──────┐
                              │ PostgreSQL │       │ Blob Storage│
                              │ (EF Core)  │       │ (S3 / Azure)│
                              └───────────┘       └─────────────┘
```

- **Base URL**: `https://api.okeymatch.com/v1`
- **Auth**: Bearer JWT token (Authorization header)
- **Content-Type**: `application/json`
- **Timeout**: Connect 15s, Receive 15s (mobil tarafta tanımlı)

---

## 2. Existing App Analysis

### 2.1 Mevcut Ekranlar

| # | Ekran | Route | Açıklama |
|---|-------|-------|----------|
| 1 | PhoneEntryPage | `/auth/phone` | Telefon numarası girişi (+90 prefix) |
| 2 | OtpVerifyPage | `/auth/otp` | 6 haneli OTP doğrulama, 60s geri sayım |
| 3 | OnboardingWizardPage | `/onboarding` | 3 adımlı profil tamamlama (ad/yaş → şehir/ilçe → fotoğraf) |
| 4 | ListingsPage | `/` | Ana sayfa, ilan listesi + filtreler |
| 5 | ExplorePage | `/explore` | Harita + liste görünümü, konum bazlı keşif |
| 6 | CreateListingPage | `/listings/create` | Yeni ilan oluşturma formu |
| 7 | ListingDetailPage | `/listings/:id` | İlan detayı + başvuru |
| 8 | ApplicationsPage | `/listings/:id/applications` | İlana gelen başvurular (owner görünümü) |
| 9 | ProfilePage | `/profile` | Profil sayfası (istatistik, rozetler, güven skoru, yorumlar, son oyunlar) |
| 10 | EditProfilePage | `/profile/edit` | Profil düzenleme |
| 11 | SettingsPage | `/profile/settings` | Ayarlar (tema, hesap, çıkış) |
| 12 | AccountInfoPage | `/profile/settings/account` | Hesap bilgileri düzenleme + email OTP doğrulama |
| 13 | VerifyProfilePage | `/profile/verify` | Selfie ile profil doğrulama (şu an devre dışı, AWS Rekognition planlanıyor) |
| 14 | MatchRoomPage | `/rooms/:id` | Maç odası (geri sayım, katılımcılar, katılım onayı) |
| 15 | CreateRatingPage | `/ratings/create` | Maç sonrası puan verme |
| 16 | UserRatingsPage | `/users/:id/ratings` | Kullanıcı puanları listesi |

### 2.2 Mevcut Feature'lar

#### Auth
- Telefon numarası ile OTP gönderimi (+90 prefix, 10 haneli numara)
- 6 haneli OTP doğrulama (mock: `123456`)
- 60 saniye bekleme süresi, tekrar gönder mekanizması
- Başarılı doğrulama sonrası `isAuthenticatedProvider` aktif

#### Profile
- `getMe()`: Mevcut kullanıcı profili
- `updateMe()`: Profil güncelleme (fullName, nickname, city, district, profilePhoto, age, email)
- `verifyProfile()`: Selfie + profil fotoğrafı karşılaştırma (planlanıyor)
- Güven skoru, rozetler, son yorumlar, son oyunlar görüntüleme
- Email OTP doğrulama (mock: `1234`)

#### Listings
- İlan listeleme (city, district, level, page, limit filtreleri)
- İlan detayı görüntüleme
- İlan oluşturma (başlık, açıklama, konum, tarih, seviye, yaş aralığı, katılımcılar)
- İlan silme
- Client-side filtreleme: zaman, mesafe, seviye, ilçe, oyuncu sayısı, yaş aralığı
- Google Places API ile mekan arama (client tarafında)

#### Applications
- İlana başvuru (joinedAsGroupCount, message)
- Başvuru listeleme (listingId bazlı)
- Başvuru kabul / red (ilan sahibi yetkisi)

#### Match
- Oda detayı görüntüleme (katılımcılar, geri sayım)
- Katılım onayı (joined / noShow)

#### Ratings
- Puan verme (score 1-5, comment)
- Kullanıcı puanları listeleme

### 2.3 DTO'lar ve Kullanım Alanları

Uygulama `domain/entities/` katmanında tanımlı modelleri hem request hem response olarak kullanıyor. Ayrı DTO dosyaları yok; usecase `Params` sınıfları request DTO görevi görüyor:

| Params Sınıfı | Kullanım |
|---------------|----------|
| `VerifyOtpParams` | phone + code |
| `UpdateMeParams` | fullName, nickname, city, district, profilePhoto, age, email |
| `GetListingsParams` | city, district, level, page, limit |
| `CreateListingParams` | title, description, city, district, lat, lng, placeName, dateTime, playerNeeded, level, minAge, maxAge, participants |
| `ApplyListingParams` | listingId, joinedAsGroupCount, message |
| `ConfirmAttendanceParams` | roomId, status |
| `CreateRatingParams` | roomId, toUserId, score, comment |

### 2.4 Backend Açısından Dikkat Çeken Noktalar

1. **Tüm data source'lar mock**: Gerçek API çağrısı yapılmıyor; backend tamamen sıfırdan geliştirilecek
2. **Token yönetimi eksik**: `AuthToken` entity'si var ama token persist edilmiyor (SharedPreferences'a yazılmıyor)
3. **`currentUserIdProvider` hardcoded**: `usr_001` olarak sabitlenmiş
4. **`totalSlots` sabit 4**: `ListingEntity.totalSlots` getter'ı her zaman 4 döndürüyor
5. **Şehir hardcoded**: CreateListingPage'de `city: 'İstanbul'` sabit
6. **Listing detail başvuru UI-only**: `_showApplyDialog` başarı durumunu mock ediyor, usecase çağırmıyor
7. **Google API key client-side**: `google_places_service.dart` içinde hardcoded API key var

---

## 3. Missing / Ambiguous Areas

### 3.1 Backend Geliştirme Öncesi Netleştirilmesi Gereken Konular

#### Kritik Kararlar

| # | Konu | Mevcut Durum | Karar Gereksinimi |
|---|------|-------------|-------------------|
| 1 | **Kullanıcı kaydı** | İlk OTP doğrulama = otomatik kayıt mı? | İlk `verifyOtp` çağrısında telefon numarası ile kullanıcı yoksa otomatik oluşturulmalı. Response'da `isNewUser: true` dönülerek mobil tarafın onboarding'e yönlendirmesi sağlanmalı. |
| 2 | **Token refresh** | Sadece `accessToken` var, `refreshToken` opsiyonel | Refresh token mekanizması implementasyonu şart. `accessToken` süresi (örn: 1 saat), `refreshToken` süresi (örn: 30 gün) belirlenmelidir. |
| 3 | **Dosya upload** | `profilePhoto` string path olarak tutuluyor | Multipart form-data ile upload endpoint'i gerekli. Blob storage (Azure Blob / AWS S3) entegrasyonu. Response'da URL dönülmeli. |
| 4 | **Maç odası oluşturma** | Sadece `getRoomById` var, oluşturma yok | Listing dolduğunda (tüm slotlar dolunca) otomatik oda oluşturulmalı mı? Yoksa ilan sahibi manuel mi başlatır? **Önerilen**: Listing `full` durumuna geçtiğinde backend otomatik `MatchRoom` oluşturur. |
| 5 | **totalSlots** | 4 olarak hardcoded | Backend'de listing bazlı `maxPlayers` (varsayılan 4) olarak tutulmalı. Okey 4 kişilik oyun; ancak gelecekte farklı masa boyutları için esneklik sağlanabilir. |
| 6 | **Google Places** | Client-side API key | Backend'de proxy endpoint sağlanmalı. API key'in client tarafında olması güvenlik riski. |

#### Eksik Endpoint'ler

| # | Endpoint İhtiyacı | Açıklama |
|---|-------------------|----------|
| 1 | `PUT /listings/:id` | İlan güncelleme (mevcut uygulamada yok ama gerekli) |
| 2 | `PATCH /listings/:id/cancel` | İlan iptal etme |
| 3 | `DELETE /applications/:id` | Başvuru iptal (başvuran tarafından) |
| 4 | `POST /auth/refresh` | Token yenileme |
| 5 | `POST /users/email/send-otp` | Email OTP gönderimi |
| 6 | `POST /users/email/verify-otp` | Email OTP doğrulama |
| 7 | `POST /files/upload` | Dosya yükleme |
| 8 | `GET /users/:id` | Başka kullanıcının public profili |
| 9 | `GET /users/me/listings` | Kendi ilanlarım |
| 10 | `GET /users/me/applications` | Kendi başvurularım |
| 11 | `GET /users/me/matches` | Maç geçmişim |
| 12 | `DELETE /users/me` | Hesap silme |
| 13 | `GET /notifications` | Bildirimler |
| 14 | `POST /notifications/read` | Bildirim okundu |

#### Eksik İş Kuralları

| # | Konu | Belirsizlik |
|---|------|------------|
| 1 | **Rozet kazanım kuralları** | `UserBadge` entity'si var ama hangi koşulda hangi rozet kazanılır tanımlı değil |
| 2 | **Güven skoru formülü** | `trustScore`, `onTimeRate`, `cancellationRate`, `avgUserRating` gösteriliyor ama hesaplama algoritması yok |
| 3 | **Rating aggregation** | Tek bir puanın genel `rating` ortalamasına etkisi |
| 4 | **İlan dolma mantığı** | `participants.length >= totalSlots` olduğunda status otomatik `full` mı olur? Kabul edilen başvuruların etkisi? |
| 5 | **Maç tamamlanma** | Room `finished` durumuna ne zaman geçer? `scheduledAt` + belirli süre sonra mı? |
| 6 | **Boosted visibility** | `ListingVisibility.boosted` ne yapar? Öne çıkarma mantığı? Ücretli mi? |

#### Eksik DTO Alanları

| Entity | Eksik Alan | Açıklama |
|--------|-----------|----------|
| `UserEntity` | `profileCompleted` | Onboarding tamamlanma durumu (şu an SharedPreferences'da) |
| `ListingEntity` | `maxPlayers` | Toplam oyuncu sayısı (hardcoded 4 yerine) |
| `ListingEntity` | `updatedAt` | Güncelleme tarihi |
| `ApplicationEntity` | `updatedAt` | Status değişiklik tarihi |
| `MatchRoomEntity` | `placeName`, `city`, `district` | Konum bilgisi (listing'den alınabilir) |
| `RatingEntity` | `tags` | Hızlı etiket sistemi (opsiyonel, örn: "dakik", "fair play") |

---

## 4. Domain Model / Entity Structure

### 4.1 Entity Diagram

```
┌──────────┐     1:N     ┌──────────────┐     1:N     ┌───────────────┐
│   User   │────────────►│   Listing    │────────────►│  Application  │
│          │             │              │             │               │
└────┬─────┘             └──────┬───────┘             └───────────────┘
     │                          │
     │ 1:N                      │ 1:1
     │                          ▼
     │                   ┌──────────────┐     N:1
     │                   │  MatchRoom   │◄────────────┐
     │                   │              │             │
     │                   └──────┬───────┘     ┌───────┴──────────┐
     │                          │ 1:N         │ MatchParticipant │
     │                          ▼             └──────────────────┘
     │                   ┌──────────────┐
     │      1:N          │    Rating    │
     ├──────────────────►│              │
     │                   └──────────────┘
     │
     │ 1:N               ┌────────────────┐
     ├──────────────────►│  Notification  │
     │                   └────────────────┘
     │ 1:N               ┌────────────────┐
     └──────────────────►│  DeviceToken   │
                         └────────────────┘
```

### 4.2 Entity Tanımları (C# / .NET)

#### User

```csharp
public class User
{
    public Guid Id { get; set; }
    public string Phone { get; set; }               // "+905321234567"
    public string? Email { get; set; }
    public bool EmailVerified { get; set; }
    public string? FullName { get; set; }
    public string? Nickname { get; set; }
    public string? ProfilePhotoUrl { get; set; }
    public string? SelfiePhotoUrl { get; set; }
    public string? City { get; set; }
    public string? District { get; set; }
    public int? Age { get; set; }
    public Level Level { get; set; } = Level.Beginner;
    public double Rating { get; set; }               // Ortalama puan (computed)
    public bool Verified { get; set; }                // Selfie doğrulama
    public bool ProfileCompleted { get; set; }        // Onboarding tamamlandı mı
    public int TotalMatches { get; set; }             // Toplam maç sayısı (computed)
    public double TrustScore { get; set; }            // Güven skoru (computed)
    public double CancellationRate { get; set; }      // İptal oranı (computed)
    public double OnTimeRate { get; set; }            // Zamanında katılım oranı (computed)
    public string? RefreshToken { get; set; }
    public DateTime? RefreshTokenExpiry { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
    public bool IsDeleted { get; set; }               // Soft delete

    // Navigation
    public ICollection<Listing> Listings { get; set; }
    public ICollection<Application> Applications { get; set; }
    public ICollection<MatchParticipant> MatchParticipants { get; set; }
    public ICollection<Rating> GivenRatings { get; set; }
    public ICollection<Rating> ReceivedRatings { get; set; }
    public ICollection<UserBadge> Badges { get; set; }
    public ICollection<Notification> Notifications { get; set; }
    public ICollection<DeviceToken> DeviceTokens { get; set; }
}
```

#### Listing

```csharp
public class Listing
{
    public Guid Id { get; set; }
    public Guid OwnerId { get; set; }
    public string Title { get; set; }
    public string Description { get; set; }
    public string City { get; set; }
    public string District { get; set; }
    public double Lat { get; set; }
    public double Lng { get; set; }
    public string PlaceName { get; set; }
    public DateTime DateTime { get; set; }            // Planlanan oyun zamanı
    public int PlayerNeeded { get; set; }              // Aranan oyuncu sayısı
    public int MaxPlayers { get; set; } = 4;           // Toplam slot
    public Level Level { get; set; }
    public ListingStatus Status { get; set; } = ListingStatus.Open;
    public ListingVisibility Visibility { get; set; } = ListingVisibility.Normal;
    public int? MinAge { get; set; }
    public int? MaxAge { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
    public bool IsDeleted { get; set; }

    // Navigation
    public User Owner { get; set; }
    public ICollection<Application> Applications { get; set; }
    public ICollection<ListingParticipant> Participants { get; set; }
    public MatchRoom? MatchRoom { get; set; }
}
```

#### ListingParticipant

```csharp
public class ListingParticipant
{
    public Guid Id { get; set; }
    public Guid ListingId { get; set; }
    public Guid UserId { get; set; }
    public bool IsOwner { get; set; }
    public DateTime JoinedAt { get; set; }

    // Navigation
    public Listing Listing { get; set; }
    public User User { get; set; }
}
```

#### Application

```csharp
public class Application
{
    public Guid Id { get; set; }
    public Guid ListingId { get; set; }
    public Guid ApplicantUserId { get; set; }
    public int JoinedAsGroupCount { get; set; } = 1;
    public string? Message { get; set; }
    public ApplicationStatus Status { get; set; } = ApplicationStatus.Pending;
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }

    // Navigation
    public Listing Listing { get; set; }
    public User Applicant { get; set; }
}
```

#### MatchRoom

```csharp
public class MatchRoom
{
    public Guid Id { get; set; }
    public Guid ListingId { get; set; }
    public DateTime ScheduledAt { get; set; }
    public RoomStatus Status { get; set; } = RoomStatus.Waiting;
    public DateTime ConfirmationDeadline { get; set; }
    public DateTime CreatedAt { get; set; }

    // Navigation
    public Listing Listing { get; set; }
    public ICollection<MatchParticipant> Participants { get; set; }
}
```

#### MatchParticipant

```csharp
public class MatchParticipant
{
    public Guid Id { get; set; }
    public Guid RoomId { get; set; }
    public Guid UserId { get; set; }
    public AttendanceStatus AttendanceStatus { get; set; } = AttendanceStatus.Pending;
    public DateTime JoinedAt { get; set; }

    // Navigation
    public MatchRoom Room { get; set; }
    public User User { get; set; }
}
```

#### Rating

```csharp
public class Rating
{
    public Guid Id { get; set; }
    public Guid RoomId { get; set; }
    public Guid FromUserId { get; set; }
    public Guid ToUserId { get; set; }
    public int Score { get; set; }                    // 1-5
    public string? Comment { get; set; }
    public DateTime CreatedAt { get; set; }

    // Navigation
    public MatchRoom Room { get; set; }
    public User FromUser { get; set; }
    public User ToUser { get; set; }
}
```

#### Badge & UserBadge

```csharp
public class Badge
{
    public Guid Id { get; set; }
    public string Code { get; set; }                  // "10_matches", "verified_profile" vb.
    public string Title { get; set; }                 // "10 Maç Tamamladı"
    public string Icon { get; set; }                  // "trophy", "verified", "shield", "clock", "star"
    public string? Description { get; set; }
    public int? RequiredMatches { get; set; }          // Rozet koşulu: minimum maç
    public double? RequiredTrustScore { get; set; }    // Rozet koşulu: minimum güven
    public bool RequiresVerification { get; set; }

    public ICollection<UserBadge> UserBadges { get; set; }
}

public class UserBadge
{
    public Guid Id { get; set; }
    public Guid UserId { get; set; }
    public Guid BadgeId { get; set; }
    public DateTime EarnedAt { get; set; }

    public User User { get; set; }
    public Badge Badge { get; set; }
}
```

#### Notification

```csharp
public class Notification
{
    public Guid Id { get; set; }
    public Guid UserId { get; set; }                   // Bildirimi alan kullanıcı
    public NotificationType Type { get; set; }
    public string Title { get; set; }                   // "Başvurunuz kabul edildi!"
    public string Body { get; set; }                    // "Akşam Okey Partisi ilanına başvurunuz kabul edildi."
    public Dictionary<string, object> Data { get; set; } // Deep link bilgileri: { "listingId": "...", "roomId": "..." }
    public bool Read { get; set; }
    public DateTime CreatedAt { get; set; }

    // Navigation
    public User User { get; set; }
}
```

> **Not:** `Data` alanı JSON olarak saklanır (`jsonb` PostgreSQL'de). Mobil uygulama bu alan üzerinden bildirime tıklandığında doğru sayfaya yönlendirme yapar. Her bildirim türü için `Data` içeriği aşağıda detaylıdır.

#### DeviceToken (FCM Push Notification için)

```csharp
public class DeviceToken
{
    public Guid Id { get; set; }
    public Guid UserId { get; set; }
    public string Token { get; set; }                   // FCM registration token
    public string Platform { get; set; }                // "ios" veya "android"
    public DateTime CreatedAt { get; set; }
    public DateTime? LastUsedAt { get; set; }

    // Navigation
    public User User { get; set; }
}
```

> **Not:** Bir kullanıcının birden fazla cihazı olabilir (telefon + tablet). Her cihaz için ayrı token saklanır. Token geçersiz olduğunda (FCM `NotRegistered` hatası) kayıt silinir.

#### SubscriptionPlan

Tüm planların tanımlarını tutan tablo. Fiyat, süre ve içerdiği özellikler backend'den yönetilir.

```csharp
public class SubscriptionPlan
{
    public Guid Id { get; set; }
    public SubscriptionPlanType Type { get; set; }     // Daily, Monthly, Yearly
    public string Name { get; set; }                   // "Günlük Geçiş", "Aylık Plan", "Yıllık Plan"
    public string? Description { get; set; }           // Kısa açıklama
    public decimal Price { get; set; }                 // 14.99, 79.99, 599.99
    public string Currency { get; set; } = "TRY";
    public int DurationDays { get; set; }              // 1, 30, 365
    public int? SavingsPercent { get; set; }           // null, null, 37
    public int BoostCredits { get; set; }              // 0, 1, 12
    public bool UnlimitedListings { get; set; }
    public bool UnlimitedApplications { get; set; }
    public bool AdvancedFilters { get; set; }
    public bool ViewApplicantDetails { get; set; }
    public bool ProBadge { get; set; }
    public bool IsActive { get; set; } = true;         // Plan satışta mı?
    public int SortOrder { get; set; }                 // Sıralama (UI'da gösterim)
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }

    // Navigation
    public ICollection<Subscription> Subscriptions { get; set; }
}
```

#### Subscription

Kullanıcının aktif veya geçmiş abonelik kayıtları.

```csharp
public class Subscription
{
    public Guid Id { get; set; }
    public Guid UserId { get; set; }
    public Guid PlanId { get; set; }
    public SubscriptionStatus Status { get; set; } = SubscriptionStatus.Active;
    public DateTime StartedAt { get; set; }
    public DateTime ExpiresAt { get; set; }
    public DateTime? CancelledAt { get; set; }
    public string? PaymentProvider { get; set; }       // "apple", "google", "stripe"
    public string? PaymentTransactionId { get; set; }  // Ödeme sağlayıcı referansı
    public int BoostCreditsRemaining { get; set; }     // Kalan boost hakkı
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }

    // Navigation
    public User User { get; set; }
    public SubscriptionPlan Plan { get; set; }
}
```

#### ListingBoost

İlan öne çıkarma kayıtları.

```csharp
public class ListingBoost
{
    public Guid Id { get; set; }
    public Guid ListingId { get; set; }
    public Guid UserId { get; set; }
    public Guid SubscriptionId { get; set; }           // Hangi abonelikten kullanıldı
    public DateTime BoostedAt { get; set; }
    public DateTime ExpiresAt { get; set; }            // Boost süresi (varsayılan 24 saat)
    public DateTime CreatedAt { get; set; }

    // Navigation
    public Listing Listing { get; set; }
    public User User { get; set; }
    public Subscription Subscription { get; set; }
}
```

#### OtpRecord (Dahili — API'ye expose edilmez)

```csharp
public class OtpRecord
{
    public Guid Id { get; set; }
    public string Target { get; set; }                // Telefon veya email
    public string Code { get; set; }                  // 6 haneli kod
    public OtpPurpose Purpose { get; set; }           // PhoneAuth, EmailVerification
    public int AttemptCount { get; set; }
    public bool IsUsed { get; set; }
    public DateTime ExpiresAt { get; set; }
    public DateTime CreatedAt { get; set; }
}

public enum OtpPurpose { PhoneAuth, EmailVerification }
```

### 4.3 Enum Tanımları

```csharp
public enum Level
{
    Beginner = 0,
    Mid = 1,
    Advanced = 2
}

public enum ListingStatus
{
    Open = 0,
    Pending = 1,
    Full = 2,
    Completed = 3,
    Cancelled = 4
}

public enum ListingVisibility
{
    Normal = 0,
    Boosted = 1
}

public enum ApplicationStatus
{
    Pending = 0,
    Accepted = 1,
    Rejected = 2,
    Cancelled = 3
}

public enum RoomStatus
{
    Waiting = 0,
    Active = 1,
    Finished = 2,
    Cancelled = 3
}

public enum AttendanceStatus
{
    Pending = 0,
    Joined = 1,
    NoShow = 2
}

public enum NotificationType
{
    ApplicationReceived = 0,   // İlan sahibine: yeni başvuru geldi
    ApplicationAccepted = 1,   // Başvuru sahibine: başvurusu kabul edildi
    ApplicationRejected = 2,   // Başvuru sahibine: başvurusu reddedildi
    RoomCreated = 3,           // Tüm katılımcılara: maç odası oluşturuldu
    AttendanceReminder = 4,    // Onay bekleyenlere: maça 30dk kaldı
    MatchCompleted = 5,        // Tüm katılımcılara: maç tamamlandı, puanlayın
    RatingReceived = 6,        // Puanlanan kullanıcıya: yeni puan aldı
    BadgeEarned = 7,           // Rozet kazanan kullanıcıya: yeni rozet
    SubscriptionExpiring = 8,  // Abonelik sona ermek üzere (3 gün önce)
    SubscriptionExpired = 9    // Abonelik sona erdi
}

public enum SubscriptionPlanType
{
    Daily = 0,
    Monthly = 1,
    Yearly = 2
}

public enum SubscriptionStatus
{
    Active = 0,
    Expired = 1,
    Cancelled = 2
}
```

### 4.4 Audit ve Soft Delete

- Tüm ana entity'lerde `CreatedAt` (UTC) ve `UpdatedAt` (UTC, nullable) alanları bulunur.
- `User` ve `Listing` entity'lerinde `IsDeleted` (bool) ile soft delete uygulanır.
- EF Core global query filter ile `IsDeleted == false` varsayılan filtre olarak eklenir.
- `Application` ve `Rating` gibi bağımlı kayıtlar silinmez; sadece status ile yönetilir.
- `Subscription` kayıtları silinmez; `Status` ile yönetilir (geçmiş abonelik geçmişi korunur).
- `ListingBoost` kayıtları silinmez; audit trail olarak saklanır.

---

## 5. API Endpoint Design

### 5.1 Auth Endpoints

#### POST /auth/send-otp

SMS ile OTP gönderir.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/auth/send-otp` |
| **Auth** | Gerekmez |
| **Rate Limit** | Aynı telefon için 60 saniyede 1 istek |

**Request:**
```json
{
  "phone": "+905321234567"
}
```

**Response (200):**
```json
{
  "message": "OTP gönderildi",
  "expiresInSeconds": 300
}
```

**Validation:**
- `phone` zorunlu, `+90` ile başlamalı, toplam 13 karakter
- Telefon formatı: `^\+90[0-9]{10}$`

**Hata Senaryoları:**
- `400` — Geçersiz telefon formatı
- `429` — Rate limit aşıldı (60s içinde tekrar istek)

---

#### POST /auth/verify-otp

OTP doğrulama yapar. Kullanıcı yoksa otomatik oluşturur.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/auth/verify-otp` |
| **Auth** | Gerekmez |

**Request:**
```json
{
  "phone": "+905321234567",
  "code": "123456"
}
```

**Response (200):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2g...",
  "expiresIn": 3600,
  "isNewUser": true,
  "profileCompleted": false
}
```

**Validation:**
- `phone` zorunlu, format kontrolü
- `code` zorunlu, 6 haneli sayısal string
- OTP süresi dolmamış olmalı (5 dakika)
- Maksimum 5 deneme hakkı

**Hata Senaryoları:**
- `400` — Geçersiz format
- `401` — Geçersiz veya süresi dolmuş OTP
- `429` — Çok fazla başarısız deneme

**Business Logic:**
1. `OtpRecord` tablosundan phone + code eşleşmesi kontrol edilir
2. Eşleşme yoksa veya süre dolmuşsa `401` döner
3. Eşleşme varsa OTP `IsUsed = true` yapılır
4. `User` tablosunda phone ile arama yapılır
5. Yoksa yeni `User` oluşturulur (`isNewUser: true`)
6. JWT access token + refresh token üretilir
7. Refresh token veritabanında saklanır

---

#### POST /auth/refresh

Token yenileme.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/auth/refresh` |
| **Auth** | Gerekmez (refresh token body'de) |

**Request:**
```json
{
  "refreshToken": "dGhpcyBpcyBhIHJlZnJlc2g..."
}
```

**Response (200):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "bmV3IHJlZnJlc2ggdG9rZW4...",
  "expiresIn": 3600
}
```

**Hata Senaryoları:**
- `401` — Geçersiz veya süresi dolmuş refresh token

---

### 5.2 User / Profile Endpoints

#### GET /users/me

Mevcut kullanıcının tam profilini döner.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/users/me` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+905321234567",
  "email": "ahmet@example.com",
  "emailVerified": true,
  "fullName": "Ahmet Yılmaz",
  "nickname": "ahmet_okey",
  "profilePhotoUrl": "https://storage.okeymatch.com/photos/usr_001.jpg",
  "selfiePhotoUrl": null,
  "city": "İstanbul",
  "district": "Kadıköy",
  "age": 28,
  "level": "mid",
  "rating": 4.2,
  "verified": false,
  "profileCompleted": true,
  "totalMatches": 15,
  "trustScore": 92.0,
  "cancellationRate": 3.0,
  "onTimeRate": 96.0,
  "avgUserRating": 4.3,
  "createdAt": "2024-01-15T00:00:00Z",
  "updatedAt": "2024-06-10T00:00:00Z",
  "recentReviews": [
    {
      "reviewerName": "Mehmet D.",
      "comment": "Çok uyumlu bir oyuncu, keyifli bir maç oldu.",
      "rating": 5.0,
      "date": "2024-06-08T00:00:00Z"
    }
  ],
  "badges": [
    {
      "id": "badge-001",
      "title": "10 Maç Tamamladı",
      "icon": "trophy",
      "earned": true
    },
    {
      "id": "badge-005",
      "title": "50 Maç Ustası",
      "icon": "trophy",
      "earned": false
    }
  ],
  "recentGames": [
    {
      "title": "Akşam Okey Partisi",
      "placeName": "Fazıl Bey Kahvesi",
      "date": "2024-06-09T00:00:00Z",
      "result": "Kazandı"
    }
  ]
}
```

> **Not:** `recentReviews` → son 4 `Rating` kaydı (toUserId = currentUser). `badges` → tüm `Badge` tablosu, `earned` alanı `UserBadge` tablosunda eşleşme olup olmadığına göre. `recentGames` → son 3 `MatchRoom` (status = Finished, participant = currentUser), listing başlığı ve sonucu ile.

---

#### PUT /users/me

Profil güncelleme. Onboarding'den de bu endpoint kullanılır.

| Özellik | Değer |
|---------|-------|
| **Route** | `PUT /v1/users/me` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "fullName": "Ahmet Yılmaz",
  "nickname": "ahmet_okey",
  "city": "İstanbul",
  "district": "Kadıköy",
  "profilePhotoUrl": "https://storage.okeymatch.com/photos/usr_001.jpg",
  "age": 28,
  "email": "ahmet@example.com"
}
```

**Response (200):** Tam `UserResponse` objesi (GET /users/me ile aynı format)

**Validation:**
- `fullName`: boş olamaz (onboarding'de zorunlu), max 100 karakter
- `age`: 16–100 arası (nullable)
- `email`: geçerli email formatı (nullable)
- `nickname`: max 30 karakter, alfanumerik + alt çizgi

**Business Logic:**
- `fullName` ve `age` dolu ise `profileCompleted = true` yapılır
- `email` değiştiğinde `emailVerified = false` yapılır

---

#### GET /users/:id

Başka kullanıcının public profilini döner.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/users/{id}` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "fullName": "Ahmet Yılmaz",
  "nickname": "ahmet_okey",
  "profilePhotoUrl": "https://storage.okeymatch.com/photos/usr_001.jpg",
  "city": "İstanbul",
  "district": "Kadıköy",
  "level": "mid",
  "rating": 4.2,
  "verified": false,
  "totalMatches": 15,
  "trustScore": 92.0,
  "badges": [],
  "recentReviews": []
}
```

> **Not:** Telefon, email, yaş gibi özel bilgiler bu endpoint'te dönülmez.

---

#### POST /users/verify-profile

Selfie ile profil doğrulama (AWS Rekognition entegrasyonu planlanıyor).

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/users/verify-profile` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "profilePhotoUrl": "https://storage.okeymatch.com/photos/profile.jpg",
  "selfiePhotoUrl": "https://storage.okeymatch.com/photos/selfie.jpg"
}
```

**Response (200):**
```json
{
  "verified": true,
  "message": "Profil doğrulama başarılı"
}
```

**Business Logic:**
1. Her iki URL'in geçerli olduğu kontrol edilir
2. AWS Rekognition `CompareFaces` API'si çağrılır
3. Benzerlik oranı %90 üzerindeyse `User.Verified = true`
4. "Doğrulanmış Profil" rozeti otomatik kazandırılır

---

#### POST /users/email/send-otp

Email doğrulama OTP'si gönderir.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/users/email/send-otp` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "email": "ahmet@example.com"
}
```

**Response (200):**
```json
{
  "message": "Doğrulama kodu gönderildi",
  "expiresInSeconds": 300
}
```

---

#### POST /users/email/verify-otp

Email OTP doğrulama.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/users/email/verify-otp` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "email": "ahmet@example.com",
  "code": "1234"
}
```

**Response (200):**
```json
{
  "emailVerified": true
}
```

**Business Logic:**
- `OtpRecord` tablosunda `Purpose = EmailVerification` ile doğrulama
- Başarılıysa `User.Email` güncellenir, `User.EmailVerified = true`

---

#### DELETE /users/me

Hesap silme (soft delete).

| Özellik | Değer |
|---------|-------|
| **Route** | `DELETE /v1/users/me` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (204):** No Content

**Business Logic:**
- `User.IsDeleted = true`
- Aktif ilanlar iptal edilir
- Bekleyen başvurular iptal edilir

---

### 5.3 File Upload Endpoint

#### POST /files/upload

Dosya yükleme (profil fotoğrafı, selfie vb.)

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/files/upload` |
| **Auth** | Bearer JWT (zorunlu) |
| **Content-Type** | `multipart/form-data` |

**Request:** Form data ile `file` alanı + `purpose` alanı (`profile_photo`, `selfie`)

**Response (200):**
```json
{
  "url": "https://storage.okeymatch.com/photos/550e8400-profile.jpg",
  "fileName": "550e8400-profile.jpg",
  "contentType": "image/jpeg",
  "sizeInBytes": 245760
}
```

**Validation:**
- Maksimum boyut: 5 MB
- İzin verilen formatlar: `image/jpeg`, `image/png`, `image/webp`
- `purpose`: `profile_photo` veya `selfie`

---

### 5.4 Listing Endpoints

#### GET /listings

İlanları listeler (filtreleme + pagination).

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/listings` |
| **Auth** | Bearer JWT (zorunlu) |

**Query Parameters:**

| Parametre | Tip | Zorunlu | Varsayılan | Açıklama |
|-----------|-----|---------|------------|----------|
| `city` | string | Hayır | — | Şehir filtresi |
| `district` | string | Hayır | — | İlçe filtresi |
| `level` | string | Hayır | — | `beginner`, `mid`, `advanced` |
| `status` | string | Hayır | `open` | İlan durumu filtresi |
| `minAge` | int | Hayır | — | Minimum yaş filtresi |
| `maxAge` | int | Hayır | — | Maksimum yaş filtresi |
| `lat` | double | Hayır | — | Kullanıcı enlemi (mesafe hesabı için) |
| `lng` | double | Hayır | — | Kullanıcı boylamı |
| `radiusKm` | double | Hayır | 15 | Mesafe filtresi (km) |
| `playerNeeded` | int | Hayır | — | Aranan oyuncu sayısı |
| `dateFrom` | DateTime | Hayır | — | Başlangıç tarihi |
| `dateTo` | DateTime | Hayır | — | Bitiş tarihi |
| `page` | int | Hayır | 1 | Sayfa numarası |
| `limit` | int | Hayır | 20 | Sayfa başına kayıt (max 50) |
| `sortBy` | string | Hayır | `dateTime` | Sıralama alanı |
| `sortOrder` | string | Hayır | `asc` | `asc` veya `desc` |

**Response (200):**
```json
{
  "items": [
    {
      "id": "lst_001",
      "ownerId": "usr_001",
      "ownerName": "Ahmet Yılmaz",
      "ownerRating": 4.7,
      "ownerTotalMatches": 32,
      "ownerVerified": true,
      "ownerTrustScore": 92.0,
      "title": "Akşam Okey Partisi",
      "description": "Rahat bir ortamda keyifli bir okey gecesi.",
      "city": "İstanbul",
      "district": "Kadıköy",
      "lat": 40.9908,
      "lng": 29.0290,
      "placeName": "Fazıl Bey Kahvesi",
      "dateTime": "2024-06-15T19:00:00Z",
      "playerNeeded": 2,
      "maxPlayers": 4,
      "level": "mid",
      "status": "open",
      "visibility": "normal",
      "minAge": 20,
      "maxAge": 35,
      "createdAt": "2024-06-15T14:00:00Z",
      "participants": [
        { "id": "usr_001", "name": "Ahmet Y.", "photoUrl": null, "isOwner": true },
        { "id": "usr_010", "name": "Serkan K.", "photoUrl": null, "isOwner": false }
      ]
    }
  ],
  "page": 1,
  "limit": 20,
  "totalCount": 45,
  "totalPages": 3
}
```

**Business Logic:**
- Yalnızca `IsDeleted == false` ve `Status` aktif (`Open`, `Pending`) olanlar varsayılan olarak döner
- `dateTime` geçmiş olanlar listelenmez (veya ayrı bir `status` filtresiyle erişilebilir)
- Mesafe hesabı: Haversine formülü (backend'de veya spatial query ile)
- `boosted` ilanlar sıralamada öne alınır

---

#### GET /listings/:id

İlan detayı.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/listings/{id}` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (200):** Tek bir listing objesi (yukarıdaki items içindekiyle aynı format)

**Hata Senaryoları:**
- `404` — İlan bulunamadı

---

#### POST /listings

Yeni ilan oluşturma.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/listings` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "title": "Akşam Okey Partisi",
  "description": "Rahat bir ortamda keyifli bir okey gecesi.",
  "city": "İstanbul",
  "district": "Kadıköy",
  "lat": 40.9908,
  "lng": 29.0290,
  "placeName": "Fazıl Bey Kahvesi",
  "dateTime": "2024-06-15T19:00:00Z",
  "playerNeeded": 2,
  "level": "mid",
  "minAge": 20,
  "maxAge": 35,
  "participants": [
    { "name": "Serkan K." }
  ]
}
```

**Response (201):** Oluşturulan listing objesi

**Validation:**
- `title`: zorunlu, 3–100 karakter
- `description`: zorunlu, 10–500 karakter
- `city`, `district`: zorunlu
- `lat`, `lng`: zorunlu, geçerli koordinatlar
- `placeName`: zorunlu
- `dateTime`: zorunlu, gelecekte olmalı (en az 1 saat sonra, en fazla 90 gün sonra)
- `playerNeeded`: 1–3 arası
- `level`: geçerli enum değeri
- `minAge`: null veya 16–100
- `maxAge`: null veya 16–100, minAge'den büyük olmalı
- `participants`: max `4 - 1 - playerNeeded` adet

**Business Logic:**
- İlan sahibi otomatik olarak `ListingParticipant` (isOwner: true) olarak eklenir
- Request'teki ek katılımcılar da eklenir
- Status: `Open`
- `maxPlayers`: varsayılan 4

---

#### PUT /listings/:id

İlan güncelleme (sadece ilan sahibi).

| Özellik | Değer |
|---------|-------|
| **Route** | `PUT /v1/listings/{id}` |
| **Auth** | Bearer JWT (zorunlu, owner check) |

**Request:** POST ile aynı format (tüm alanlar opsiyonel — partial update)

**Hata Senaryoları:**
- `403` — İlan sahibi değil
- `400` — İlan `Open` veya `Pending` durumunda değilse güncelenemez

---

#### DELETE /listings/:id

İlan silme (soft delete, sadece ilan sahibi).

| Özellik | Değer |
|---------|-------|
| **Route** | `DELETE /v1/listings/{id}` |
| **Auth** | Bearer JWT (zorunlu, owner check) |

**Response (204):** No Content

**Business Logic:**
- `Listing.IsDeleted = true`
- Bekleyen başvurular otomatik `Cancelled` yapılır
- İlişkili oda varsa `Cancelled` yapılır

---

#### PATCH /listings/:id/cancel

İlan iptal etme.

| Özellik | Değer |
|---------|-------|
| **Route** | `PATCH /v1/listings/{id}/cancel` |
| **Auth** | Bearer JWT (zorunlu, owner check) |

**Response (200):** Güncellenen listing objesi (status: cancelled)

---

### 5.5 Application Endpoints

#### GET /listings/:id/applications

İlana yapılan başvuruları listeler.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/listings/{listingId}/applications` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (200):**
```json
[
  {
    "id": "app_001",
    "listingId": "lst_001",
    "applicantUserId": "usr_010",
    "applicantName": "Serkan Yıldırım",
    "applicantRating": 4.5,
    "joinedAsGroupCount": 1,
    "message": "Merhaba, katılmak isterim!",
    "status": "pending",
    "createdAt": "2024-06-15T11:00:00Z"
  }
]
```

> **Not:** İlan sahibi tüm başvuruları görür. Diğer kullanıcılar sadece kendi başvurularını görür.

---

#### POST /listings/:id/apply

İlana başvuru yapar.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/listings/{listingId}/apply` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "joinedAsGroupCount": 1,
  "message": "Merhaba, katılmak isterim! 3 yıldır okey oynuyorum."
}
```

**Response (201):**
```json
{
  "id": "app_new_001",
  "listingId": "lst_001",
  "applicantUserId": "usr_current",
  "applicantName": "Mevcut Kullanıcı",
  "applicantRating": 4.0,
  "joinedAsGroupCount": 1,
  "message": "Merhaba, katılmak isterim!",
  "status": "pending",
  "createdAt": "2024-06-15T14:30:00Z"
}
```

**Validation:**
- `joinedAsGroupCount`: 1–3 arası
- Kalan slot sayısı kadar veya daha az olmalı
- `message`: opsiyonel, max 500 karakter

**Business Logic:**
- Kullanıcı kendi ilanına başvuramaz
- Aynı ilana tekrar başvuramaz (aktif başvurusu varken)
- İlan `Open` durumunda olmalı
- Yaş aralığı kontrolü (minAge/maxAge tanımlıysa)

**Hata Senaryoları:**
- `400` — Kendi ilanına başvuru / zaten başvurmuş / slot yetersiz
- `404` — İlan bulunamadı
- `409` — Zaten aktif başvurusu var

---

#### POST /applications/:id/accept

Başvuruyu kabul eder (ilan sahibi).

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/applications/{id}/accept` |
| **Auth** | Bearer JWT (zorunlu, listing owner check) |

**Response (200):** Güncellenen application objesi (status: accepted)

**Business Logic:**
1. Başvuru `Pending` durumunda olmalı
2. Kalan slot sayısı `joinedAsGroupCount` kadar veya fazla olmalı
3. Status → `Accepted`
4. Başvuru sahibi `ListingParticipant` olarak eklenir
5. `Listing.PlayerNeeded` güncellenir (azaltılır)
6. Tüm slotlar dolduğunda:
   - `Listing.Status` → `Full`
   - Kalan `Pending` başvurular otomatik `Rejected` yapılır
   - `MatchRoom` otomatik oluşturulur (confirmationDeadline = scheduledAt - 30dk)
7. Başvuru sahibine bildirim gönderilir

---

#### POST /applications/:id/reject

Başvuruyu reddeder (ilan sahibi).

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/applications/{id}/reject` |
| **Auth** | Bearer JWT (zorunlu, listing owner check) |

**Response (200):** Güncellenen application objesi (status: rejected)

---

#### DELETE /applications/:id

Başvuruyu iptal eder (başvuru sahibi).

| Özellik | Değer |
|---------|-------|
| **Route** | `DELETE /v1/applications/{id}` |
| **Auth** | Bearer JWT (zorunlu, applicant check) |

**Response (204):** No Content

**Business Logic:**
- Sadece `Pending` durumundaki başvurular iptal edilebilir
- `Accepted` durumundaki başvuru iptalinde slot geri açılır

---

### 5.6 Match Room Endpoints

#### GET /rooms/:id

Maç odası detayı.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/rooms/{id}` |
| **Auth** | Bearer JWT (zorunlu, participant check) |

**Response (200):**
```json
{
  "id": "room_001",
  "listingId": "lst_001",
  "scheduledAt": "2024-06-15T19:00:00Z",
  "status": "waiting",
  "confirmationDeadline": "2024-06-15T18:30:00Z",
  "createdAt": "2024-06-15T14:00:00Z",
  "participants": [
    {
      "id": "p1",
      "userId": "u1",
      "userName": "Ahmet Yılmaz",
      "userRating": 4.5,
      "joinedAt": "2024-06-15T13:15:00Z",
      "attendanceStatus": "joined"
    },
    {
      "id": "p2",
      "userId": "u2",
      "userName": "Mehmet Kaya",
      "userRating": 3.8,
      "joinedAt": "2024-06-15T13:30:00Z",
      "attendanceStatus": "pending"
    }
  ]
}
```

---

#### POST /rooms/:id/confirm-attendance

Katılım onayı veya red.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/rooms/{id}/confirm-attendance` |
| **Auth** | Bearer JWT (zorunlu, participant check) |

**Request:**
```json
{
  "status": "joined"
}
```

**Response (200):**
```json
{
  "id": "p2",
  "userId": "u2",
  "userName": "Mehmet Kaya",
  "userRating": 3.8,
  "joinedAt": "2024-06-15T13:30:00Z",
  "attendanceStatus": "joined"
}
```

**Validation:**
- `status`: `joined` veya `noShow`
- `confirmationDeadline` geçmemiş olmalı

**Business Logic:**
- Tüm katılımcılar `joined` onayladığında: `Room.Status` → `Active`
- Herhangi biri `noShow` verirse: yerine yeni oyuncu aranabilir veya oda iptal
- `noShow` veren kullanıcının `CancellationRate` artar, `TrustScore` düşer

---

### 5.7 Rating Endpoints

#### POST /ratings

Puan verme.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/ratings` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "roomId": "room_001",
  "toUserId": "usr_002",
  "score": 5,
  "comment": "Harika bir oyuncu, çok keyifli bir maçtı!"
}
```

**Response (201):**
```json
{
  "id": "r_new_001",
  "roomId": "room_001",
  "fromUserId": "usr_001",
  "fromUserName": "Ahmet Yılmaz",
  "toUserId": "usr_002",
  "toUserName": "Mehmet Kaya",
  "score": 5,
  "comment": "Harika bir oyuncu, çok keyifli bir maçtı!",
  "createdAt": "2024-06-15T22:00:00Z"
}
```

**Validation:**
- `roomId`: geçerli bir oda
- `toUserId`: odadaki bir katılımcı, kendisi olamaz
- `score`: 1–5 arası integer
- `comment`: opsiyonel, max 500 karakter
- Aynı kullanıcıya aynı oda için tekrar puan verilemez

**Business Logic:**
- Room status `Finished` olmalı
- Puan verildiğinde `ToUser.Rating` yeniden hesaplanır (tüm puanların ortalaması)
- `ToUser.TrustScore` güncellenir

---

#### GET /users/:id/ratings

Kullanıcının aldığı puanlar.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/users/{id}/ratings` |
| **Auth** | Bearer JWT (zorunlu) |
| **Pagination** | `page`, `limit` query params |

**Response (200):**
```json
{
  "items": [
    {
      "id": "r1",
      "roomId": "room_001",
      "fromUserId": "u1",
      "fromUserName": "Ahmet Yılmaz",
      "toUserId": "usr_target",
      "toUserName": "Hedef Oyuncu",
      "score": 5,
      "comment": "Harika bir oyuncu!",
      "createdAt": "2024-06-14T00:00:00Z"
    }
  ],
  "page": 1,
  "limit": 20,
  "totalCount": 12,
  "totalPages": 1,
  "averageRating": 4.3
}
```

---

### 5.8 Notification Endpoints

#### GET /notifications

Kullanıcının bildirimlerini listeler.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/notifications` |
| **Auth** | Bearer JWT (zorunlu) |

**Query Parameters:**

| Parametre | Tip | Zorunlu | Varsayılan | Açıklama |
|-----------|-----|---------|------------|----------|
| `page` | int | Hayır | 1 | Sayfa numarası |
| `limit` | int | Hayır | 20 | Sayfa başına kayıt (max 50) |

**Response (200):**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "application_received",
      "title": "Yeni başvuru geldi!",
      "body": "Serkan Y. \"Akşam Okey Partisi\" ilanınıza başvurdu.",
      "data": { "listingId": "lst_001" },
      "read": false,
      "createdAt": "2024-06-15T14:30:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "type": "room_created",
      "title": "Maç odası hazır!",
      "body": "\"Hafta Sonu Turnuvası\" için maç odası oluşturuldu.",
      "data": { "roomId": "room_001", "listingId": "lst_002" },
      "read": false,
      "createdAt": "2024-06-15T13:00:00Z"
    }
  ],
  "unreadCount": 5,
  "page": 1,
  "limit": 20,
  "totalCount": 25,
  "totalPages": 2
}
```

---

#### POST /notifications/read

Bildirimleri okundu olarak işaretler.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/notifications/read` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "notificationIds": ["notif_001", "notif_002"]
}
```

**Response (204):** No Content

**Validation:**
- `notificationIds` boş olamaz
- Yalnızca kullanıcının kendi bildirimlerini okundu yapabilir

---

#### POST /users/me/device-token

FCM push notification token kaydı. Login sonrası ve token yenilendiğinde çağrılır.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/users/me/device-token` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "token": "fMp7B4K3R...(FCM token)...",
  "platform": "ios"
}
```

**Response (200):**
```json
{
  "message": "Token kaydedildi"
}
```

**Validation:**
- `token`: zorunlu, boş olamaz
- `platform`: zorunlu, `ios` veya `android`

**Business Logic:**
- Aynı token zaten varsa `LastUsedAt` güncellenir (duplicate oluşturulmaz)
- Kullanıcı logout olduğunda ilgili token silinir
- Geçersiz token döndüğünde (FCM `NotRegistered`) otomatik temizlenir

---

#### DELETE /users/me/device-token

Logout sırasında FCM token silme.

| Özellik | Değer |
|---------|-------|
| **Route** | `DELETE /v1/users/me/device-token` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "token": "fMp7B4K3R...(FCM token)..."
}
```

**Response (204):** No Content

---

### 5.9 Bildirim Türleri — Tetikleme Kuralları ve Data Formatları

Aşağıdaki tablo her bildirim türünün ne zaman, kime gönderileceğini ve `data` alanında hangi bilgilerin taşınacağını tanımlar. Backend'de bildirim oluşturulurken **hem veritabanına `Notification` kaydı yazılır, hem de FCM push gönderilir**.

#### `application_received` — Yeni başvuru geldi

| Alan | Değer |
|------|-------|
| **Tetikleyici** | `POST /listings/:id/apply` başarılı olduğunda |
| **Alıcı** | İlan sahibi (listing.ownerId) |
| **Title** | `"Yeni başvuru geldi!"` |
| **Body** | `"{applicantName} \"{listingTitle}\" ilanınıza başvurdu."` |
| **Data** | `{ "listingId": "{id}" }` |
| **Deep link** | Mobil: `/listings/{id}` → ilan detayı |

---

#### `application_accepted` — Başvuru kabul edildi

| Alan | Değer |
|------|-------|
| **Tetikleyici** | `POST /applications/:id/accept` başarılı olduğunda |
| **Alıcı** | Başvuru sahibi (application.applicantUserId) |
| **Title** | `"Başvurunuz kabul edildi!"` |
| **Body** | `"\"{listingTitle}\" ilanına başvurunuz kabul edildi."` |
| **Data** | `{ "listingId": "{listingId}" }` |
| **Deep link** | Mobil: `/listings/{listingId}` → ilan detayı |

---

#### `application_rejected` — Başvuru reddedildi

| Alan | Değer |
|------|-------|
| **Tetikleyici** | `POST /applications/:id/reject` veya listing full olduğunda otomatik reject |
| **Alıcı** | Başvuru sahibi (application.applicantUserId) |
| **Title** | `"Başvurunuz reddedildi"` |
| **Body** | `"\"{listingTitle}\" ilanına başvurunuz reddedildi."` |
| **Data** | `{ "listingId": "{listingId}" }` |
| **Deep link** | Mobil: `/` → ana sayfa |

---

#### `room_created` — Maç odası oluşturuldu

| Alan | Değer |
|------|-------|
| **Tetikleyici** | Listing `Full` olduğunda backend otomatik MatchRoom oluşturur |
| **Alıcı** | Tüm listing katılımcıları (ListingParticipant'lar) |
| **Title** | `"Maç odası hazır!"` |
| **Body** | `"\"{listingTitle}\" için maç odası oluşturuldu. Katılımınızı onaylayın."` |
| **Data** | `{ "roomId": "{roomId}", "listingId": "{listingId}" }` |
| **Deep link** | Mobil: `/rooms/{roomId}` → maç odası |

---

#### `attendance_reminder` — Katılım hatırlatması

| Alan | Değer |
|------|-------|
| **Tetikleyici** | Background job: `scheduledAt - 30 dakika` |
| **Alıcı** | `AttendanceStatus.Pending` olan katılımcılar |
| **Title** | `"Maçınıza az kaldı!"` |
| **Body** | `"\"{listingTitle}\" maçınıza 30 dakika kaldı. Katılımınızı onaylayın."` |
| **Data** | `{ "roomId": "{roomId}" }` |
| **Deep link** | Mobil: `/rooms/{roomId}` → maç odası |

---

#### `match_completed` — Maç tamamlandı

| Alan | Değer |
|------|-------|
| **Tetikleyici** | Background job: `scheduledAt + 2 saat` → Room status `Finished` olduğunda |
| **Alıcı** | Tüm oda katılımcıları (MatchParticipant'lar) |
| **Title** | `"Maç tamamlandı!"` |
| **Body** | `"\"{listingTitle}\" maçınız tamamlandı. Oyuncuları değerlendirebilirsiniz."` |
| **Data** | `{ "roomId": "{roomId}" }` |
| **Deep link** | Mobil: `/ratings/create` (extra ile roomId) |

---

#### `rating_received` — Yeni puan alındı

| Alan | Değer |
|------|-------|
| **Tetikleyici** | `POST /ratings` başarılı olduğunda |
| **Alıcı** | Puanlanan kullanıcı (rating.toUserId) |
| **Title** | `"Yeni değerlendirme!"` |
| **Body** | `"{fromUserName} sizi {score} yıldız ile değerlendirdi."` |
| **Data** | `{ "fromUserId": "{fromUserId}", "roomId": "{roomId}" }` |
| **Deep link** | Mobil: `/profile` → profil sayfası |

---

#### `badge_earned` — Rozet kazanıldı

| Alan | Değer |
|------|-------|
| **Tetikleyici** | Badge check: maç tamamlandığında, profil doğrulandığında (event-driven) |
| **Alıcı** | Rozet kazanan kullanıcı |
| **Title** | `"Yeni rozet kazandın!"` |
| **Body** | `"\"{badgeTitle}\" rozetini kazandınız. Tebrikler!"` |
| **Data** | `{ "badgeId": "{badgeId}" }` |
| **Deep link** | Mobil: `/profile` → profil sayfası |

---

### 5.10 FCM Push Notification Payload Formatı

Backend'den FCM'e gönderilecek payload formatı:

```json
{
  "message": {
    "token": "cihaz_fcm_token",
    "notification": {
      "title": "Başvurunuz kabul edildi!",
      "body": "\"Akşam Okey Partisi\" ilanına başvurunuz kabul edildi."
    },
    "data": {
      "type": "application_accepted",
      "listingId": "lst_001",
      "click_action": "FLUTTER_NOTIFICATION_CLICK"
    },
    "android": {
      "priority": "high",
      "notification": {
        "channel_id": "okey_match_notifications",
        "sound": "default"
      }
    },
    "apns": {
      "payload": {
        "aps": {
          "badge": 5,
          "sound": "default"
        }
      }
    }
  }
}
```

**Önemli Notlar:**
- `notification` bloğu: Uygulama kapalıyken sistem tarafından gösterilir
- `data` bloğu: Uygulama açıkken Flutter tarafında işlenir, deep link yönlendirmesi için kullanılır
- `data.type`: Bildirim türü (enum string, camelCase: `applicationAccepted`)
- iOS badge sayısı: Backend'de kullanıcının toplam `unreadCount` değeri hesaplanarak gönderilir
- Birden fazla cihazı olan kullanıcılar için tüm `DeviceToken`'lara gönderilir

---

### 5.11 Subscription & Boost Endpoints

#### GET /subscriptions/plans

Mevcut abonelik planlarını listeler. Mobil uygulama bu endpoint'ten planları çekerek UI'da gösterir. Planlar backend'den yönetilir — fiyat, özellik, boost kredisi gibi tüm bilgiler bu endpoint'ten gelir.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/subscriptions/plans` |
| **Auth** | Gerekmez (public) |
| **Cache** | 1 saat (planlar nadiren değişir) |

**Response (200):**
```json
{
  "plans": [
    {
      "id": "plan_daily_001",
      "type": "daily",
      "name": "Günlük Geçiş",
      "description": "24 saatlik premium erişim",
      "price": 14.99,
      "currency": "TRY",
      "durationDays": 1,
      "savingsPercent": null,
      "boostCredits": 0,
      "features": {
        "unlimitedListings": true,
        "unlimitedApplications": true,
        "advancedFilters": true,
        "viewApplicantDetails": true,
        "proBadge": false
      },
      "sortOrder": 0
    },
    {
      "id": "plan_monthly_001",
      "type": "monthly",
      "name": "Aylık Plan",
      "description": "Aylık faturalandırma",
      "price": 79.99,
      "currency": "TRY",
      "durationDays": 30,
      "savingsPercent": null,
      "boostCredits": 1,
      "features": {
        "unlimitedListings": true,
        "unlimitedApplications": true,
        "advancedFilters": true,
        "viewApplicantDetails": true,
        "proBadge": true
      },
      "sortOrder": 1
    },
    {
      "id": "plan_yearly_001",
      "type": "yearly",
      "name": "Yıllık Plan",
      "description": "₺599,99 yıllık faturalandırma",
      "price": 599.99,
      "currency": "TRY",
      "durationDays": 365,
      "savingsPercent": 37,
      "boostCredits": 12,
      "features": {
        "unlimitedListings": true,
        "unlimitedApplications": true,
        "advancedFilters": true,
        "viewApplicantDetails": true,
        "proBadge": true
      },
      "sortOrder": 2
    }
  ]
}
```

> **Not:** Yanıtta yalnızca `IsActive == true` olan planlar dönülür. `sortOrder` alanı UI'da tab sıralamasını belirler. `features` objesi plan kapsamındaki özellikleri boolean olarak tanımlar.

---

#### GET /subscriptions/me

Mevcut kullanıcının aktif aboneliğini döner.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/subscriptions/me` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (200) — Aktif abonelik varsa:**
```json
{
  "id": "sub_001",
  "plan": {
    "id": "plan_monthly_001",
    "type": "monthly",
    "name": "Aylık Plan",
    "price": 79.99,
    "currency": "TRY",
    "durationDays": 30,
    "boostCredits": 1,
    "features": {
      "unlimitedListings": true,
      "unlimitedApplications": true,
      "advancedFilters": true,
      "viewApplicantDetails": true,
      "proBadge": true
    }
  },
  "status": "active",
  "startedAt": "2024-06-01T00:00:00Z",
  "expiresAt": "2024-07-01T00:00:00Z",
  "boostCreditsRemaining": 1,
  "isActive": true
}
```

**Response (200) — Abonelik yoksa:**
```json
{
  "id": null,
  "plan": null,
  "status": null,
  "startedAt": null,
  "expiresAt": null,
  "boostCreditsRemaining": 0,
  "isActive": false
}
```

> **Not:** `isActive` alanı backend tarafında hesaplanır: `Status == Active && ExpiresAt > DateTime.UtcNow`. Mobil taraf bu alana güvenerek abonelik durumunu belirler.

---

#### POST /subscriptions

Yeni abonelik oluşturur (ödeme sonrası).

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/subscriptions` |
| **Auth** | Bearer JWT (zorunlu) |

**Request:**
```json
{
  "planId": "plan_monthly_001",
  "paymentProvider": "apple",
  "paymentTransactionId": "GPA.3374-7238-2091-32451"
}
```

**Response (201):**
```json
{
  "id": "sub_new_001",
  "plan": {
    "id": "plan_monthly_001",
    "type": "monthly",
    "name": "Aylık Plan",
    "price": 79.99,
    "currency": "TRY",
    "durationDays": 30,
    "boostCredits": 1,
    "features": {
      "unlimitedListings": true,
      "unlimitedApplications": true,
      "advancedFilters": true,
      "viewApplicantDetails": true,
      "proBadge": true
    }
  },
  "status": "active",
  "startedAt": "2024-06-15T14:00:00Z",
  "expiresAt": "2024-07-15T14:00:00Z",
  "boostCreditsRemaining": 1,
  "isActive": true
}
```

**Validation:**
- `planId`: Geçerli ve aktif bir plan olmalı
- `paymentProvider`: `apple` | `google` | `stripe`
- `paymentTransactionId`: Zorunlu, boş olamaz

**Business Logic:**
1. Kullanıcının zaten aktif aboneliği varsa `409 Conflict` döner
2. Plan `IsActive == true` kontrolü
3. Ödeme doğrulama (Apple/Google receipt validation — ayrı servis)
4. `Subscription` kaydı oluşturulur
5. `BoostCreditsRemaining` plan tanımından alınır
6. `User` tablosunda PRO rozeti güncellenir (plan `ProBadge == true` ise)

**Hata Senaryoları:**
- `400` — Geçersiz planId veya paymentProvider
- `402` — Ödeme doğrulanamadı
- `409` — Zaten aktif abonelik var

---

#### POST /subscriptions/me/cancel

Aktif aboneliği iptal eder. Dönem sonuna kadar erişim devam eder.

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/subscriptions/me/cancel` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (200):**
```json
{
  "id": "sub_001",
  "status": "cancelled",
  "cancelledAt": "2024-06-20T14:00:00Z",
  "expiresAt": "2024-07-01T00:00:00Z",
  "message": "Aboneliğiniz dönem sonuna kadar aktif kalacaktır."
}
```

**Business Logic:**
- `Status` → `Cancelled`
- `CancelledAt` kaydedilir
- Erişim `ExpiresAt` tarihine kadar devam eder
- Apple/Google tarafında da iptal tetiklenir (webhook veya API)

**Hata Senaryoları:**
- `404` — Aktif abonelik bulunamadı

---

#### POST /listings/:id/boost

İlanı öne çıkarır (boost credit kullanarak).

| Özellik | Değer |
|---------|-------|
| **Route** | `POST /v1/listings/{id}/boost` |
| **Auth** | Bearer JWT (zorunlu, listing owner check) |

**Response (200):**
```json
{
  "listingId": "lst_001",
  "boostedAt": "2024-06-15T14:00:00Z",
  "expiresAt": "2024-06-16T14:00:00Z",
  "boostCreditsRemaining": 0,
  "message": "İlanınız 24 saat boyunca öne çıkarıldı."
}
```

**Validation:**
- İlan kullanıcıya ait olmalı
- İlan `Open` veya `Pending` durumunda olmalı
- İlan zaten aktif boost'ta olmamalı

**Business Logic:**
1. Kullanıcının aktif aboneliği ve `BoostCreditsRemaining > 0` kontrolü
2. `ListingBoost` kaydı oluşturulur (24 saat süreli)
3. `Subscription.BoostCreditsRemaining` 1 azaltılır
4. `Listing.Visibility` → `Boosted`
5. 24 saat sonra background job ile `Listing.Visibility` → `Normal` (BoostExpirationJob)

**Hata Senaryoları:**
- `403` — İlan sahibi değil
- `400` — İlan uygun durumda değil / zaten boost'ta
- `402` — Boost kredisi yok (abonelik yok veya kalan hak 0)

---

#### GET /subscriptions/me/boost-history

Kullanıcının boost geçmişini listeler.

| Özellik | Değer |
|---------|-------|
| **Route** | `GET /v1/subscriptions/me/boost-history` |
| **Auth** | Bearer JWT (zorunlu) |

**Response (200):**
```json
{
  "items": [
    {
      "id": "boost_001",
      "listingId": "lst_001",
      "listingTitle": "Akşam Okey Partisi",
      "boostedAt": "2024-06-15T14:00:00Z",
      "expiresAt": "2024-06-16T14:00:00Z",
      "isActive": false
    }
  ],
  "boostCreditsRemaining": 1
}
```

---

## 6. Business Logic Rules


### 6.1 Auth Kuralları

| Kural | Detay |
|-------|-------|
| OTP süresi | 5 dakika |
| OTP deneme hakkı | 5 başarısız deneme sonrası 15 dakika bekleme |
| OTP formatı | 6 haneli sayısal |
| Rate limit | Aynı numara için 60 saniyede 1 istek |
| Access token süresi | 1 saat |
| Refresh token süresi | 30 gün |
| Otomatik kayıt | İlk doğrulama ile kullanıcı oluşturulur |

### 6.2 Listing Kuralları

| Kural | Detay |
|-------|-------|
| Minimum tarih | Şu andan en az 1 saat sonra |
| Maksimum tarih | Şu andan en fazla 90 gün sonra |
| `playerNeeded` aralığı | 1–3 (toplam 4 oyuncu - owner) |
| Yaş aralığı | minAge: 16–100, maxAge: minAge'den büyük |
| Geçmiş tarihli ilanlar | Otomatik olarak `Completed` veya `Cancelled` durumuna geçer |

**Status Geçişleri:**

```
                 ┌─────────────┐
                 │    Open     │
                 └──────┬──────┘
                        │
              ┌─────────┼─────────┐
              ▼                   ▼
       ┌──────────┐        ┌───────────┐
       │ Pending  │        │ Cancelled │
       └────┬─────┘        └───────────┘
            │
            ▼
       ┌──────────┐
       │   Full   │
       └────┬─────┘
            │
            ▼
       ┌───────────┐
       │ Completed │
       └───────────┘
```

- `Open` → `Pending`: Bazı başvurular kabul edildi ama tüm slotlar dolmadı
- `Open` / `Pending` → `Full`: Tüm slotlar doldu
- `Full` → `Completed`: Maç tamamlandı (MatchRoom.Status = Finished)
- `Open` / `Pending` → `Cancelled`: İlan sahibi iptal etti veya tarih geçti

### 6.3 Application Kuralları

| Kural | Detay |
|-------|-------|
| Kendi ilanına başvuru | Yasak |
| Tekrar başvuru | Aynı ilana aktif (Pending) başvurusu olan kullanıcı tekrar başvuramaz |
| Grup başvurusu | `joinedAsGroupCount` kadar slot kalan olmalı |
| Kabul etkisi | Başvuran `ListingParticipant` olarak eklenir, `playerNeeded` azaltılır |
| Son slot dolunca | Kalan Pending başvurular otomatik `Rejected` |

### 6.4 Match Room Kuralları

| Kural | Detay |
|-------|-------|
| Oluşturma zamanı | Listing `Full` olduğunda otomatik |
| Onay süresi | `scheduledAt` - 30 dakika |
| Tüm oyuncular onaylayınca | `Waiting` → `Active` |
| No-show durumu | Oyuncunun `CancellationRate` artar |
| Maç tamamlanma | `scheduledAt` + 2 saat sonra otomatik `Finished` (background job) |

### 6.5 Rating Kuralları

| Kural | Detay |
|-------|-------|
| Puan aralığı | 1–5 (integer) |
| Puan verme koşulu | Room `Finished` durumunda olmalı |
| Kendine puan | Yasak |
| Tekrar puan | Aynı oda + aynı kullanıcıya tekrar puan verilemez |
| Rating hesaplama | Tüm alınan puanların aritmetik ortalaması |
| Puan verme süresi | Room `Finished` olduktan sonra 48 saat içinde |

### 6.6 Güven Skoru (Trust Score) Hesaplama

```
TrustScore = (OnTimeRate * 0.4) + (NormalizedRating * 0.35) + (InverseCancellationRate * 0.25)
```

| Bileşen | Hesaplama |
|---------|-----------|
| `OnTimeRate` | (joined olarak katıldığı maç / toplam davet edildiği maç) * 100 |
| `NormalizedRating` | (avgRating / 5.0) * 100 |
| `InverseCancellationRate` | 100 - cancellationRate |
| `CancellationRate` | (noShow sayısı / toplam davet) * 100 |

### 6.7 Rozet Kazanım Kuralları

| Rozet | Code | Koşul |
|-------|------|-------|
| 10 Maç Tamamladı | `10_matches` | `totalMatches >= 10` |
| 50 Maç Ustası | `50_matches` | `totalMatches >= 50` |
| Doğrulanmış Profil | `verified_profile` | `verified == true` |
| Güvenilir Oyuncu | `trusted_player` | `trustScore >= 85` |
| Dakik Katılımcı | `punctual` | `onTimeRate >= 95` |
| Turnuva Şampiyonu | `tournament_champion` | Turnuva sistemi eklendiğinde |

Rozetler her maç sonrası ve profil değişikliğinde kontrol edilir (background job veya event-driven).

### 6.8 Yetki Kontrolleri

| İşlem | Yetki |
|-------|-------|
| İlan oluşturma | Authenticated + profileCompleted |
| İlan güncelleme/silme | İlan sahibi |
| Başvuru kabul/red | İlan sahibi |
| Başvuru iptal | Başvuru sahibi |
| Katılım onayı | Oda katılımcısı |
| Puan verme | Oda katılımcısı (tamamlanmış oda) |

### 6.9 Bildirim Kuralları

| Kural | Detay |
|-------|-------|
| Bildirim oluşturma | Her bildirim hem DB'ye yazılır hem FCM push gönderilir |
| Çoklu cihaz | Kullanıcının tüm `DeviceToken`'larına push gönderilir |
| Okundu işaretleme | Yalnızca kendi bildirimlerini işaretleyebilir |
| Eski bildirim temizliği | 90 günden eski okunmuş bildirimler background job ile silinir |
| FCM token temizliği | `NotRegistered` dönen tokenlar otomatik silinir |
| Toplu reject bildirimi | Listing `Full` olduğunda kalan `Pending` başvurular toplu reject edilir, her birine ayrı bildirim gider |
| Hatırlatma bildirimi | Maçtan 30dk önce yalnızca `AttendanceStatus.Pending` olanlara gönderilir |
| Maç tamamlanma bildirimi | Room `Finished` olduğunda tüm katılımcılara gönderilir |
| Rozet bildirimi | Rozet ilk kez kazanıldığında bir kez gönderilir |

**Bildirim Tetikleme Noktaları (Event-Driven):**

```
POST /listings/:id/apply           → application_received  → ilan sahibine
POST /applications/:id/accept      → application_accepted  → başvuru sahibine
                                   → application_rejected  → (listing full ise) diğer pending başvurulara
                                   → room_created          → (listing full ise) tüm katılımcılara
POST /applications/:id/reject      → application_rejected  → başvuru sahibine
POST /ratings                      → rating_received       → puanlanan kullanıcıya
MatchCompletionJob                 → match_completed       → tüm katılımcılara
AttendanceReminderJob              → attendance_reminder   → pending katılımcılara
BadgeCheckJob                      → badge_earned          → rozet kazanan kullanıcıya
SubscriptionExpirationJob          → subscription_expiring → 3 gün kala abonelik sahibine
SubscriptionExpirationJob          → subscription_expired  → süresi dolan abonelik sahibine
```

### 6.10 Abonelik Kuralları

| Kural | Detay |
|-------|-------|
| Plan yönetimi | Planlar backend'den yönetilir, mobil uygulama `GET /subscriptions/plans` ile çeker |
| Aktif abonelik kontrolü | `Status == Active && ExpiresAt > DateTime.UtcNow` |
| Çoklu abonelik | Kullanıcı aynı anda yalnızca 1 aktif aboneliğe sahip olabilir |
| İptal sonrası erişim | Dönem sonuna kadar tüm özellikler aktif kalır |
| Süre dolumu | Background job ile `ExpiresAt` geçmiş abonelikler `Expired` yapılır |
| Yenileme | Yeni abonelik yalnızca aktif abonelik yoksa oluşturulabilir |
| Günlük plan | 24 saat süreli, otomatik yenileme yok |
| Aylık plan | 30 gün süreli, aylık 1 boost kredisi |
| Yıllık plan | 365 gün süreli, yılda 12 boost kredisi (toplam) |
| Ödeme doğrulama | Apple App Store / Google Play receipt validation zorunlu |
| Hatırlatma | Abonelik bitimine 3 gün kala bildirim gönderilir |
| Free tier limitleri | Haftada 1 ilan, haftada 2 başvuru (backend'den kontrol edilir) |

### 6.11 İlan Boostlama Kuralları

| Kural | Detay |
|-------|-------|
| Boost süresi | 24 saat |
| Boost kredisi | Plandan gelir (günlük: 0, aylık: 1, yıllık: 12) |
| Boost etkisi | `Listing.Visibility = Boosted` → sıralamada öne alınır |
| Tekrar boost | Aynı ilan aktif boost süresindeyken tekrar boost edilemez |
| İlan durumu | Yalnızca `Open` veya `Pending` durumdaki ilanlar boost edilebilir |
| Süre bitimi | `BoostExpirationJob` ile otomatik `Normal` yapılır |
| Kredi yönetimi | Boost kullanıldığında `Subscription.BoostCreditsRemaining` azaltılır |
| Abonelik iptali | İptal sonrası kalan boost hakları dönem sonuna kadar kullanılabilir |

---

## 7. Data Flow

### 7.1 Auth Akışı

```
PhoneEntryPage                API                    Database
     │                         │                        │
     │──POST /auth/send-otp──►│                        │
     │                         │──Create OtpRecord────►│
     │                         │──Send SMS (provider)──│
     │◄────200 OK─────────────│                        │
     │                         │                        │
OtpVerifyPage                  │                        │
     │                         │                        │
     │──POST /auth/verify-otp─►│                        │
     │                         │──Validate OtpRecord──►│
     │                         │──Find/Create User────►│
     │                         │──Generate JWT─────────│
     │                         │──Save RefreshToken───►│
     │◄────200 {tokens}───────│                        │
     │                         │                        │
     │  [isNewUser?] ──yes──► OnboardingWizardPage     │
     │                   no──► ListingsPage             │
```

### 7.2 Listing Oluşturma → Maç Tamamlama Akışı

```
CreateListingPage              API                    Database
     │                         │                        │
     │──POST /listings────────►│                        │
     │                         │──Create Listing───────►│
     │                         │──Add Owner as ────────►│
     │                         │  ListingParticipant    │
     │◄────201 Created────────│                        │
     │                         │                        │

ListingDetailPage              │                        │
     │                         │                        │
     │──POST /listings/:id/───►│                        │
     │  apply                  │──Create Application──►│
     │◄────201 Created────────│──Notify Owner──────────│
     │                         │                        │

ApplicationsPage               │                        │
     │                         │                        │
     │──POST /applications/───►│                        │
     │  :id/accept             │──Update App Status───►│
     │                         │──Add Participant─────►│
     │                         │──Check if Full────────│
     │                         │  [Full?]               │
     │                         │   yes──Create Room───►│
     │                         │   yes──Reject Others─►│
     │                         │   yes──Notify All─────│
     │◄────200 OK─────────────│                        │

MatchRoomPage                  │                        │
     │                         │                        │
     │──POST /rooms/:id/──────►│                        │
     │  confirm-attendance     │──Update Status────────►│
     │                         │  [All joined?]         │
     │                         │   yes──Room → Active──►│
     │◄────200 OK─────────────│                        │
     │                         │                        │
     │         [scheduledAt + 2h geçince]               │
     │                         │──Room → Finished─────►│
     │                         │──Notify: Rate peers───│

CreateRatingPage               │                        │
     │                         │                        │
     │──POST /ratings─────────►│                        │
     │                         │──Create Rating────────►│
     │                         │──Recalc User Rating──►│
     │                         │──Recalc TrustScore───►│
     │                         │──Check Badges─────────│
     │◄────201 Created────────│                        │
```

### 7.3 Profil Güncelleme Akışı

```
AccountInfoPage / OnboardingWizardPage
     │
     │──POST /files/upload──► API ──► Blob Storage ──► URL döner
     │◄────200 {url}────────│
     │
     │──PUT /users/me───────► API
     │   {fullName, city,    │
     │    profilePhotoUrl,   │──Update User─────► Database
     │    age, ...}          │
     │                       │──If onboarding:
     │                       │  profileCompleted=true
     │                       │──Check badges
     │◄────200 UserResponse──│
```

### 7.4 Bildirim Akışı

```
                                   API                     Database / FCM
                                    │                          │
  [Event tetiklenir]                │                          │
  (başvuru kabul, maç tamamlandı,   │                          │
   puan verildi, rozet kazanıldı)   │                          │
                                    │                          │
                                    │──1. Notification kayıt──►│ (Notification tablosuna INSERT)
                                    │                          │
                                    │──2. DeviceToken sorgula─►│ (userId'ye ait tokenlar)
                                    │                          │
                                    │──3. FCM Push gönder─────►│ Firebase Cloud Messaging
                                    │   {notification + data}  │
                                    │                          │
                                    │   [Token geçersizse]     │
                                    │──4. Token sil───────────►│ (DeviceToken DELETE)
                                    │                          │

Flutter App                        API
     │                              │
     │──GET /notifications─────────►│ (sayfalı liste + unreadCount)
     │◄────200 {items, unread}─────│
     │                              │
     │──POST /notifications/read──►│ (okundu işaretleme)
     │◄────204────────────────────│
     │                              │
     │──POST /users/me/device-token►│ (FCM token kayıt — login sonrası)
     │◄────200 OK─────────────────│
```

---

## 8. Infrastructure Notes

### 8.1 Proje Yapısı (Clean Architecture)

```
OkeyMatch.sln
├── src/
│   ├── OkeyMatch.Api/                    # ASP.NET Core Web API
│   │   ├── Controllers/
│   │   │   ├── AuthController.cs
│   │   │   ├── UsersController.cs
│   │   │   ├── ListingsController.cs
│   │   │   ├── ApplicationsController.cs
│   │   │   ├── RoomsController.cs
│   │   │   ├── RatingsController.cs
│   │   │   ├── FilesController.cs
│   │   │   ├── NotificationsController.cs
│   │   │   └── SubscriptionsController.cs
│   │   ├── Middleware/
│   │   │   ├── ExceptionHandlingMiddleware.cs
│   │   │   └── RequestLoggingMiddleware.cs
│   │   ├── Filters/
│   │   │   └── ValidationFilter.cs
│   │   └── Program.cs
│   │
│   ├── OkeyMatch.Application/           # Use cases, DTOs, interfaces
│   │   ├── Common/
│   │   │   ├── Interfaces/
│   │   │   ├── Models/
│   │   │   │   └── PaginatedResult.cs
│   │   │   └── Behaviors/
│   │   │       └── ValidationBehavior.cs
│   │   ├── Auth/
│   │   │   ├── Commands/
│   │   │   │   ├── SendOtpCommand.cs
│   │   │   │   ├── VerifyOtpCommand.cs
│   │   │   │   └── RefreshTokenCommand.cs
│   │   │   └── DTOs/
│   │   ├── Users/
│   │   │   ├── Commands/
│   │   │   ├── Queries/
│   │   │   └── DTOs/
│   │   ├── Listings/
│   │   ├── Applications/
│   │   ├── Rooms/
│   │   ├── Ratings/
│   │   ├── Notifications/
│   │   └── Subscriptions/
│   │       ├── Commands/
│   │       │   ├── CreateSubscriptionCommand.cs
│   │       │   ├── CancelSubscriptionCommand.cs
│   │       │   └── BoostListingCommand.cs
│   │       ├── Queries/
│   │       │   ├── GetPlansQuery.cs
│   │       │   ├── GetMySubscriptionQuery.cs
│   │       │   └── GetBoostHistoryQuery.cs
│   │       └── DTOs/
│   │           ├── SubscriptionPlanDto.cs
│   │           ├── SubscriptionPlanFeaturesDto.cs
│   │           ├── SubscriptionDto.cs
│   │           ├── CreateSubscriptionRequest.cs
│   │           ├── CancelSubscriptionResponse.cs
│   │           ├── BoostListingResponse.cs
│   │           └── BoostHistoryDto.cs
│   │
│   ├── OkeyMatch.Domain/                # Entities, Enums, Value Objects
│   │   ├── Entities/
│   │   ├── Enums/
│   │   ├── Events/
│   │   └── Exceptions/
│   │
│   └── OkeyMatch.Infrastructure/        # EF Core, External services
│       ├── Persistence/
│       │   ├── ApplicationDbContext.cs
│       │   ├── Configurations/           # Fluent API entity configs
│       │   ├── Migrations/
│       │   └── Repositories/
│       ├── Services/
│       │   ├── JwtService.cs
│       │   ├── OtpService.cs
│       │   ├── SmsService.cs
│       │   ├── EmailService.cs
│       │   ├── BlobStorageService.cs
│       │   ├── TrustScoreService.cs
│       │   ├── BadgeService.cs
│       │   ├── NotificationService.cs
│       │   ├── FcmPushService.cs
│       │   ├── SubscriptionService.cs
│       │   └── PaymentValidationService.cs
│       └── BackgroundJobs/
│           ├── MatchCompletionJob.cs
│           ├── ListingExpirationJob.cs
│           ├── BadgeCheckJob.cs
│           ├── AttendanceReminderJob.cs
│           ├── NotificationCleanupJob.cs
│           ├── SubscriptionExpirationJob.cs
│           └── BoostExpirationJob.cs
│
└── tests/
    ├── OkeyMatch.UnitTests/
    ├── OkeyMatch.IntegrationTests/
    └── OkeyMatch.Api.Tests/
```

### 8.2 Logging

- **Yapısal loglama**: Serilog ile (console + file + seq/elk)
- **Correlation ID**: Her request için unique ID (middleware ile)
- **Request/Response logging**: API interceptor seviyesinde (hassas veriler maskelenir)
- **Log seviyeleri**: Information (başarılı işlemler), Warning (iş kuralı ihlali), Error (exception)

### 8.3 Exception Handling

Merkezi exception handling middleware ile:

```json
{
  "type": "ValidationError",
  "title": "Doğrulama hatası",
  "status": 400,
  "errors": {
    "phone": ["Geçerli bir telefon numarası girin"]
  },
  "traceId": "00-abc123..."
}
```

| Exception Tipi | HTTP Status | Açıklama |
|---------------|-------------|----------|
| `ValidationException` | 400 | Girdi doğrulama hatası |
| `UnauthorizedException` | 401 | Token geçersiz/eksik |
| `ForbiddenException` | 403 | Yetki yetersiz |
| `NotFoundException` | 404 | Kayıt bulunamadı |
| `ConflictException` | 409 | Çakışma (zaten var) |
| `TooManyRequestsException` | 429 | Rate limit aşıldı |
| `Exception` (unhandled) | 500 | Sunucu hatası |

### 8.4 Validation

- **FluentValidation** kütüphanesi ile her Command/Query için validator
- MediatR pipeline behavior olarak validation otomatik çalıştırılır
- Request DTO'larda `[Required]`, `[MaxLength]` gibi attribute'lar da kullanılabilir

### 8.5 Authentication & Authorization

- **JWT Bearer** authentication (ASP.NET Core Identity opsiyonel)
- Access token: 1 saat ömürlü, HMAC-SHA256 imzalı
- Refresh token: 30 gün ömürlü, veritabanında saklanır
- Token claims: `sub` (userId), `phone`, `email`, `profile_completed`
- Custom authorization policy'ler: `ProfileCompleted`, `ListingOwner`, `RoomParticipant`

### 8.6 Caching

| Veri | Strateji | TTL |
|------|----------|-----|
| Listing listesi | Distributed cache (Redis) | 2 dakika |
| User profili | In-memory cache | 5 dakika (kendi profil değişince invalidate) |
| Badge tanımları | In-memory cache | 1 saat (nadiren değişir) |
| OTP rate limit | Distributed cache (Redis) | 60 saniye |

### 8.7 File Upload

- **Azure Blob Storage** veya **AWS S3** ile dosya saklama
- Profil fotoğrafları: `photos/{userId}-profile-{timestamp}.jpg`
- Selfie: `photos/{userId}-selfie-{timestamp}.jpg`
- CDN ile serve edilmesi önerilir
- Maksimum boyut: 5 MB
- Desteklenen formatlar: JPEG, PNG, WebP
- Yükleme öncesi image resize (max 1024x1024) — server-side veya client-side (uygulama zaten 1024x1024 yapıyor)

### 8.8 SMS & Email Servisleri

| Servis | Amaç | Önerilen Provider |
|--------|-------|-------------------|
| SMS | OTP gönderimi | Twilio, Vonage veya yerli: Netgsm, İleti Merkezi |
| Email | Email OTP, bildirim | SendGrid, AWS SES |
| Push Notification | Mobil bildirim | Firebase Cloud Messaging (FCM) |

### 8.9 Background Jobs

**Hangfire** veya **Quartz.NET** ile:

| Job | Sıklık | Açıklama |
|-----|--------|----------|
| `MatchCompletionJob` | Her 15 dakika | `scheduledAt + 2 saat` geçmiş Active room'ları `Finished` yapar |
| `ListingExpirationJob` | Her 30 dakika | `dateTime` geçmiş Open/Pending listing'leri `Cancelled` yapar |
| `BadgeCheckJob` | Her maç tamamlandığında (event-driven) | Kullanıcı rozet koşullarını kontrol eder |
| `TrustScoreRecalcJob` | Her puan/katılım sonrası (event-driven) | Güven skoru yeniden hesaplar |
| `AttendanceReminderJob` | Her 5 dakika | `scheduledAt - 30dk` olan room'lardaki pending katılımcılara bildirim |
| `NotificationCleanupJob` | Günlük | 90 günden eski okunmuş bildirimleri temizler |
| `OtpCleanupJob` | Her saat | Süresi dolmuş OTP kayıtlarını temizler |
| `SubscriptionExpirationJob` | Her 30 dakika | `ExpiresAt` geçmiş Active abonelikleri `Expired` yapar, bildirim gönderir. Ayrıca 3 gün kala uyarı bildirimi gönderir |
| `BoostExpirationJob` | Her 15 dakika | `ExpiresAt` geçmiş ListingBoost kayıtlarını bulur, `Listing.Visibility` → `Normal` yapar |

### 8.10 Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `POST /auth/send-otp` | Aynı telefon: 1/60s, Aynı IP: 10/dakika |
| `POST /auth/verify-otp` | Aynı telefon: 5 deneme/OTP |
| Genel API | 100 istek/dakika/kullanıcı |
| `POST /files/upload` | 10 istek/dakika/kullanıcı |

---

## 9. Suggested Development Order

### Faz 1: Temel Altyapı (Hafta 1-2)

```
1. Solution oluşturma (Clean Architecture katmanları)
2. Domain entity'leri ve enum'lar
3. EF Core DbContext + entity configurations
4. PostgreSQL migration'ları
5. Global exception handling middleware
6. JWT authentication altyapısı
7. Validation pipeline (FluentValidation + MediatR)
8. Base repository pattern
9. Logging altyapısı (Serilog)
```

> **Neden ilk?** Tüm diğer modüller bu altyapıya bağımlıdır.

### Faz 2: Auth Modülü (Hafta 2-3)

```
1. OtpRecord entity + repository
2. OTP gönderim servisi (SMS provider entegrasyonu)
3. POST /auth/send-otp
4. POST /auth/verify-otp (user auto-create dahil)
5. JWT token servisi (access + refresh)
6. POST /auth/refresh
7. Rate limiting middleware
```

> **Neden ikinci?** Auth olmadan diğer hiçbir endpoint çalışamaz.

### Faz 3: User / Profile Modülü (Hafta 3-4)

```
1. User entity + repository
2. GET /users/me
3. PUT /users/me (onboarding dahil)
4. POST /files/upload (blob storage)
5. Email OTP (send + verify)
6. GET /users/:id (public profil)
7. DELETE /users/me
```

> **Neden üçüncü?** Listing oluşturma `profileCompleted` gerektirir. Owner bilgileri listing response'larında kullanılır.

### Faz 4: Listing Modülü (Hafta 4-5)

```
1. Listing + ListingParticipant entity + repository
2. POST /listings
3. GET /listings (filtreleme + pagination + spatial query)
4. GET /listings/:id
5. PUT /listings/:id
6. DELETE /listings/:id
7. PATCH /listings/:id/cancel
8. Listing expiration background job
```

> **Neden dördüncü?** Application modülü listing'e bağımlıdır.

### Faz 5: Application Modülü (Hafta 5-6)

```
1. Application entity + repository
2. POST /listings/:id/apply
3. GET /listings/:id/applications
4. POST /applications/:id/accept (participant ekleme + auto-full logic)
5. POST /applications/:id/reject
6. DELETE /applications/:id
7. MatchRoom otomatik oluşturma (listing full olduğunda)
```

### Faz 6: Match Room Modülü (Hafta 6-7)

```
1. MatchRoom + MatchParticipant entity + repository
2. GET /rooms/:id
3. POST /rooms/:id/confirm-attendance
4. Room status yönetimi
5. MatchCompletion background job
```

### Faz 7: Rating & Trust Score (Hafta 7-8)

```
1. Rating entity + repository
2. POST /ratings
3. GET /users/:id/ratings
4. Trust score hesaplama servisi
5. User rating aggregation
6. Badge entity + rozet kontrol servisi
7. Badge check job (event-driven)
```

### Faz 8: Bildirim Sistemi (Hafta 8-9)

```
1. Notification + DeviceToken entity + repository + migration
2. GET /notifications (pagination + unreadCount)
3. POST /notifications/read (toplu okundu işaretleme)
4. POST /users/me/device-token (FCM token kayıt)
5. DELETE /users/me/device-token (logout token silme)
6. NotificationService: bildirim oluşturma + DB kayıt
7. FcmPushService: Firebase Admin SDK entegrasyonu
8. Event-driven bildirim tetikleme (tüm tetikleme noktaları — bkz. Section 6.9)
9. AttendanceReminderJob: maçtan 30dk önce hatırlatma
10. NotificationCleanupJob: 90 gün sonra eski bildirimleri temizle
```

### Faz 9: Subscription & Boost Modülü (Hafta 9-10)

```
1. SubscriptionPlan + Subscription + ListingBoost entity + repository + migration
2. SubscriptionPlan seed data (Günlük, Aylık, Yıllık planlar)
3. GET /subscriptions/plans (public, cached)
4. POST /subscriptions (ödeme sonrası abonelik oluşturma)
5. GET /subscriptions/me (mevcut abonelik sorgulama)
6. POST /subscriptions/me/cancel (abonelik iptal)
7. POST /listings/:id/boost (ilan öne çıkarma)
8. GET /subscriptions/me/boost-history
9. PaymentValidationService (Apple/Google receipt validation)
10. SubscriptionExpirationJob (süre dolan abonelikleri expire etme + bildirim)
11. BoostExpirationJob (süre dolan boost'ları normal'e çevirme)
12. Free tier kontrolleri (haftalık ilan/başvuru limitleri — middleware veya service)
```

> **Neden bu sırada?** Abonelik sistemi listing (boost) ve user (erişim kontrolü) modüllerine bağımlıdır, ancak bildirim sistemi entegrasyonu da gerektirir.

### Faz 10: Son İyileştirmeler (Hafta 10-11)

```
1. Caching (Redis)
2. Performance optimizasyonu
3. API documentation (Swagger/OpenAPI)
```

---

## 10. Final Notes for Backend Developer

### 10.1 Mimari Kararlar

- **MediatR** kullanılmalı (CQRS pattern): Command/Query ayrımı ile kodun test edilebilirliği ve bakımı kolaylaşır
- **Repository pattern** + **Unit of Work**: EF Core'un DbContext'i zaten UoW sağlar; generic repository yerine feature-specific repository'ler tercih edilmeli
- **Domain Events**: Listing `Full` olduğunda, puan verildiğinde vb. olaylarda event-driven mimari kullanılmalı

### 10.2 Mobil Uygulama ile Birebir Uyum İçin Kritik Notlar

1. **Enum string serialization**: Mobil uygulama enum'ları `camelCase` string olarak kullanıyor (`beginner`, `mid`, `advanced`). Backend JSON serialization'da `JsonStringEnumConverter` ile `camelCase` format kullanılmalı.

2. **DateTime formatı**: UTC olarak saklanmalı, ISO 8601 formatında dönülmeli (`2024-06-15T19:00:00Z`).

3. **Null handling**: Mobil tarafta nullable alanlar var (`email`, `nickname`, `profilePhoto` vb.). Backend response'larda `null` değerler JSON'da korunmalı, empty string olarak dönülmemeli.

4. **API endpoint'leri sabit**: `lib/core/constants/api_endpoints.dart` dosyasında tanımlı endpoint path'leri backend ile birebir eşleşmeli. Base URL: `https://api.okeymatch.com/v1`

5. **Pagination response formatı**: Mobil tarafta `page` ve `limit` parametreleri kullanılıyor. Response'da `totalCount` ve `totalPages` dönülmeli.

6. **Error response tutarlılığı**: Mobil tarafta error mesajı `message` field'ından okunuyor. Tüm error response'larda tutarlı format kullanılmalı.

7. **Owner bilgileri listing response'unda**: `ListingEntity`'deki `ownerName`, `ownerRating`, `ownerTotalMatches`, `ownerVerified`, `ownerTrustScore` alanları listing response'unda denormalize olarak dönülmeli (join ile).

8. **Participant listesi listing response'unda**: Her listing response'unda `participants` array'i dönülmeli (isOwner, name, photoUrl dahil).

### 10.3 Static Veri Kullanımından Kaçınılması

- **İlçe listesi**: `CreateListingPage`'de İstanbul ilçeleri hardcoded. Backend'de şehir/ilçe tablosu veya en azından validation yapılmalı. İlk etapta sabit liste kabul edilebilir ancak ileriye dönük dinamik yapılmalı.
- **Rozet tanımları**: Veritabanında `Badge` tablosunda saklanmalı, mobil taraf API'den çekmeli.
- **Seviye (Level)**: Enum olarak backend'de tanımlı, ileride dinamik hale getirilebilir.

### 10.4 DTO Uyumluluğunun Korunması

Mobil uygulamadaki entity field isimleri backend response field isimleriyle birebir eşleşmelidir. Tutarlı naming convention: **camelCase** (JSON).

| Mobil (Dart) | Backend (C# Property) | JSON Response |
|-------------|----------------------|---------------|
| `ownerId` | `OwnerId` | `ownerId` |
| `ownerName` | `OwnerName` | `ownerName` |
| `playerNeeded` | `PlayerNeeded` | `playerNeeded` |
| `dateTime` | `DateTime` | `dateTime` |
| `placeName` | `PlaceName` | `placeName` |
| `joinedAsGroupCount` | `JoinedAsGroupCount` | `joinedAsGroupCount` |
| `applicantUserId` | `ApplicantUserId` | `applicantUserId` |
| `applicantRating` | `ApplicantRating` | `applicantRating` |
| `attendanceStatus` | `AttendanceStatus` | `attendanceStatus` |
| `fromUserId` | `FromUserId` | `fromUserId` |
| `toUserId` | `ToUserId` | `toUserId` |
| `trustScore` | `TrustScore` | `trustScore` |
| `cancellationRate` | `CancellationRate` | `cancellationRate` |
| `onTimeRate` | `OnTimeRate` | `onTimeRate` |
| `avgUserRating` | `AvgUserRating` | `avgUserRating` |
| `profileCompleted` | `ProfileCompleted` | `profileCompleted` |

**Notification DTO Uyumu:**

| Mobil (Dart) | Backend (C# Property) | JSON Response |
|-------------|----------------------|---------------|
| `id` | `Id` | `id` |
| `type` | `Type` | `type` (camelCase string: `applicationReceived`) |
| `title` | `Title` | `title` |
| `body` | `Body` | `body` |
| `data` | `Data` | `data` (JSON object) |
| `read` | `Read` | `read` |
| `createdAt` | `CreatedAt` | `createdAt` |

> **Kritik:** `type` alanı JSON'da camelCase string olarak dönülmeli (`applicationReceived`, `roomCreated` vb.). Mobil tarafta `NotificationType` enum'u bu string'lerle eşleşir.

**Subscription DTO Uyumu:**

| Mobil (Dart) | Backend (C# Property) | JSON Response |
|-------------|----------------------|---------------|
| `id` | `Id` | `id` |
| `plan` | `Plan` | `plan` (nested object) |
| `status` | `Status` | `status` (camelCase string: `active`, `expired`, `cancelled`) |
| `startedAt` | `StartedAt` | `startedAt` |
| `expiresAt` | `ExpiresAt` | `expiresAt` |
| `boostCreditsRemaining` | `BoostCreditsRemaining` | `boostCreditsRemaining` |
| `isActive` | `IsActive` | `isActive` (computed) |

**SubscriptionPlan DTO Uyumu:**

| Mobil (Dart) | Backend (C# Property) | JSON Response |
|-------------|----------------------|---------------|
| `id` | `Id` | `id` |
| `type` | `Type` | `type` (`daily`, `monthly`, `yearly`) |
| `name` | `Name` | `name` |
| `description` | `Description` | `description` |
| `price` | `Price` | `price` (decimal) |
| `currency` | `Currency` | `currency` |
| `durationDays` | `DurationDays` | `durationDays` |
| `savingsPercent` | `SavingsPercent` | `savingsPercent` (nullable) |
| `boostCredits` | `BoostCredits` | `boostCredits` |
| `features` | `Features` | `features` (nested object) |
| `sortOrder` | `SortOrder` | `sortOrder` |

**ListingBoost DTO Uyumu:**

| Mobil (Dart) | Backend (C# Property) | JSON Response |
|-------------|----------------------|---------------|
| `id` | `Id` | `id` |
| `listingId` | `ListingId` | `listingId` |
| `listingTitle` | `ListingTitle` | `listingTitle` (denormalize) |
| `boostedAt` | `BoostedAt` | `boostedAt` |
| `expiresAt` | `ExpiresAt` | `expiresAt` |
| `isActive` | `IsActive` | `isActive` (computed: `ExpiresAt > UtcNow`) |

> **Kritik:** Plan bilgileri (fiyat, özellikler, boost kredisi) her zaman backend'den çekilir. Mobil uygulama bu bilgileri cache'leyebilir ancak oturum başladığında veya `GET /subscriptions/plans` çağrıldığında güncellenmelidir. Hardcoded fiyat bilgisi kullanılmamalıdır.

### 10.5 Veritabanı İndeksleri

Performans için önerilen indeksler:

```sql
-- User
CREATE INDEX IX_Users_Phone ON Users (Phone) WHERE IsDeleted = false;
CREATE INDEX IX_Users_Email ON Users (Email) WHERE IsDeleted = false;

-- Listing
CREATE INDEX IX_Listings_Status_DateTime ON Listings (Status, DateTime) WHERE IsDeleted = false;
CREATE INDEX IX_Listings_City_District ON Listings (City, District) WHERE IsDeleted = false;
CREATE INDEX IX_Listings_OwnerId ON Listings (OwnerId) WHERE IsDeleted = false;
CREATE INDEX IX_Listings_Location ON Listings USING GIST (
  ST_MakePoint(Lng, Lat)
); -- PostGIS spatial index

-- Application
CREATE INDEX IX_Applications_ListingId ON Applications (ListingId);
CREATE INDEX IX_Applications_ApplicantUserId ON Applications (ApplicantUserId);

-- MatchRoom
CREATE INDEX IX_MatchRooms_ListingId ON MatchRooms (ListingId);
CREATE INDEX IX_MatchRooms_Status ON MatchRooms (Status);

-- Rating
CREATE INDEX IX_Ratings_ToUserId ON Ratings (ToUserId);
CREATE INDEX IX_Ratings_RoomId ON Ratings (RoomId);

-- Notification
CREATE INDEX IX_Notifications_UserId_CreatedAt ON Notifications (UserId, CreatedAt DESC);
CREATE INDEX IX_Notifications_UserId_Read ON Notifications (UserId) WHERE Read = false;

-- DeviceToken
CREATE INDEX IX_DeviceTokens_UserId ON DeviceTokens (UserId);
CREATE UNIQUE INDEX IX_DeviceTokens_Token ON DeviceTokens (Token);

-- OtpRecord
CREATE INDEX IX_OtpRecords_Target_Purpose ON OtpRecords (Target, Purpose) WHERE IsUsed = false;

-- Subscription
CREATE INDEX IX_Subscriptions_UserId_Status ON Subscriptions (UserId, Status);
CREATE INDEX IX_Subscriptions_ExpiresAt ON Subscriptions (ExpiresAt) WHERE Status = 0; -- Active
CREATE INDEX IX_SubscriptionPlans_IsActive ON SubscriptionPlans (IsActive, SortOrder);

-- ListingBoost
CREATE INDEX IX_ListingBoosts_ListingId ON ListingBoosts (ListingId);
CREATE INDEX IX_ListingBoosts_UserId ON ListingBoosts (UserId);
CREATE INDEX IX_ListingBoosts_ExpiresAt ON ListingBoosts (ExpiresAt) WHERE ExpiresAt > NOW();
```

### 10.6 API Versioning

- URL path versioning: `/v1/...`
- İleride `/v2/` gerekirse mevcut API'yi bozmadan yeni versiyon eklenebilir
- `Asp.Versioning.Http` paketi önerilir

### 10.7 Health Check & Monitoring

```csharp
// Program.cs
builder.Services.AddHealthChecks()
    .AddNpgSql(connectionString)
    .AddRedis(redisConnectionString)
    .AddUrlGroup(new Uri("https://api.sms-provider.com/health"), "SMS Provider");
```

- `/health` endpoint'i load balancer için
- `/health/ready` detaylı dependency check için
- Application Insights / Prometheus + Grafana ile monitoring

---

### 10.8 Firebase Analytics Entegrasyonu (Client-Side)

Mobil uygulamada **Firebase Analytics** entegre edilmiştir. Analytics event'leri tamamen client-side (Flutter) tarafında tetiklenir ve doğrudan Firebase'e gönderilir. Backend'den herhangi bir analytics endpoint'i **gerekmez**. Ancak backend geliştiricinin bilmesi gereken noktalar:

#### 10.8.1 User Property'ler ve Backend Senkronizasyonu

Mobil uygulama aşağıdaki user property'leri Firebase Analytics'e set eder. Bu property'ler backend API response'larından alınan verilerle güncellenir:

| User Property | Değer Kaynağı | Güncelleme Zamanı |
|---------------|--------------|-------------------|
| `is_premium` | `GET /subscriptions/me` → `isActive` | Subscription satın alma/iptal |
| `subscription_type` | `GET /subscriptions/me` → `plan.type` | Subscription değişikliği |
| `profile_completed` | `PUT /users/me` → onboarding tamamlama | Profil ilk kez tamamlandığında |
| `trust_score` | `GET /users/me` → `trustScore` | Profil yüklendiğinde |
| `total_matches` | `GET /users/me` → `totalMatches` | Profil yüklendiğinde |

> **Önemli:** Backend bu alanları doğru ve güncel dönmelidir. Örneğin `trustScore` hesaplaması backend'de yapılır ve her profil çekildiğinde mobil taraf bu değeri Firebase'e user property olarak yazar. Yanlış veya eksik değer, analytics segmentasyonunu bozar.

#### 10.8.2 Firebase'e Gönderilen Event'ler (Referans)

Aşağıdaki event'ler mobil taraftan Firebase'e gönderilmektedir. Backend geliştiricinin bu event'leri bilmesi, hangi kullanıcı aksiyonlarının takip edildiğini anlaması açısından faydalıdır:

| Kategori | Event'ler |
|----------|-----------|
| **Auth** | `otp_sent`, `otp_verified`, `otp_failed`, `otp_resent`, `social_login_started`, `social_login_success`, `social_login_failed` |
| **Onboarding** | `onboarding_started`, `onboarding_step_completed`, `onboarding_completed` |
| **Listing** | `listing_create_started`, `listing_create_completed`, `listing_detail_viewed` |
| **Application** | `apply_dialog_opened`, `apply_submitted`, `application_accepted`, `application_rejected` |
| **Match** | `match_room_viewed`, `attendance_confirmed` |
| **Subscription** | `paywall_viewed`, `paywall_plan_selected`, `paywall_cta_tapped`, `purchase_completed`, `subscription_cancelled` |
| **Diğer** | `notification_tapped`, `theme_changed`, `logout_tapped` |

#### 10.8.3 BigQuery Export (İleride)

Firebase Analytics verilerini BigQuery'ye export edip backend tarafında analiz yapmak istenirse:

- Firebase Console → Project Settings → Integrations → BigQuery'den export aktif edilir
- Backend tarafında BigQuery client ile sorgu yapılabilir (A/B test sonuçları, funnel analizi vb.)
- Bu aşamada backend'de herhangi bir tablo veya endpoint **gerekmez**; sadece Firebase Console konfigürasyonu yeterlidir

#### 10.8.4 KVKK/GDPR Uyumu (Planlanan)

Kullanıcı onay (consent) mekanizması henüz implemente edilmemiştir. Backend'de kullanıcının analytics onayını saklamak için:

```csharp
// User entity'sine eklenebilir
public bool AnalyticsConsentGiven { get; set; } = false;
public DateTime? AnalyticsConsentDate { get; set; }
```

Mobil taraf bu bilgiyi `GET /users/me` response'undan okuyarak `FirebaseAnalytics.setAnalyticsCollectionEnabled(bool)` çağrısı yapacaktır.

---

> **Son söz:** Bu doküman, mevcut Flutter uygulamasındaki tüm ekranlar, entity yapıları, kullanıcı akışları ve API endpoint tanımları baz alınarak hazırlanmıştır. Backend geliştirici bu dokümanı referans alarak, mobil uygulamayla tam uyumlu bir .NET backend implementasyonuna başlayabilir. Doküman yaşayan bir belgedir; geliştirme sürecinde keşfedilen yeni gereksinimler eklenmelidir.

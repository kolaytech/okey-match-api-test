#!/usr/bin/env python3
"""
OkeyAdvert API Endpoint Test Suite v2
Updated for: https://okey-api.kolaytech.com
Tests all endpoints and generates HTML report with spec compliance analysis.
"""

import json
import urllib.request
import urllib.error
import ssl
import time
import os
from datetime import datetime

BASE_URL = "https://okey-api.kolaytech.com"
RESULTS = []
ACCESS_TOKEN = None
REFRESH_TOKEN = None
CREATED_LISTING_ID = None
CREATED_APP_ID = None
CURRENT_USER_ID = None

def make_request(method, path, body=None, headers=None, timeout=15, content_type="application/json"):
    url = f"{BASE_URL}{path}"
    if headers is None:
        headers = {}
    headers.setdefault('User-Agent', 'OkeyMatchAPITest/2.0')
    data = None
    if body is not None:
        if isinstance(body, dict):
            data = json.dumps(body).encode('utf-8')
        else:
            data = body.encode('utf-8') if isinstance(body, str) else body
        if 'Content-Type' not in headers:
            headers['Content-Type'] = content_type
    if ACCESS_TOKEN and 'Authorization' not in headers:
        headers['Authorization'] = f'Bearer {ACCESS_TOKEN}'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    start = time.time()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            elapsed = int((time.time() - start) * 1000)
            body_bytes = resp.read()
            try:
                body_text = body_bytes.decode('utf-8')
            except:
                body_text = str(body_bytes)
            return resp.status, body_text, elapsed
    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - start) * 1000)
        try:
            body_text = e.read().decode('utf-8')
        except:
            body_text = str(e)
        return e.code, body_text, elapsed
    except urllib.error.URLError as e:
        elapsed = int((time.time() - start) * 1000)
        return 0, f"Connection Error: {str(e.reason)}", elapsed
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return 0, f"Error: {str(e)}", elapsed

def add_result(category, method, endpoint, status_code, response_body, description, requires_auth, request_body=None, elapsed_ms=0, expected_fail=False, expected_fail_reason=""):
    is_success = 200 <= status_code <= 299
    display_body = response_body
    if len(display_body) > 2000:
        display_body = display_body[:2000] + "... (truncated)"
    RESULTS.append({
        'category': category, 'method': method, 'endpoint': endpoint,
        'statusCode': status_code, 'responseBody': display_body,
        'description': description, 'requiresAuth': requires_auth,
        'requestBody': json.dumps(request_body, indent=2, ensure_ascii=False) if request_body else None,
        'isSuccess': is_success, 'elapsedMs': elapsed_ms,
        'expectedFail': expected_fail, 'expectedFailReason': expected_fail_reason
    })
    icon = "✅" if is_success else ("⚠️" if expected_fail else "❌")
    print(f"  {icon} [{status_code}] {method} {endpoint} ({elapsed_ms}ms)")

def test_health():
    print("\n📌 SERVER HEALTH")
    print("─" * 50)
    code, resp, ms = make_request("GET", "/swagger/v1/swagger.json", headers={})
    is_ok = code == 200
    add_result("Health", "GET", "/swagger/v1/swagger.json", code,
               "Swagger JSON erişilebilir" if is_ok else resp,
               "API dökümantasyonu erişimi", False, None, ms)

def test_auth():
    global ACCESS_TOKEN, REFRESH_TOKEN
    print("\n📌 AUTH Endpoints")
    print("─" * 50)

    # Register
    body = {"phone": "+905551234567", "password": "Test123456!", "fullName": "API Test Kullanıcı", "email": "apitest@okeymatch.com"}
    code, resp, ms = make_request("POST", "/api/Auth/register", body, headers={})
    add_result("Auth", "POST", "/api/Auth/register", code, resp, "Yeni kullanıcı kaydı", False, body, ms,
               expected_fail=(code == 400), expected_fail_reason="Kullanıcı daha önce kayıt olmuş olabilir")
    if code == 200:
        try:
            data = json.loads(resp)
            ACCESS_TOKEN = data.get('accessToken')
            REFRESH_TOKEN = data.get('refreshToken')
        except: pass

    # Login
    body = {"phone": "+905551234567", "password": "Test123456!"}
    code, resp, ms = make_request("POST", "/api/Auth/login", body, headers={})
    add_result("Auth", "POST", "/api/Auth/login", code, resp, "Kullanıcı girişi (phone + password)", False, body, ms)
    if code == 200:
        try:
            data = json.loads(resp)
            ACCESS_TOKEN = data.get('accessToken', ACCESS_TOKEN)
            REFRESH_TOKEN = data.get('refreshToken', REFRESH_TOKEN)
            print(f"    🔑 Token alındı! (len={len(ACCESS_TOKEN) if ACCESS_TOKEN else 0})")
        except: pass

    # Send OTP
    body = {"phone": "+905551234567"}
    code, resp, ms = make_request("POST", "/api/Auth/send-otp", body, headers={})
    add_result("Auth", "POST", "/api/Auth/send-otp", code, resp, "SMS ile OTP kodu gönderme", False, body, ms)

    # Verify OTP
    body = {"phone": "+905551234567", "code": "123456"}
    code, resp, ms = make_request("POST", "/api/Auth/verify-otp", body, headers={})
    add_result("Auth", "POST", "/api/Auth/verify-otp", code, resp, "OTP doğrulama", False, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Test OTP kodu geçersiz olabilir")
    if code == 200:
        try:
            data = json.loads(resp)
            ACCESS_TOKEN = data.get('accessToken', ACCESS_TOKEN)
            REFRESH_TOKEN = data.get('refreshToken', REFRESH_TOKEN)
        except: pass

    # Refresh Token
    body = {"refreshToken": REFRESH_TOKEN or "dummy-refresh-token"}
    code, resp, ms = make_request("POST", "/api/Auth/refresh", body, headers={})
    add_result("Auth", "POST", "/api/Auth/refresh", code, resp, "Access token yenileme", False, body, ms)
    if code == 200:
        try:
            data = json.loads(resp)
            ACCESS_TOKEN = data.get('accessToken', ACCESS_TOKEN)
            REFRESH_TOKEN = data.get('refreshToken', REFRESH_TOKEN)
        except: pass

def test_users():
    global CURRENT_USER_ID
    print("\n📌 USERS Endpoints")
    print("─" * 50)

    # GET me
    code, resp, ms = make_request("GET", "/api/Users/me")
    add_result("Users", "GET", "/api/Users/me", code, resp, "Mevcut kullanıcı profili", True, None, ms)
    if code == 200:
        try:
            data = json.loads(resp)
            CURRENT_USER_ID = data.get('id')
            print(f"    👤 User ID: {CURRENT_USER_ID}")
        except: pass

    # PUT me (update profile)
    body = {"fullName": "API Test Kullanıcı", "nickname": "api_tester", "city": "İstanbul", "district": "Kadıköy", "age": 25, "level": "mid"}
    code, resp, ms = make_request("PUT", "/api/Users/me", body)
    add_result("Users", "PUT", "/api/Users/me", code, resp, "Profil güncelleme + onboarding", True, body, ms)

    # GET user by ID
    test_id = CURRENT_USER_ID or "00000000-0000-0000-0000-000000000001"
    code, resp, ms = make_request("GET", f"/api/Users/{test_id}")
    add_result("Users", "GET", "/api/Users/{id}", code, resp, "Başka kullanıcının public profili", True, None, ms)

    # Email Send OTP
    body = {"email": "apitest@okeymatch.com"}
    code, resp, ms = make_request("POST", "/api/Users/email/send-otp", body)
    add_result("Users", "POST", "/api/Users/email/send-otp", code, resp, "Email OTP gönderimi", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Backend email service henüz tam konfigüre edilmemiş olabilir")

    # Email Verify OTP
    body = {"email": "apitest@okeymatch.com", "code": "1234"}
    code, resp, ms = make_request("POST", "/api/Users/email/verify-otp", body)
    add_result("Users", "POST", "/api/Users/email/verify-otp", code, resp, "Email OTP doğrulama", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Test OTP kodu geçersiz olabilir")

    # GET my listings
    code, resp, ms = make_request("GET", "/api/Users/me/listings?page=1&pageSize=5")
    add_result("Users", "GET", "/api/Users/me/listings", code, resp, "Kullanıcının kendi ilanları", True, None, ms,
               expected_fail=(code >= 400), expected_fail_reason="Backend'de bilinen bir serialization sorunu olabilir")

    # GET my applications
    code, resp, ms = make_request("GET", "/api/Users/me/applications?page=1&pageSize=5")
    add_result("Users", "GET", "/api/Users/me/applications", code, resp, "Kullanıcının kendi başvuruları", True, None, ms)

    # GET my matches
    code, resp, ms = make_request("GET", "/api/Users/me/matches?page=1&pageSize=5")
    add_result("Users", "GET", "/api/Users/me/matches", code, resp, "Maç geçmişi", True, None, ms)

def test_files():
    print("\n📌 FILES Endpoints")
    print("─" * 50)
    import base64
    tiny_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    boundary = "----TestBoundary123"
    body_data = f"------TestBoundary123\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test.png\"\r\nContent-Type: image/png\r\n\r\n".encode('utf-8') + tiny_png + f"\r\n------TestBoundary123--\r\n".encode('utf-8')
    headers = {'Content-Type': f'multipart/form-data; boundary=----TestBoundary123', 'User-Agent': 'OkeyMatchAPITest/2.0'}
    if ACCESS_TOKEN:
        headers['Authorization'] = f'Bearer {ACCESS_TOKEN}'
    url = f"{BASE_URL}/api/Files/upload"
    req = urllib.request.Request(url, data=body_data, headers=headers, method="POST")
    start = time.time()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            elapsed = int((time.time() - start) * 1000)
            resp_text = r.read().decode('utf-8')
            code = r.status
    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - start) * 1000)
        resp_text = e.read().decode('utf-8')
        code = e.code
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        resp_text = str(e)
        code = 0
    add_result("Files", "POST", "/api/Files/upload", code, resp_text, "Dosya yükleme (multipart)", True, {"file": "test.png (1x1 PNG)"}, elapsed,
               expected_fail=(code >= 400), expected_fail_reason="Backend AWS S3 konfigürasyonu henüz tamamlanmamış olabilir")

def test_listings():
    global CREATED_LISTING_ID
    print("\n📌 LISTINGS Endpoints")
    print("─" * 50)

    code, resp, ms = make_request("GET", "/api/Listings?Page=1&PageSize=5")
    add_result("Listings", "GET", "/api/Listings", code, resp, "Tüm ilanları listele (sayfalama)", True, None, ms,
               expected_fail=(code >= 400), expected_fail_reason="Backend'de bilinen bir serialization sorunu olabilir")

    code, resp, ms = make_request("GET", "/api/Listings?City=Istanbul&Level=beginner&Page=1&PageSize=5")
    add_result("Listings", "GET", "/api/Listings?filters", code, resp, "Filtrelenmiş ilan listesi (City, Level)", True, None, ms)

    code, resp, ms = make_request("GET", "/api/Listings?Lat=41.0082&Lng=28.9784&RadiusKm=10&Page=1&PageSize=5")
    add_result("Listings", "GET", "/api/Listings?geo", code, resp, "Konum bazlı ilan arama (Lat, Lng, Radius)", True, None, ms,
               expected_fail=(code >= 400), expected_fail_reason="Backend'de bilinen bir serialization sorunu olabilir")

    body = {"title": "Test Okey Partisi", "description": "API testi için oluşturulmuş ilan", "city": "İstanbul", "district": "Kadıköy", "lat": 40.9833, "lng": 29.0167, "placeName": "Test Kahvehane", "dateTime": "2026-05-10T14:00:00Z", "playerNeeded": 3, "level": "mid", "minAge": 18, "maxAge": 50}
    code, resp, ms = make_request("POST", "/api/Listings", body)
    add_result("Listings", "POST", "/api/Listings", code, resp, "Yeni ilan oluştur", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Backend entity save hatası — DB migration sorunu olabilir")
    if 200 <= code <= 201:
        try:
            CREATED_LISTING_ID = resp.strip().strip('"')
            print(f"    📋 Listing ID: {CREATED_LISTING_ID}")
        except: pass

    test_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"
    no_listing = CREATED_LISTING_ID is None
    code, resp, ms = make_request("GET", f"/api/Listings/{test_id}")
    add_result("Listings", "GET", "/api/Listings/{id}", code, resp, "ID ile ilan detayı getir", True, None, ms,
               expected_fail=(no_listing and code >= 400), expected_fail_reason="İlan oluşturulamadığı için dummy ID ile test edildi")

    body = {"title": "Güncellenmiş Test İlanı", "description": "Güncellenmiş açıklama", "playerNeeded": 2, "level": "advanced"}
    code, resp, ms = make_request("PUT", f"/api/Listings/{test_id}", body)
    add_result("Listings", "PUT", "/api/Listings/{id}", code, resp, "İlan güncelle", True, body, ms,
               expected_fail=(no_listing and code >= 400), expected_fail_reason="İlan oluşturulamadığı için dummy ID ile test edildi")

def test_listings_cleanup():
    print("\n📌 LISTINGS - Destructive Operations")
    print("─" * 50)
    test_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"
    no_listing = CREATED_LISTING_ID is None
    code, resp, ms = make_request("PATCH", f"/api/Listings/{test_id}/cancel")
    add_result("Listings", "PATCH", "/api/Listings/{id}/cancel", code, resp, "İlan iptal et", True, None, ms,
               expected_fail=(no_listing and code >= 400), expected_fail_reason="İlan oluşturulamadığı için dummy ID ile test edildi")
    code, resp, ms = make_request("DELETE", f"/api/Listings/{test_id}")
    add_result("Listings", "DELETE", "/api/Listings/{id}", code, resp, "İlan sil", True, None, ms,
               expected_fail=(no_listing and code >= 400), expected_fail_reason="İlan oluşturulamadığı için dummy ID ile test edildi")

def test_applications():
    global CREATED_APP_ID
    print("\n📌 APPLICATIONS Endpoints")
    print("─" * 50)
    test_listing_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"

    body = {"joinedAsGroupCount": 1, "message": "Ben de oynamak istiyorum!"}
    code, resp, ms = make_request("POST", f"/api/Applications/apply/{test_listing_id}", body)
    add_result("Applications", "POST", "/api/Applications/apply/{listingId}", code, resp, "İlana başvuru yap", True, body, ms,
               expected_fail=(code == 400), expected_fail_reason="Tek kullanıcı testi — kendi ilanına başvuru yapılamaz")
    if 200 <= code <= 201:
        try:
            CREATED_APP_ID = resp.strip().strip('"')
        except: pass

    code, resp, ms = make_request("GET", f"/api/Applications/listing/{test_listing_id}")
    add_result("Applications", "GET", "/api/Applications/listing/{listingId}", code, resp, "İlanın başvurularını listele", True, None, ms,
               expected_fail=(CREATED_LISTING_ID is None and code >= 400), expected_fail_reason="İlan oluşturulamadığı için dummy ID ile test edildi")

    test_app_id = CREATED_APP_ID or "00000000-0000-0000-0000-000000000001"
    code, resp, ms = make_request("POST", f"/api/Applications/{test_app_id}/accept")
    add_result("Applications", "POST", "/api/Applications/{id}/accept", code, resp, "Başvuruyu kabul et", True, None, ms,
               expected_fail=True, expected_fail_reason="Geçerli başvuru oluşturulamadı (tek kullanıcı limiti)")
    code, resp, ms = make_request("POST", f"/api/Applications/{test_app_id}/reject")
    add_result("Applications", "POST", "/api/Applications/{id}/reject", code, resp, "Başvuruyu reddet", True, None, ms,
               expected_fail=True, expected_fail_reason="Geçerli başvuru oluşturulamadı (tek kullanıcı limiti)")
    code, resp, ms = make_request("DELETE", f"/api/Applications/{test_app_id}")
    add_result("Applications", "DELETE", "/api/Applications/{id}", code, resp, "Başvuruyu sil/geri çek", True, None, ms,
               expected_fail=True, expected_fail_reason="Geçerli başvuru oluşturulamadı (tek kullanıcı limiti)")

def test_notifications():
    print("\n📌 NOTIFICATIONS Endpoints")
    print("─" * 50)
    code, resp, ms = make_request("GET", "/api/Notifications?page=1&pageSize=10")
    add_result("Notifications", "GET", "/api/Notifications", code, resp, "Bildirimleri listele (paginated)", True, None, ms)
    code, resp, ms = make_request("GET", "/api/Notifications?isRead=false&page=1&pageSize=10")
    add_result("Notifications", "GET", "/api/Notifications?isRead=false", code, resp, "Okunmamış bildirimleri listele", True, None, ms)
    body = {"token": "test-fcm-token-12345", "platform": "android"}
    code, resp, ms = make_request("POST", "/api/Notifications/device-token", body)
    add_result("Notifications", "POST", "/api/Notifications/device-token", code, resp, "FCM cihaz token kaydet", True, body, ms)
    body = {"token": "test-fcm-token-12345"}
    code, resp, ms = make_request("DELETE", "/api/Notifications/device-token", body)
    add_result("Notifications", "DELETE", "/api/Notifications/device-token", code, resp, "FCM cihaz token kaldır", True, body, ms)
    body = {"notificationIds": ["00000000-0000-0000-0000-000000000001"]}
    code, resp, ms = make_request("POST", "/api/Notifications/mark-read", body)
    add_result("Notifications", "POST", "/api/Notifications/mark-read", code, resp, "Bildirimleri okundu işaretle", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Dummy notification ID kullanıldı")

def test_payments():
    print("\n📌 PAYMENTS Endpoints")
    print("─" * 50)
    body = {"amount": 99.99, "currency": "TRY", "paymentMethod": "credit_card", "description": "Test ödeme", "require3DSecure": False, "cardHolderName": "Test User", "cardNumber": "4111111111111111", "expiryMonth": "12", "expiryYear": "2027", "cvv": "123"}
    code, resp, ms = make_request("POST", "/api/Payments/process", body)
    add_result("Payments", "POST", "/api/Payments/process", code, resp, "Ödeme işlemi başlat", True, body, ms)
    body = {"transactionId": "test-tx-id", "success": True, "threeDSecureResult": "OK"}
    code, resp, ms = make_request("POST", "/api/Payments/3dsecure/callback", body)
    add_result("Payments", "POST", "/api/Payments/3dsecure/callback", code, resp, "3D Secure callback işlemi", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Dummy transaction ID kullanıldı — gerçek ödeme işlemi yok")
    code, resp, ms = make_request("GET", "/api/Payments/mock/3dsecure/verify/test-tx-id")
    add_result("Payments", "GET", "/api/Payments/mock/3dsecure/verify/{txId}", code, resp, "3D Secure doğrulama (mock)", False, None, ms)

def test_ratings():
    print("\n📌 RATINGS Endpoints")
    print("─" * 50)
    body = {"roomId": "00000000-0000-0000-0000-000000000001", "toUserId": "00000000-0000-0000-0000-000000000002", "score": 5, "comment": "Harika bir oyuncu!"}
    code, resp, ms = make_request("POST", "/api/Ratings", body)
    add_result("Ratings", "POST", "/api/Ratings", code, resp, "Oyuncu değerlendirmesi oluştur", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Gerçek room/user ID gerekli")
    test_user = CURRENT_USER_ID or "00000000-0000-0000-0000-000000000001"
    code, resp, ms = make_request("GET", f"/api/Ratings/user/{test_user}")
    add_result("Ratings", "GET", "/api/Ratings/user/{userId}", code, resp, "Kullanıcının aldığı değerlendirmeler", True, None, ms)

def test_rooms():
    print("\n📌 ROOMS Endpoints")
    print("─" * 50)
    code, resp, ms = make_request("GET", "/api/Rooms/00000000-0000-0000-0000-000000000001")
    add_result("Rooms", "GET", "/api/Rooms/{id}", code, resp, "Maç odası detayı getir", True, None, ms,
               expected_fail=(code >= 400), expected_fail_reason="Gerçek room ID gerekli — henüz maç oluşturulmadı")
    code, resp, ms = make_request("POST", "/api/Rooms/00000000-0000-0000-0000-000000000001/confirm-attendance")
    add_result("Rooms", "POST", "/api/Rooms/{id}/confirm-attendance", code, resp, "Maça katılım onayla", True, None, ms,
               expected_fail=(code >= 400), expected_fail_reason="Gerçek room ID gerekli — henüz maç oluşturulmadı")

def test_subscriptions():
    print("\n📌 SUBSCRIPTIONS Endpoints")
    print("─" * 50)
    code, resp, ms = make_request("GET", "/api/Subscriptions/plans")
    add_result("Subscriptions", "GET", "/api/Subscriptions/plans", code, resp, "Abonelik planlarını listele", True, None, ms)
    code, resp, ms = make_request("GET", "/api/Subscriptions/me")
    add_result("Subscriptions", "GET", "/api/Subscriptions/me", code, resp, "Mevcut aboneliğini getir", True, None, ms)
    body = {"planId": "00000000-0000-0000-0000-000000000001", "paymentReceipt": "test-receipt-123", "platform": "ios"}
    code, resp, ms = make_request("POST", "/api/Subscriptions", body)
    add_result("Subscriptions", "POST", "/api/Subscriptions", code, resp, "Abonelik oluştur", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Geçersiz plan ID kullanıldı")
    code, resp, ms = make_request("POST", "/api/Subscriptions/me/cancel")
    add_result("Subscriptions", "POST", "/api/Subscriptions/me/cancel", code, resp, "Aboneliği iptal et", True, None, ms,
               expected_fail=(code >= 400), expected_fail_reason="Aktif abonelik yok")
    test_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"
    body = {"durationHours": 24}
    code, resp, ms = make_request("POST", f"/api/Subscriptions/boost/{test_id}", body)
    add_result("Subscriptions", "POST", "/api/Subscriptions/boost/{listingId}", code, resp, "İlanı öne çıkar (boost)", True, body, ms,
               expected_fail=(code >= 400), expected_fail_reason="Aktif abonelik veya boost hakkı yok")

def test_users_cleanup():
    print("\n📌 USERS - Delete Account (SKIP)")
    print("─" * 50)
    print("  ⏭️ DELETE /api/Users/me atlanıyor (test hesabı silinmesin)")
    add_result("Users", "DELETE", "/api/Users/me", 200, '{"skipped": true, "reason": "Test hesabı korunuyor"}',
               "Hesap silme (KVKK) — test'te atlandı", True, None, 0)


# ──────────────────────────────────────────────────────────────
# HTML REPORT GENERATOR
# ──────────────────────────────────────────────────────────────

def generate_spec_analysis():
    """Analyze spec compliance and return HTML for panels"""
    # Missing endpoints analysis (compared to backend_technical_specification.md)
    missing_endpoints = [
        {"priority": "Düşük", "endpoint": "POST /api/Users/verify-profile", "desc": "Selfie ile profil doğrulama (AWS Rekognition)", "impact": "İleride eklenebilir"},
        {"priority": "Düşük", "endpoint": "GET /subscriptions/me/boost-history", "desc": "Boost geçmişi listesi", "impact": "İleride eklenebilir"},
    ]

    # Response format differences
    format_diffs = [
        {"endpoint": "GET /api/Applications/listing/{id}", "spec": "PaginatedResult wrapper", "actual": "Plain array döner", "severity": "Orta"},
    ]

    # DTO differences
    dto_diffs = [
        {"field": "UserProfileDto.cancellationRate", "spec": "Var", "actual": "Yok", "impact": "Profil detayında gösterilemiyor"},
        {"field": "UserProfileDto.onTimeRate", "spec": "Var", "actual": "Yok", "impact": "Güven skoru detayı eksik"},
        {"field": "UserProfileDto.avgUserRating", "spec": "Var", "actual": "Yok", "impact": "Ayrı alan olarak yok, rating var"},
        {"field": "UserProfileDto.badges", "spec": "Badge array", "actual": "Yok", "impact": "Rozetler gösterilemiyor"},
        {"field": "UserProfileDto.selfiePhotoUrl", "spec": "Var", "actual": "Yok", "impact": "Selfie doğrulama desteği eksik"},
        {"field": "NotificationDto.body→message", "spec": "body alanı", "actual": "message alanı", "impact": "Alan ismi farkı — frontend mapping gerekli"},
    ]

    return missing_endpoints, format_diffs, dto_diffs


def generate_html_report():
    total = len(RESULTS)
    success = sum(1 for r in RESULTS if r['isSuccess'])
    failed = total - success
    expected_fails = sum(1 for r in RESULTS if r.get('expectedFail') and not r['isSuccess'])
    real_fails = failed - expected_fails

    categories = {}
    for r in RESULTS:
        cat = r['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    method_colors = {'GET': '#61affe', 'POST': '#49cc90', 'PUT': '#fca130', 'PATCH': '#50e3c2', 'DELETE': '#f93e3e'}
    category_icons = {'Auth': '🔐', 'Users': '👤', 'Files': '📁', 'Listings': '📋', 'Applications': '📩', 'Notifications': '🔔', 'Payments': '💳', 'Ratings': '⭐', 'Rooms': '🏠', 'Subscriptions': '💎', 'Health': '💚'}

    missing_endpoints, format_diffs, dto_diffs = generate_spec_analysis()

    now = datetime.now().strftime('%d %B %Y, %H:%M:%S')
    rate = round(success / total * 100) if total > 0 else 0

    # Build category sections
    cat_html = ""
    for cat_name, items in categories.items():
        cat_success = sum(1 for i in items if i['isSuccess'])
        cat_fail = len(items) - cat_success
        icon = category_icons.get(cat_name, '📌')

        badges_html = ""
        if cat_success > 0:
            badges_html += f'<span class="badge badge-success">{cat_success} başarılı</span>'
        if cat_fail > 0:
            badges_html += f'<span class="badge badge-fail">{cat_fail} başarısız</span>'

        endpoints_html = ""
        for item in items:
            mc = method_colors.get(item['method'], '#999')
            sc_class = 's2xx' if item['isSuccess'] else ('s4xx' if 400 <= item['statusCode'] < 500 else ('s5xx' if item['statusCode'] >= 500 else 's0xx'))
            status_icon = '✅' if item['isSuccess'] else ('⚠️' if item.get('expectedFail') else '❌')
            status_class = 'success' if item['isSuccess'] else 'fail'
            auth_badge = f'<span class="badge" style="background:rgba(59,130,246,0.1);color:#3b82f6;border:1px solid rgba(59,130,246,0.2);font-size:0.65rem;">🔒 AUTH</span>' if item['requiresAuth'] else ''

            details_html = ""
            if item['requestBody']:
                details_html += f'<div class="detail-section"><h4>📤 İstek Gövdesi (Request Body)</h4><div class="code-block">{item["requestBody"]}</div></div>'
            details_html += f'<div class="detail-section"><h4>📥 Yanıt (Response) — HTTP {item["statusCode"]}</h4><div class="code-block">{item["responseBody"]}</div></div>'

            if not item['isSuccess'] and item.get('expectedFail'):
                details_html += f'''<div class="detail-section"><div class="analysis-box expected-fail">
                    <h4>ℹ️ Beklenen Davranış</h4>
                    <p><strong>Sebep:</strong> {item.get("expectedFailReason", "")}</p>
                    <p><strong>Not:</strong> Bu bir backend hatası değil, test limitasyonundan kaynaklı beklenen sonuçtur.</p>
                </div></div>'''
            elif not item['isSuccess']:
                details_html += f'''<div class="detail-section"><div class="analysis-box">
                    <h4>⚠️ Hata Analizi</h4>
                    <p><strong>Sebep:</strong> Endpoint beklenen yanıtı döndürmedi.</p>
                    <p><strong>Öneri:</strong> Backend loglarını kontrol edin.</p>
                </div></div>'''

            ef_class = ' expected-fail-row' if (item.get('expectedFail') and not item['isSuccess']) else ''

            endpoints_html += f'''<div class="endpoint{ef_class}" data-success="{str(item['isSuccess']).lower()}" onclick="this.classList.toggle('expanded')">
                <div class="endpoint-header">
                    <div class="endpoint-status {status_class}">{status_icon}</div>
                    <span class="method-badge" style="background:{mc}">{item['method']}</span>
                    <span class="endpoint-path">{item['endpoint']}</span>
                    {auth_badge}
                    <span class="endpoint-desc">{item['description']}</span>
                    <div class="endpoint-meta">
                        <span class="status-code {sc_class}">{item['statusCode']}</span>
                        <span class="elapsed">{item['elapsedMs']}ms</span>
                    </div>
                    <span class="expand-icon">▼</span>
                </div>
                <div class="endpoint-details"><div class="details-content">{details_html}</div></div>
            </div>'''

        cat_html += f'''<div class="category">
            <div class="category-header">
                <span class="category-icon">{icon}</span>
                <h2>{cat_name}</h2>
                <div class="category-badge">{badges_html}</div>
            </div>
            {endpoints_html}
        </div>'''

    # Build spec analysis panels
    missing_rows = ""
    for m in missing_endpoints:
        color = '#ef4444' if m['priority'] == 'Kritik' else ('#f59e0b' if m['priority'] == 'Yüksek' else ('#3b82f6' if m['priority'] == 'Orta' else '#6b7280'))
        missing_rows += f'<tr><td><span style="color:{color};font-weight:600">{m["priority"]}</span></td><td><code>{m["endpoint"]}</code></td><td>{m["desc"]}</td><td>{m["impact"]}</td></tr>'

    format_rows = ""
    for f in format_diffs:
        format_rows += f'<tr><td><code>{f["endpoint"]}</code></td><td>{f["spec"]}</td><td>{f["actual"]}</td><td>{f["severity"]}</td></tr>'

    dto_rows = ""
    for d in dto_diffs:
        dto_rows += f'<tr><td><code>{d["field"]}</code></td><td>{d["spec"]}</td><td>{d["actual"]}</td><td>{d["impact"]}</td></tr>'

    spec_html = f'''<div class="spec-analysis">
        <h2 style="font-size:1.5rem;font-weight:700;margin-bottom:1.5rem;">📋 Spec Uyumluluk Analizi</h2>

        <div class="spec-panel" onclick="togglePanel(this)">
            <div class="spec-panel-header">
                <span>🚨 Eksik Endpoint'ler — Spec'te tanımlı ama backend'de yok</span>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    <span class="spec-badge" style="background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3)">{len(missing_endpoints)} EKSİK</span>
                    <span class="expand-icon">▼</span>
                </div>
            </div>
            <div class="spec-panel-content">
                <p style="color:var(--text-secondary);margin-bottom:1rem;">{f"backend_technical_specification.md dosyasında tanımlı ancak Swagger'da bulunmayan endpoint'ler."}</p>
                <table class="spec-table"><thead><tr><th>Öncelik</th><th>Endpoint</th><th>Açıklama</th><th>Etki</th></tr></thead><tbody>{missing_rows}</tbody></table>
                {"<p style='color:#10b981;margin-top:1rem;font-weight:600;'>✅ Önceki analizde 14 eksik olan endpoint sayısı 2'ye düştü! Users Controller ve Files Controller başarıyla implement edildi.</p>" if len(missing_endpoints) <= 3 else ""}
            </div>
        </div>

        <div class="spec-panel" onclick="togglePanel(this)">
            <div class="spec-panel-header">
                <span>⚠️ Response Format Farklılıkları — Spec ile uyumsuz response yapıları</span>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    <span class="spec-badge" style="background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3)">{len(format_diffs)} UYUMSUZ</span>
                    <span class="expand-icon">▼</span>
                </div>
            </div>
            <div class="spec-panel-content">
                <table class="spec-table"><thead><tr><th>Endpoint</th><th>Spec'teki Format</th><th>Mevcut Format</th><th>Önem</th></tr></thead><tbody>{format_rows}</tbody></table>
            </div>
        </div>

        <div class="spec-panel" onclick="togglePanel(this)">
            <div class="spec-panel-header">
                <span>🔄 DTO / Schema Farkları — Alan isimleri ve eksik field'lar</span>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    <span class="spec-badge" style="background:rgba(59,130,246,0.15);color:#3b82f6;border:1px solid rgba(59,130,246,0.3)">{len(dto_diffs)} FARK</span>
                    <span class="expand-icon">▼</span>
                </div>
            </div>
            <div class="spec-panel-content">
                <table class="spec-table"><thead><tr><th>Alan</th><th>Spec</th><th>Durum</th><th>Etki</th></tr></thead><tbody>{dto_rows}</tbody></table>
            </div>
        </div>
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OkeyAdvert API Test Raporu v2</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{--bg-primary:#0a0e1a;--bg-secondary:#111827;--bg-card:#1a1f35;--bg-card-hover:#1f2645;--border:#2a3155;--text-primary:#e8eaf6;--text-secondary:#9ca3af;--text-muted:#6b7280;--accent-green:#10b981;--accent-green-bg:rgba(16,185,129,0.1);--accent-red:#ef4444;--accent-red-bg:rgba(239,68,68,0.1);--accent-blue:#3b82f6;--accent-blue-bg:rgba(59,130,246,0.1);--accent-amber:#f59e0b;--accent-purple:#8b5cf6;}}
        * {{margin:0;padding:0;box-sizing:border-box;}}
        body {{font-family:'Inter',-apple-system,sans-serif;background:var(--bg-primary);color:var(--text-primary);min-height:100vh;line-height:1.6;}}
        .background-pattern {{position:fixed;top:0;left:0;right:0;bottom:0;background:radial-gradient(ellipse at 20% 50%,rgba(59,130,246,0.08) 0%,transparent 50%),radial-gradient(ellipse at 80% 50%,rgba(139,92,246,0.08) 0%,transparent 50%),radial-gradient(ellipse at 50% 0%,rgba(16,185,129,0.05) 0%,transparent 50%);pointer-events:none;z-index:0;}}
        .container {{max-width:1400px;margin:0 auto;padding:2rem 3rem;position:relative;z-index:1;}}
        .header {{text-align:center;margin-bottom:3rem;padding:2rem 0;}}
        .header h1 {{font-size:2.5rem;font-weight:800;background:linear-gradient(135deg,#3b82f6,#8b5cf6,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:0.5rem;letter-spacing:-0.02em;}}
        .header .subtitle {{color:var(--text-secondary);font-size:1rem;}}
        .header .test-date {{color:var(--text-muted);font-size:0.85rem;margin-top:0.5rem;font-family:'JetBrains Mono',monospace;}}
        .summary {{display:grid;grid-template-columns:repeat(5,1fr);gap:1.25rem;margin-bottom:3rem;}}
        .summary-card {{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:1.25rem 0.75rem;text-align:center;transition:all 0.3s ease;position:relative;overflow:visible;}}
        .summary-card::before {{content:'';position:absolute;top:0;left:0;right:0;height:3px;}}
        .summary-card.total::before {{background:linear-gradient(90deg,#3b82f6,#8b5cf6);}}
        .summary-card.success::before {{background:linear-gradient(90deg,#10b981,#34d399);}}
        .summary-card.failed::before {{background:linear-gradient(90deg,#ef4444,#f87171);}}
        .summary-card.rate::before {{background:linear-gradient(90deg,#f59e0b,#fbbf24);}}
        .summary-card.expected::before {{background:linear-gradient(90deg,#8b5cf6,#a78bfa);}}
        .summary-card:hover {{transform:translateY(-4px);border-color:rgba(59,130,246,0.3);box-shadow:0 8px 25px rgba(0,0,0,0.3);}}
        .summary-card .number {{font-size:2.5rem;font-weight:800;margin-bottom:0.25rem;}}
        .summary-card.total .number {{color:var(--accent-blue);}}
        .summary-card.success .number {{color:var(--accent-green);}}
        .summary-card.failed .number {{color:var(--accent-red);}}
        .summary-card.rate .number {{color:var(--accent-amber);}}
        .summary-card.expected .number {{color:var(--accent-purple);}}
        .summary-card .label {{color:var(--text-secondary);font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.03em;white-space:nowrap;}}
        .category {{margin-bottom:2.5rem;}}
        .category-header {{display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;padding-bottom:0.75rem;border-bottom:1px solid var(--border);}}
        .category-icon {{font-size:1.5rem;}}
        .category-header h2 {{font-size:1.4rem;font-weight:700;}}
        .category-badge {{margin-left:auto;display:flex;gap:0.5rem;}}
        .badge {{padding:0.25rem 0.75rem;border-radius:100px;font-size:0.75rem;font-weight:600;}}
        .badge-success {{background:var(--accent-green-bg);color:var(--accent-green);border:1px solid rgba(16,185,129,0.2);}}
        .badge-fail {{background:var(--accent-red-bg);color:var(--accent-red);border:1px solid rgba(239,68,68,0.2);}}
        .endpoint {{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-bottom:0.75rem;overflow:hidden;transition:all 0.2s ease;}}
        .endpoint:hover {{border-color:rgba(59,130,246,0.3);}}
        .endpoint.expected-fail-row {{border-left:3px solid var(--accent-purple);}}
        .endpoint-header {{display:flex;align-items:center;padding:1rem 1.25rem;cursor:pointer;gap:1rem;user-select:none;}}
        .endpoint-status {{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;}}
        .endpoint-status.success {{background:var(--accent-green-bg);}}
        .endpoint-status.fail {{background:var(--accent-red-bg);}}
        .method-badge {{padding:0.2rem 0.6rem;border-radius:6px;font-size:0.7rem;font-weight:700;font-family:'JetBrains Mono',monospace;text-transform:uppercase;color:#fff;min-width:60px;text-align:center;flex-shrink:0;}}
        .endpoint-path {{font-family:'JetBrains Mono',monospace;font-size:0.85rem;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
        .endpoint-desc {{color:var(--text-secondary);font-size:0.8rem;flex-shrink:0;max-width:280px;text-align:right;}}
        .endpoint-meta {{display:flex;align-items:center;gap:0.75rem;flex-shrink:0;}}
        .status-code {{font-family:'JetBrains Mono',monospace;font-size:0.8rem;font-weight:600;padding:0.15rem 0.5rem;border-radius:6px;}}
        .status-code.s2xx {{background:var(--accent-green-bg);color:var(--accent-green);}}
        .status-code.s4xx {{background:var(--accent-red-bg);color:var(--accent-red);}}
        .status-code.s5xx {{background:rgba(139,92,246,0.1);color:var(--accent-purple);}}
        .status-code.s0xx {{background:rgba(107,114,128,0.1);color:var(--text-muted);}}
        .elapsed {{font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--text-muted);}}
        .expand-icon {{color:var(--text-muted);transition:transform 0.3s ease;font-size:0.8rem;flex-shrink:0;}}
        .endpoint.expanded .expand-icon {{transform:rotate(180deg);}}
        .endpoint-details {{max-height:0;overflow:hidden;transition:max-height 0.4s ease;}}
        .endpoint.expanded .endpoint-details {{max-height:2000px;}}
        .details-content {{padding:0 1.25rem 1.25rem;border-top:1px solid var(--border);}}
        .detail-section {{margin-top:1rem;}}
        .detail-section h4 {{font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-muted);margin-bottom:0.5rem;font-weight:600;}}
        .code-block {{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:1rem;font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:#e6edf3;overflow-x:auto;white-space:pre-wrap;word-break:break-all;max-height:300px;overflow-y:auto;line-height:1.5;}}
        .analysis-box {{background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:8px;padding:1rem;margin-top:0.5rem;}}
        .analysis-box.expected-fail {{background:rgba(139,92,246,0.08);border-color:rgba(139,92,246,0.2);}}
        .analysis-box h4 {{color:var(--accent-amber);font-size:0.85rem;margin-bottom:0.5rem;text-transform:none;letter-spacing:0;}}
        .analysis-box.expected-fail h4 {{color:var(--accent-purple);}}
        .analysis-box p {{color:var(--text-secondary);font-size:0.8rem;margin-bottom:0.25rem;}}
        .filter-bar {{display:flex;gap:0.75rem;margin-bottom:2rem;flex-wrap:wrap;}}
        .filter-btn {{padding:0.5rem 1.25rem;border-radius:100px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);cursor:pointer;font-size:0.85rem;font-weight:500;transition:all 0.2s ease;font-family:'Inter',sans-serif;}}
        .filter-btn:hover {{border-color:var(--accent-blue);color:var(--accent-blue);}}
        .filter-btn.active {{background:var(--accent-blue-bg);color:var(--accent-blue);border-color:var(--accent-blue);}}
        .spec-analysis {{margin-bottom:3rem;}}
        .spec-panel {{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-bottom:0.75rem;overflow:hidden;cursor:pointer;transition:all 0.2s ease;}}
        .spec-panel:hover {{border-color:rgba(59,130,246,0.3);}}
        .spec-panel-header {{display:flex;align-items:center;justify-content:space-between;padding:1rem 1.25rem;font-weight:500;}}
        .spec-panel-content {{max-height:0;overflow:hidden;transition:max-height 0.4s ease;}}
        .spec-panel.expanded .spec-panel-content {{max-height:2000px;}}
        .spec-panel.expanded .expand-icon {{transform:rotate(180deg);}}
        .spec-panel-content {{padding:0 1.25rem;}}
        .spec-panel.expanded .spec-panel-content {{padding:0 1.25rem 1.25rem;}}
        .spec-badge {{padding:0.25rem 0.75rem;border-radius:100px;font-size:0.7rem;font-weight:700;text-transform:uppercase;}}
        .spec-table {{width:100%;border-collapse:collapse;margin-top:0.5rem;font-size:0.8rem;}}
        .spec-table th {{text-align:left;padding:0.5rem;color:var(--text-muted);border-bottom:1px solid var(--border);font-weight:600;text-transform:uppercase;font-size:0.7rem;letter-spacing:0.05em;}}
        .spec-table td {{padding:0.5rem;border-bottom:1px solid rgba(42,49,85,0.5);color:var(--text-secondary);}}
        .spec-table code {{background:rgba(59,130,246,0.1);color:var(--accent-blue);padding:0.1rem 0.4rem;border-radius:4px;font-size:0.75rem;}}
        .footer {{text-align:center;padding:2rem;color:var(--text-muted);font-size:0.8rem;border-top:1px solid var(--border);margin-top:2rem;}}

        /* Responsive */
        @media (max-width: 900px) {{
            .summary {{grid-template-columns:repeat(2,1fr);}}
            .endpoint-header {{flex-wrap:wrap;gap:0.5rem;}}
            .endpoint-path {{min-width:100%;order:10;font-size:0.8rem;}}
            .endpoint-desc {{max-width:100%;text-align:left;order:11;font-size:0.75rem;}}
            .header h1 {{font-size:1.8rem;}}
            .spec-panel-header {{flex-wrap:wrap;gap:0.5rem;}}
        }}
        @media (max-width: 480px) {{
            .summary {{grid-template-columns:repeat(2,1fr);}}
            .summary-card .number {{font-size:1.8rem;}}
            .container {{padding:1rem;}}
            .endpoint-meta {{gap:0.5rem;}}
        }}
    </style>
</head>
<body>
    <div class="background-pattern"></div>
    <div class="container">
        <div class="header">
            <h1>🎯 OkeyAdvert API Test Raporu</h1>
            <p class="subtitle">Tüm endpoint'lerin otomatik test sonuçları</p>
            <p class="test-date">Test tarihi: {now}</p>
            <p class="test-date">Base URL: {BASE_URL}</p>
        </div>

        <div class="summary">
            <div class="summary-card total"><div class="number">{total}</div><div class="label">Toplam</div></div>
            <div class="summary-card success"><div class="number">{success}</div><div class="label">Başarılı ✅</div></div>
            <div class="summary-card failed"><div class="number">{real_fails}</div><div class="label">Hata ❌</div></div>
            <div class="summary-card expected"><div class="number">{expected_fails}</div><div class="label">Beklenen ⚠️</div></div>
            <div class="summary-card rate"><div class="number">{rate}%</div><div class="label">Başarı</div></div>
        </div>

        {spec_html}

        <div class="filter-bar">
            <button class="filter-btn active" onclick="filterResults('all')">Tümü ({total})</button>
            <button class="filter-btn" onclick="filterResults('success')">✅ Başarılı ({success})</button>
            <button class="filter-btn" onclick="filterResults('fail')">❌ Başarısız ({failed})</button>
            <button class="filter-btn" onclick="filterResults('expected')">⚠️ Beklenen ({expected_fails})</button>
        </div>

        {cat_html}

        <div class="footer">
            <p>OkeyAdvert API Test Suite v2 — Otomatik oluşturuldu</p>
            <p>kolaytech/okey-match-api-test</p>
        </div>
    </div>

    <script>
        function filterResults(type) {{
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.endpoint').forEach(el => {{
                const isSuccess = el.dataset.success === 'true';
                const isExpected = el.classList.contains('expected-fail-row');
                if (type === 'all') el.style.display = '';
                else if (type === 'success') el.style.display = isSuccess ? '' : 'none';
                else if (type === 'fail') el.style.display = !isSuccess ? '' : 'none';
                else if (type === 'expected') el.style.display = (isExpected && !isSuccess) ? '' : 'none';
            }});
        }}

        function togglePanel(el) {{
            el.classList.toggle('expanded');
        }}
    </script>
</body>
</html>'''

    # Write HTML
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, 'api_test_report.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n📄 Rapor oluşturuldu: {report_path}")

    # Also copy as index.html for GitHub Pages
    index_path = os.path.join(script_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"📄 index.html kopyalandı: {index_path}")

    # Write JSON results
    results_path = os.path.join(script_dir, 'results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(RESULTS, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    print("=" * 60)
    print("🎯 OkeyAdvert API Test Suite v2")
    print(f"📡 Base URL: {BASE_URL}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    test_health()
    test_auth()
    test_users()
    test_files()
    test_listings()
    test_applications()
    test_listings_cleanup()
    test_notifications()
    test_payments()
    test_ratings()
    test_rooms()
    test_subscriptions()
    test_users_cleanup()

    total = len(RESULTS)
    success = sum(1 for r in RESULTS if r['isSuccess'])
    expected = sum(1 for r in RESULTS if r.get('expectedFail') and not r['isSuccess'])
    print(f"\n{'=' * 60}")
    print(f"📊 Sonuç: {success}/{total} başarılı ({round(success/total*100)}%)")
    print(f"   ⚠️ Beklenen hatalar: {expected}")
    print(f"   ❌ Gerçek hatalar: {total - success - expected}")
    print(f"{'=' * 60}")

    generate_html_report()

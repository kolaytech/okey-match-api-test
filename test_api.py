#!/usr/bin/env python3
"""
OkeyAdvert API Endpoint Test Suite
Tests all endpoints from Swagger spec and generates HTML report.
"""

import json
import urllib.request
import urllib.error
import ssl
import time
from datetime import datetime

BASE_URL = "http://94.138.209.132:8080"
RESULTS = []
ACCESS_TOKEN = None
REFRESH_TOKEN = None
CREATED_LISTING_ID = None
CREATED_APP_ID = None

def make_request(method, path, body=None, headers=None, timeout=15):
    """Make HTTP request and return (status_code, response_body, elapsed_ms)"""
    url = f"{BASE_URL}{path}"
    if headers is None:
        headers = {}
    
    data = None
    if body is not None:
        if isinstance(body, dict):
            data = json.dumps(body).encode('utf-8')
        else:
            data = body.encode('utf-8') if isinstance(body, str) else body
        headers['Content-Type'] = 'application/json'
    
    if ACCESS_TOKEN and 'Authorization' not in headers:
        headers['Authorization'] = f'Bearer {ACCESS_TOKEN}'
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    start = time.time()
    try:
        # Ignore SSL for testing
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


def add_result(category, method, endpoint, status_code, response_body, description, requires_auth, request_body=None, elapsed_ms=0):
    """Add a test result"""
    # Determine if success
    is_success = 200 <= status_code <= 299
    
    # Truncate large responses for display
    display_body = response_body
    if len(display_body) > 2000:
        display_body = display_body[:2000] + "... (truncated)"
    
    RESULTS.append({
        'category': category,
        'method': method,
        'endpoint': endpoint,
        'statusCode': status_code,
        'responseBody': display_body,
        'description': description,
        'requiresAuth': requires_auth,
        'requestBody': json.dumps(request_body, indent=2, ensure_ascii=False) if request_body else None,
        'isSuccess': is_success,
        'elapsedMs': elapsed_ms
    })
    
    icon = "✅" if is_success else "❌"
    print(f"  {icon} [{status_code}] {method} {endpoint} ({elapsed_ms}ms)")


def test_auth():
    """Test Auth endpoints"""
    global ACCESS_TOKEN, REFRESH_TOKEN
    print("\n📌 AUTH Endpoints")
    print("─" * 50)
    
    # Register
    body = {"phone": "+905551234567", "password": "Test123456!", "fullName": "API Test Kullanıcı", "email": "apitest@okeymatch.com"}
    code, resp, ms = make_request("POST", "/api/Auth/register", body, headers={})
    add_result("Auth", "POST", "/api/Auth/register", code, resp, "Yeni kullanıcı kaydı", False, body, ms)
    
    if code == 200:
        try:
            data = json.loads(resp)
            ACCESS_TOKEN = data.get('accessToken')
            REFRESH_TOKEN = data.get('refreshToken')
        except:
            pass
    
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
        except:
            pass
    
    # Send OTP
    body = {"phone": "+905551234567"}
    code, resp, ms = make_request("POST", "/api/Auth/send-otp", body, headers={})
    add_result("Auth", "POST", "/api/Auth/send-otp", code, resp, "SMS ile OTP kodu gönderme", False, body, ms)
    
    # Verify OTP
    body = {"phone": "+905551234567", "code": "123456"}
    code, resp, ms = make_request("POST", "/api/Auth/verify-otp", body, headers={})
    add_result("Auth", "POST", "/api/Auth/verify-otp", code, resp, "OTP doğrulama", False, body, ms)
    
    # Refresh Token
    body = {"refreshToken": REFRESH_TOKEN or "dummy-refresh-token"}
    code, resp, ms = make_request("POST", "/api/Auth/refresh", body, headers={})
    add_result("Auth", "POST", "/api/Auth/refresh", code, resp, "Access token yenileme", False, body, ms)
    
    if code == 200:
        try:
            data = json.loads(resp)
            ACCESS_TOKEN = data.get('accessToken', ACCESS_TOKEN)
            REFRESH_TOKEN = data.get('refreshToken', REFRESH_TOKEN)
        except:
            pass


def test_listings():
    """Test Listings endpoints"""
    global CREATED_LISTING_ID
    print("\n📌 LISTINGS Endpoints")
    print("─" * 50)
    
    # GET all listings
    code, resp, ms = make_request("GET", "/api/Listings?Page=1&PageSize=5")
    add_result("Listings", "GET", "/api/Listings", code, resp, "Tüm ilanları listele (sayfalama)", True, None, ms)
    
    # GET filtered
    code, resp, ms = make_request("GET", "/api/Listings?City=Istanbul&Level=beginner&Page=1&PageSize=5")
    add_result("Listings", "GET", "/api/Listings?filters", code, resp, "Filtrelenmiş ilan listesi (City, Level)", True, None, ms)
    
    # GET with geo filter
    code, resp, ms = make_request("GET", "/api/Listings?Lat=41.0082&Lng=28.9784&RadiusKm=10&Page=1&PageSize=5")
    add_result("Listings", "GET", "/api/Listings?geo", code, resp, "Konum bazlı ilan arama (Lat, Lng, Radius)", True, None, ms)
    
    # POST create listing
    body = {
        "title": "Test Okey Partisi",
        "description": "API testi için oluşturulmuş ilan",
        "city": "İstanbul",
        "district": "Kadıköy",
        "lat": 40.9833,
        "lng": 29.0167,
        "placeName": "Test Kahvehane",
        "dateTime": "2026-04-10T14:00:00Z",
        "playerNeeded": 3,
        "level": "mid",
        "minAge": 18,
        "maxAge": 50
    }
    code, resp, ms = make_request("POST", "/api/Listings", body)
    add_result("Listings", "POST", "/api/Listings", code, resp, "Yeni ilan oluştur", True, body, ms)
    
    if 200 <= code <= 201:
        try:
            data = json.loads(resp)
            if isinstance(data, dict) and 'id' in data:
                CREATED_LISTING_ID = data['id']
            else:
                CREATED_LISTING_ID = resp.strip().strip('"')
        except:
            CREATED_LISTING_ID = resp.strip().strip('"')
        print(f"    📋 Listing ID: {CREATED_LISTING_ID}")
    
    # GET by ID
    test_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"
    code, resp, ms = make_request("GET", f"/api/Listings/{test_id}")
    add_result("Listings", "GET", "/api/Listings/{id}", code, resp, "ID ile ilan detayı getir", True, None, ms)
    
    # PUT update
    body = {
        "title": "Güncellenmiş Test İlanı",
        "description": "Güncellenmiş açıklama",
        "playerNeeded": 2,
        "level": "advanced"
    }
    code, resp, ms = make_request("PUT", f"/api/Listings/{test_id}", body)
    add_result("Listings", "PUT", "/api/Listings/{id}", code, resp, "İlan güncelle", True, body, ms)
    
    # NOTE: Cancel and Delete are tested AFTER applications, so they can use a valid listing ID


def test_listings_cleanup():
    """Test destructive listing operations (cancel, delete) after other tests"""
    print("\n📌 LISTINGS - Destructive Operations")
    print("─" * 50)
    
    test_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"
    
    # PATCH cancel
    code, resp, ms = make_request("PATCH", f"/api/Listings/{test_id}/cancel")
    add_result("Listings", "PATCH", "/api/Listings/{id}/cancel", code, resp, "İlan iptal et", True, None, ms)
    
    # DELETE
    code, resp, ms = make_request("DELETE", f"/api/Listings/{test_id}")
    add_result("Listings", "DELETE", "/api/Listings/{id}", code, resp, "İlan sil", True, None, ms)


def test_applications():
    """Test Applications endpoints"""
    global CREATED_APP_ID
    print("\n📌 APPLICATIONS Endpoints")
    print("─" * 50)
    
    test_listing_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"
    
    # POST apply
    body = {"joinedAsGroupCount": 1, "message": "Ben de oynamak istiyorum!"}
    code, resp, ms = make_request("POST", f"/api/Applications/apply/{test_listing_id}", body)
    add_result("Applications", "POST", "/api/Applications/apply/{listingId}", code, resp, "İlana başvuru yap", True, body, ms)
    
    if 200 <= code <= 201:
        try:
            data = json.loads(resp)
            if isinstance(data, dict) and 'id' in data:
                CREATED_APP_ID = data['id']
            else:
                CREATED_APP_ID = resp.strip().strip('"')
        except:
            CREATED_APP_ID = resp.strip().strip('"')
        print(f"    📋 Application ID: {CREATED_APP_ID}")
    
    # GET listing apps
    code, resp, ms = make_request("GET", f"/api/Applications/listing/{test_listing_id}")
    add_result("Applications", "GET", "/api/Applications/listing/{listingId}", code, resp, "İlanın başvurularını listele", True, None, ms)
    
    test_app_id = CREATED_APP_ID or "00000000-0000-0000-0000-000000000001"
    
    # POST accept
    code, resp, ms = make_request("POST", f"/api/Applications/{test_app_id}/accept")
    add_result("Applications", "POST", "/api/Applications/{id}/accept", code, resp, "Başvuruyu kabul et", True, None, ms)
    
    # POST reject
    code, resp, ms = make_request("POST", f"/api/Applications/{test_app_id}/reject")
    add_result("Applications", "POST", "/api/Applications/{id}/reject", code, resp, "Başvuruyu reddet", True, None, ms)
    
    # DELETE
    code, resp, ms = make_request("DELETE", f"/api/Applications/{test_app_id}")
    add_result("Applications", "DELETE", "/api/Applications/{id}", code, resp, "Başvuruyu sil/geri çek", True, None, ms)


def test_notifications():
    """Test Notifications endpoints"""
    print("\n📌 NOTIFICATIONS Endpoints")
    print("─" * 50)
    
    # GET notifications
    code, resp, ms = make_request("GET", "/api/Notifications?page=1&pageSize=10")
    add_result("Notifications", "GET", "/api/Notifications", code, resp, "Bildirimleri listele", True, None, ms)
    
    # GET unread
    code, resp, ms = make_request("GET", "/api/Notifications?isRead=false&page=1&pageSize=10")
    add_result("Notifications", "GET", "/api/Notifications?isRead=false", code, resp, "Okunmamış bildirimleri listele", True, None, ms)
    
    # POST register device
    body = {"token": "test-fcm-token-12345", "platform": "android"}
    code, resp, ms = make_request("POST", "/api/Notifications/device-token", body)
    add_result("Notifications", "POST", "/api/Notifications/device-token", code, resp, "FCM cihaz token kaydet", True, body, ms)
    
    # DELETE unregister device
    body = {"token": "test-fcm-token-12345"}
    code, resp, ms = make_request("DELETE", "/api/Notifications/device-token", body)
    add_result("Notifications", "DELETE", "/api/Notifications/device-token", code, resp, "FCM cihaz token kaldır", True, body, ms)
    
    # POST mark read
    body = {"notificationIds": ["00000000-0000-0000-0000-000000000001"]}
    code, resp, ms = make_request("POST", "/api/Notifications/mark-read", body)
    add_result("Notifications", "POST", "/api/Notifications/mark-read", code, resp, "Bildirimleri okundu işaretle", True, body, ms)


def test_payments():
    """Test Payments endpoints"""
    print("\n📌 PAYMENTS Endpoints")
    print("─" * 50)
    
    # POST process
    body = {
        "amount": 99.99,
        "currency": "TRY",
        "paymentMethod": "credit_card",
        "description": "Test ödeme",
        "require3DSecure": False,
        "cardHolderName": "Test User",
        "cardNumber": "4111111111111111",
        "expiryMonth": "12",
        "expiryYear": "2027",
        "cvv": "123"
    }
    code, resp, ms = make_request("POST", "/api/Payments/process", body)
    add_result("Payments", "POST", "/api/Payments/process", code, resp, "Ödeme işlemi başlat", True, body, ms)
    
    # POST 3d secure callback
    body = {"transactionId": "test-tx-id", "success": True, "threeDSecureResult": "OK"}
    code, resp, ms = make_request("POST", "/api/Payments/3dsecure/callback", body)
    add_result("Payments", "POST", "/api/Payments/3dsecure/callback", code, resp, "3D Secure callback işlemi", True, body, ms)
    
    # GET mock 3d verify
    code, resp, ms = make_request("GET", "/api/Payments/mock/3dsecure/verify/test-tx-id")
    add_result("Payments", "GET", "/api/Payments/mock/3dsecure/verify/{txId}", code, resp, "3D Secure doğrulama (mock/test)", False, None, ms)


def test_ratings():
    """Test Ratings endpoints"""
    print("\n📌 RATINGS Endpoints")
    print("─" * 50)
    
    # POST create rating
    body = {
        "roomId": "00000000-0000-0000-0000-000000000001",
        "toUserId": "00000000-0000-0000-0000-000000000002",
        "score": 5,
        "comment": "Harika bir oyuncu!"
    }
    code, resp, ms = make_request("POST", "/api/Ratings", body)
    add_result("Ratings", "POST", "/api/Ratings", code, resp, "Oyuncu değerlendirmesi oluştur", True, body, ms)
    
    # GET user ratings
    code, resp, ms = make_request("GET", "/api/Ratings/user/00000000-0000-0000-0000-000000000001")
    add_result("Ratings", "GET", "/api/Ratings/user/{userId}", code, resp, "Kullanıcının aldığı değerlendirmeler", True, None, ms)


def test_rooms():
    """Test Rooms endpoints"""
    print("\n📌 ROOMS Endpoints")
    print("─" * 50)
    
    # GET room
    code, resp, ms = make_request("GET", "/api/Rooms/00000000-0000-0000-0000-000000000001")
    add_result("Rooms", "GET", "/api/Rooms/{id}", code, resp, "Maç odası detayı getir", True, None, ms)
    
    # POST confirm attendance
    code, resp, ms = make_request("POST", "/api/Rooms/00000000-0000-0000-0000-000000000001/confirm-attendance")
    add_result("Rooms", "POST", "/api/Rooms/{id}/confirm-attendance", code, resp, "Maça katılım onayla", True, None, ms)


def test_subscriptions():
    """Test Subscriptions endpoints"""
    print("\n📌 SUBSCRIPTIONS Endpoints")
    print("─" * 50)
    
    # GET plans
    code, resp, ms = make_request("GET", "/api/Subscriptions/plans")
    add_result("Subscriptions", "GET", "/api/Subscriptions/plans", code, resp, "Abonelik planlarını listele", True, None, ms)
    
    # GET my subscription
    code, resp, ms = make_request("GET", "/api/Subscriptions/me")
    add_result("Subscriptions", "GET", "/api/Subscriptions/me", code, resp, "Mevcut aboneliğini getir", True, None, ms)
    
    # POST create
    body = {"planId": "00000000-0000-0000-0000-000000000001", "paymentReceipt": "test-receipt-123", "platform": "ios"}
    code, resp, ms = make_request("POST", "/api/Subscriptions", body)
    add_result("Subscriptions", "POST", "/api/Subscriptions", code, resp, "Abonelik oluştur", True, body, ms)
    
    # POST cancel
    code, resp, ms = make_request("POST", "/api/Subscriptions/me/cancel")
    add_result("Subscriptions", "POST", "/api/Subscriptions/me/cancel", code, resp, "Aboneliği iptal et", True, None, ms)
    
    # POST boost
    test_id = CREATED_LISTING_ID or "00000000-0000-0000-0000-000000000001"
    body = {"durationHours": 24}
    code, resp, ms = make_request("POST", f"/api/Subscriptions/boost/{test_id}", body)
    add_result("Subscriptions", "POST", "/api/Subscriptions/boost/{listingId}", code, resp, "İlanı öne çıkar (boost)", True, body, ms)


def test_health():
    """Test server health"""
    print("\n📌 SERVER HEALTH")
    print("─" * 50)
    
    code, resp, ms = make_request("GET", "/swagger/v1/swagger.json", headers={})
    is_ok = code == 200
    add_result("Health", "GET", "/swagger/v1/swagger.json", code, 
               "Swagger JSON erişilebilir" if is_ok else resp, 
               "API dökümantasyonu erişimi", False, None, ms)


def generate_html_report():
    """Generate beautiful HTML report"""
    
    total = len(RESULTS)
    success = sum(1 for r in RESULTS if r['isSuccess'])
    failed = total - success
    
    # Group by category
    categories = {}
    for r in RESULTS:
        cat = r['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)
    
    method_colors = {
        'GET': '#61affe',
        'POST': '#49cc90',
        'PUT': '#fca130',
        'PATCH': '#50e3c2',
        'DELETE': '#f93e3e'
    }
    
    category_icons = {
        'Auth': '🔐',
        'Listings': '📋',
        'Applications': '📩',
        'Notifications': '🔔',
        'Payments': '💳',
        'Ratings': '⭐',
        'Rooms': '🏠',
        'Subscriptions': '💎',
        'Health': '💚'
    }
    
    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OkeyAdvert API Test Raporu</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0e1a;
            --bg-secondary: #111827;
            --bg-card: #1a1f35;
            --bg-card-hover: #1f2645;
            --border: #2a3155;
            --text-primary: #e8eaf6;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent-green: #10b981;
            --accent-green-bg: rgba(16, 185, 129, 0.1);
            --accent-red: #ef4444;
            --accent-red-bg: rgba(239, 68, 68, 0.1);
            --accent-blue: #3b82f6;
            --accent-blue-bg: rgba(59, 130, 246, 0.1);
            --accent-amber: #f59e0b;
            --accent-purple: #8b5cf6;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        .background-pattern {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(ellipse at 20% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 50%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 0%, rgba(16, 185, 129, 0.05) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            position: relative;
            z-index: 1;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem 0;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }}
        
        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 400;
        }}
        
        .header .test-date {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 0.5rem;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        /* Summary Cards */
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 3rem;
        }}
        
        .summary-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .summary-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
        }}
        
        .summary-card.total::before {{ background: linear-gradient(90deg, #3b82f6, #8b5cf6); }}
        .summary-card.success::before {{ background: linear-gradient(90deg, #10b981, #34d399); }}
        .summary-card.failed::before {{ background: linear-gradient(90deg, #ef4444, #f87171); }}
        .summary-card.rate::before {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
        
        .summary-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(59, 130, 246, 0.3);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }}
        
        .summary-card .number {{
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }}
        
        .summary-card.total .number {{ color: var(--accent-blue); }}
        .summary-card.success .number {{ color: var(--accent-green); }}
        .summary-card.failed .number {{ color: var(--accent-red); }}
        .summary-card.rate .number {{ color: var(--accent-amber); }}
        
        .summary-card .label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        /* Category Section */
        .category {{
            margin-bottom: 2.5rem;
        }}
        
        .category-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
        }}
        
        .category-icon {{
            font-size: 1.5rem;
        }}
        
        .category-header h2 {{
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-primary);
        }}
        
        .category-badge {{
            margin-left: auto;
            display: flex;
            gap: 0.5rem;
        }}
        
        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        
        .badge-success {{
            background: var(--accent-green-bg);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}
        
        .badge-fail {{
            background: var(--accent-red-bg);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}
        
        /* Endpoint Row */
        .endpoint {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 0.75rem;
            overflow: hidden;
            transition: all 0.2s ease;
        }}
        
        .endpoint:hover {{
            border-color: rgba(59, 130, 246, 0.3);
        }}
        
        .endpoint-header {{
            display: flex;
            align-items: center;
            padding: 1rem 1.25rem;
            cursor: pointer;
            gap: 1rem;
            user-select: none;
        }}
        
        .endpoint-status {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            flex-shrink: 0;
        }}
        
        .endpoint-status.success {{
            background: var(--accent-green-bg);
        }}
        
        .endpoint-status.fail {{
            background: var(--accent-red-bg);
        }}
        
        .method-badge {{
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #fff;
            min-width: 60px;
            text-align: center;
            flex-shrink: 0;
        }}
        
        .endpoint-path {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: var(--text-primary);
            flex: 1;
        }}
        
        .endpoint-desc {{
            color: var(--text-secondary);
            font-size: 0.8rem;
            margin-left: auto;
            flex-shrink: 0;
        }}
        
        .endpoint-meta {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-shrink: 0;
        }}
        
        .status-code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
        }}
        
        .status-code.s2xx {{
            background: var(--accent-green-bg);
            color: var(--accent-green);
        }}
        
        .status-code.s4xx {{
            background: var(--accent-red-bg);
            color: var(--accent-red);
        }}
        
        .status-code.s5xx {{
            background: rgba(139, 92, 246, 0.1);
            color: var(--accent-purple);
        }}
        
        .status-code.s0xx {{
            background: rgba(107, 114, 128, 0.1);
            color: var(--text-muted);
        }}
        
        .elapsed {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        
        .expand-icon {{
            color: var(--text-muted);
            transition: transform 0.3s ease;
            font-size: 0.8rem;
            flex-shrink: 0;
        }}
        
        .endpoint.expanded .expand-icon {{
            transform: rotate(180deg);
        }}
        
        .endpoint-details {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.4s ease;
        }}
        
        .endpoint.expanded .endpoint-details {{
            max-height: 2000px;
        }}
        
        .details-content {{
            padding: 0 1.25rem 1.25rem;
            border-top: 1px solid var(--border);
        }}
        
        .detail-section {{
            margin-top: 1rem;
        }}
        
        .detail-section h4 {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            font-weight: 600;
        }}
        
        .code-block {{
            background: #0d1117;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            line-height: 1.5;
            color: #c9d1d9;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        
        .error-analysis {{
            background: rgba(239, 68, 68, 0.05);
            border: 1px solid rgba(239, 68, 68, 0.15);
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-top: 1rem;
        }}
        
        .error-analysis h4 {{
            color: var(--accent-red);
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .error-analysis .reason {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }}
        
        .error-analysis .suggestion {{
            color: var(--accent-amber);
            font-size: 0.85rem;
            padding-left: 1rem;
            border-left: 2px solid var(--accent-amber);
        }}
        
        .auth-badge {{
            font-size: 0.65rem;
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            background: rgba(139, 92, 246, 0.15);
            color: var(--accent-purple);
            border: 1px solid rgba(139, 92, 246, 0.2);
            font-weight: 600;
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
            margin-top: 3rem;
        }}
        
        /* Filter Buttons */
        .filters {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 0.5rem 1.25rem;
            border-radius: 100px;
            border: 1px solid var(--border);
            background: var(--bg-card);
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: 'Inter', sans-serif;
        }}
        
        .filter-btn:hover {{
            border-color: var(--accent-blue);
            color: var(--accent-blue);
        }}
        
        .filter-btn.active {{
            background: var(--accent-blue-bg);
            border-color: var(--accent-blue);
            color: var(--accent-blue);
        }}

        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .header h1 {{ font-size: 1.8rem; }}
            .endpoint-header {{ flex-wrap: wrap; gap: 0.5rem; }}
            .endpoint-desc {{ display: none; }}
            .summary {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="background-pattern"></div>
    <div class="container">
        <div class="header">
            <h1>🎯 OkeyAdvert API Test Raporu</h1>
            <p class="subtitle">Tüm endpoint'lerin otomatik test sonuçları</p>
            <p class="test-date">Test tarihi: {datetime.now().strftime("%d %B %Y, %H:%M:%S")}</p>
            <p class="test-date">Base URL: {BASE_URL}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card total">
                <div class="number">{total}</div>
                <div class="label">Toplam Endpoint</div>
            </div>
            <div class="summary-card success">
                <div class="number">{success}</div>
                <div class="label">Başarılı ✅</div>
            </div>
            <div class="summary-card failed">
                <div class="number">{failed}</div>
                <div class="label">Başarısız ❌</div>
            </div>
            <div class="summary-card rate">
                <div class="number">{round(success/total*100) if total > 0 else 0}%</div>
                <div class="label">Başarı Oranı</div>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" onclick="filterResults('all')">Tümü ({total})</button>
            <button class="filter-btn" onclick="filterResults('success')">✅ Başarılı ({success})</button>
            <button class="filter-btn" onclick="filterResults('fail')">❌ Başarısız ({failed})</button>
        </div>
"""
    
    for cat_name, cat_results in categories.items():
        cat_success = sum(1 for r in cat_results if r['isSuccess'])
        cat_fail = len(cat_results) - cat_success
        cat_icon = category_icons.get(cat_name, '📦')
        
        html += f"""
        <div class="category">
            <div class="category-header">
                <span class="category-icon">{cat_icon}</span>
                <h2>{cat_name}</h2>
                <div class="category-badge">
                    <span class="badge badge-success">{cat_success} başarılı</span>
                    {"<span class='badge badge-fail'>" + str(cat_fail) + " başarısız</span>" if cat_fail > 0 else ""}
                </div>
            </div>
"""
        
        for r in cat_results:
            status_icon = "✅" if r['isSuccess'] else "❌"
            status_class = "success" if r['isSuccess'] else "fail"
            method_color = method_colors.get(r['method'], '#6b7280')
            
            sc = r['statusCode']
            if 200 <= sc <= 299:
                sc_class = "s2xx"
            elif 400 <= sc <= 499:
                sc_class = "s4xx"
            elif sc >= 500:
                sc_class = "s5xx"
            else:
                sc_class = "s0xx"
            
            # Error analysis
            error_html = ""
            if not r['isSuccess']:
                reason, suggestion = analyze_error(r)
                error_html = f"""
                    <div class="error-analysis">
                        <h4>⚠️ Hata Analizi</h4>
                        <p class="reason"><strong>Sebep:</strong> {reason}</p>
                        <p class="suggestion"><strong>Öneri:</strong> {suggestion}</p>
                    </div>
"""
            
            # Request body section
            req_body_html = ""
            if r['requestBody']:
                req_body_html = f"""
                    <div class="detail-section">
                        <h4>📤 İstek Gövdesi (Request Body)</h4>
                        <div class="code-block">{escape_html(r['requestBody'])}</div>
                    </div>
"""
            
            auth_badge = '<span class="auth-badge">🔒 AUTH</span>' if r['requiresAuth'] else ''
            
            html += f"""
            <div class="endpoint" data-status="{status_class}">
                <div class="endpoint-header" onclick="toggleEndpoint(this)">
                    <div class="endpoint-status {status_class}">{status_icon}</div>
                    <span class="method-badge" style="background: {method_color}">{r['method']}</span>
                    <span class="endpoint-path">{escape_html(r['endpoint'])}</span>
                    {auth_badge}
                    <span class="endpoint-desc">{r['description']}</span>
                    <div class="endpoint-meta">
                        <span class="status-code {sc_class}">{r['statusCode']}</span>
                        <span class="elapsed">{r['elapsedMs']}ms</span>
                    </div>
                    <span class="expand-icon">▼</span>
                </div>
                <div class="endpoint-details">
                    <div class="details-content">
                        {req_body_html}
                        <div class="detail-section">
                            <h4>📥 Yanıt (Response) — HTTP {r['statusCode']}</h4>
                            <div class="code-block">{escape_html(r['responseBody'])}</div>
                        </div>
                        {error_html}
                    </div>
                </div>
            </div>
"""
        
        html += "        </div>\n"
    
    html += f"""
        <div class="footer">
            <p>OkeyAdvert API Test Raporu • Oluşturulma: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} • Toplam {total} endpoint test edildi</p>
        </div>
    </div>
    
    <script>
        function toggleEndpoint(header) {{
            const endpoint = header.parentElement;
            endpoint.classList.toggle('expanded');
        }}
        
        function filterResults(filter) {{
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            document.querySelectorAll('.endpoint').forEach(el => {{
                const status = el.getAttribute('data-status');
                if (filter === 'all') {{
                    el.style.display = '';
                }} else if (filter === 'success') {{
                    el.style.display = status === 'success' ? '' : 'none';
                }} else if (filter === 'fail') {{
                    el.style.display = status === 'fail' ? '' : 'none';
                }}
            }});
        }}
        
        // Auto-expand failed endpoints
        document.querySelectorAll('.endpoint[data-status="fail"]').forEach(el => {{
            el.classList.add('expanded');
        }});
    </script>
</body>
</html>
"""
    
    return html


def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;"))

def analyze_error(result):
    """Analyze error and return (reason, suggestion)"""
    sc = result['statusCode']
    body = result['responseBody'].lower() if result['responseBody'] else ""
    endpoint = result['endpoint']
    method = result['method']
    
    if sc == 0:
        return ("Sunucuya bağlanılamadı. Sunucu kapalı veya ağ bağlantısı yok.",
                "Sunucunun çalıştığından emin olun. `curl -v {BASE_URL}` ile bağlantıyı test edin.")
    
    if sc == 401:
        return ("Kimlik doğrulama başarısız. Token geçersiz veya eksik.",
                "Authorization header'da geçerli bir Bearer token gönderildiğinden emin olun. Login endpoint'inden yeni token alın.")
    
    if sc == 403:
        return ("Yetkilendirme hatası. Bu işlem için yeterli yetkiniz yok.",
                "Kullanıcının bu endpoint'e erişim yetkisi olduğundan emin olun. Rol/permission kontrollerini kontrol edin.")
    
    if sc == 404:
        if "not found" in body or "bulunamadı" in body:
            return ("İstenen kaynak bulunamadı. ID geçersiz veya kayıt mevcut değil.",
                    "Geçerli bir ID ile tekrar deneyin. Önce ilgili GET/LIST endpoint'ini çağırarak mevcut kayıtları kontrol edin.")
        return ("Endpoint bulunamadı. Route tanımı eksik veya yanlış.",
                "API route tanımlarını kontrol edin. URL'nin doğru olduğundan emin olun.")
    
    if sc == 400:
        if "validation" in body or "required" in body:
            return ("İstek doğrulama hatası. Gönderilen veri format/içerik olarak hatalı.",
                    "Request body'deki alanların Swagger şemasına uygun olduğundan emin olun. Zorunlu alanları kontrol edin.")
        if "already" in body or "exists" in body or "zaten" in body:
            return ("Kaynak zaten mevcut. Tekrarlanan kayıt oluşturma girişimi.",
                    "Bu kaynak daha önce oluşturulmuş olabilir. Önce mevcut kaydı kontrol edin.")
        if "phone" in body:
            return ("Telefon numarası ile ilgili doğrulama hatası.",
                    "Telefon numarasının doğru formatta (+905XXXXXXXXX) olduğundan emin olun.")
        return ("İstek format hatası. Gönderilen veriler geçersiz.",
                f"Request body'nin Swagger şemasına uygunluğunu kontrol edin. Body: {(result.get('requestBody') or 'N/A')[:100]}")
    
    if sc == 405:
        return ("HTTP method desteklenmiyor.",
                f"Bu endpoint {method} metodunu desteklemiyor olabilir. Swagger'daki method tanımını kontrol edin.")
    
    if sc == 409:
        return ("Çakışma hatası. Kaynak mevcut durumla çelişen bir işlem.",
                "Kaynağın mevcut durumunu kontrol edin. Örneğin zaten kabul edilmiş bir başvuruyu tekrar kabul etmeye çalışıyor olabilirsiniz.")
    
    if sc == 415:
        return ("Desteklenmeyen medya tipi. Content-Type header'ı yanlış.",
                "Content-Type: application/json header'ı gönderdiğinizden emin olun.")
    
    if sc == 422:
        return ("İş kuralı hatası. İstek sözdizimi doğru ama iş mantığı kurallarına aykırı.",
                "İş kurallarını kontrol edin. Örneğin kendi ilanınıza başvuramazsınız gibi kısıtlamalar olabilir.")
    
    if 500 <= sc <= 599:
        return ("Sunucu hatası (Internal Server Error). Backend'te beklenmeyen bir hata oluştu.",
                "Backend loglarını kontrol edin. Bu muhtemelen bir bug veya eksik konfigürasyon. Response body'deki hata mesajını backend ekibiyle paylaşın.")
    
    return (f"HTTP {sc} hatası alındı.", 
            "Response body'yi inceleyerek hatanın detayını anlayın ve backend ekibiyle paylaşın.")


def main():
    print("🚀 OkeyAdvert API Test Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run all tests in order
    test_health()
    test_auth()
    test_listings()
    test_applications()
    test_listings_cleanup()  # Cancel/delete listing after applications have used it
    test_notifications()
    test_payments()
    test_ratings()
    test_rooms()
    test_subscriptions()
    
    # Summary
    total = len(RESULTS)
    success = sum(1 for r in RESULTS if r['isSuccess'])
    failed = total - success
    
    print("\n" + "=" * 60)
    print(f"📊 ÖZET: {total} endpoint test edildi")
    print(f"   ✅ Başarılı: {success}")
    print(f"   ❌ Başarısız: {failed}")
    print(f"   📈 Oran: {round(success/total*100)}%")
    print("=" * 60)
    
    # Generate HTML report
    html = generate_html_report()
    report_path = "/Users/abdulsamed.demirtop/okey_match/api_test/api_test_report.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n📄 HTML Rapor: {report_path}")
    
    # Also save JSON results
    json_path = "/Users/abdulsamed.demirtop/okey_match/api_test/results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'testDate': datetime.now().isoformat(),
            'baseUrl': BASE_URL,
            'summary': {'total': total, 'success': success, 'failed': failed},
            'results': RESULTS
        }, f, indent=2, ensure_ascii=False)
    print(f"📊 JSON Sonuçlar: {json_path}")


if __name__ == "__main__":
    main()

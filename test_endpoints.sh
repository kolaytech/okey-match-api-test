#!/bin/bash
# OkeyAdvert API Endpoint Test Script
# Base URL
BASE_URL="http://94.138.209.132:8080"
RESULTS_FILE="/Users/abdulsamed.demirtop/okey_match/api_test/results.json"

# Initialize results array
echo '{"results": [], "testDate": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}' > "$RESULTS_FILE"

# Helper function to add result
add_result() {
    local category="$1"
    local method="$2"
    local endpoint="$3"
    local status_code="$4"
    local response_body="$5"
    local description="$6"
    local requires_auth="$7"
    local request_body="$8"
    
    # Escape special characters for JSON
    response_body=$(echo "$response_body" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
    request_body=$(echo "$request_body" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
    
    python3 -c "
import json
with open('$RESULTS_FILE', 'r') as f:
    data = json.load(f)
data['results'].append({
    'category': '$category',
    'method': '$method',
    'endpoint': '$endpoint',
    'statusCode': $status_code,
    'responseBody': $response_body,
    'description': '$description',
    'requiresAuth': '$requires_auth' == 'true',
    'requestBody': $request_body
})
with open('$RESULTS_FILE', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
"
}

echo "🔍 Starting OkeyAdvert API Endpoint Tests..."
echo "================================================"

# ============================================
# 1. AUTH ENDPOINTS (No Auth Required)
# ============================================
echo ""
echo "📌 Testing AUTH Endpoints..."

# 1.1 Register
echo "  → POST /api/Auth/register"
REQ_BODY='{"phone":"+905551234567","password":"Test123456!","fullName":"Test User","email":"test@okeymatch.com"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Auth/register" \
  -H "Content-Type: application/json" \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Auth" "POST" "/api/Auth/register" "$HTTP_CODE" "$BODY" "Yeni kullanıcı kaydı" "false" "$REQ_BODY"

# 1.2 Login
echo "  → POST /api/Auth/login"
REQ_BODY='{"phone":"+905551234567","password":"Test123456!"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Auth/login" \
  -H "Content-Type: application/json" \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Auth" "POST" "/api/Auth/login" "$HTTP_CODE" "$BODY" "Kullanıcı girişi" "false" "$REQ_BODY"

# Extract tokens if login successful
ACCESS_TOKEN=""
REFRESH_TOKEN=""
if [ "$HTTP_CODE" -eq 200 ] 2>/dev/null; then
    ACCESS_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('accessToken',''))" 2>/dev/null)
    REFRESH_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('refreshToken',''))" 2>/dev/null)
    echo "    ✅ Token alındı!"
else
    echo "    ⚠️  Login başarısız, farklı test kullanıcı bilgileriyle tekrar deneniyor..."
    # Try register first then login
    REQ_BODY_REG='{"phone":"+905559876543","password":"Test123456!","fullName":"API Test User","email":"apitest@okeymatch.com"}'
    RESPONSE_REG=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Auth/register" \
      -H "Content-Type: application/json" \
      -d "$REQ_BODY_REG" 2>&1)
    REG_CODE=$(echo "$RESPONSE_REG" | tail -1)
    REG_BODY=$(echo "$RESPONSE_REG" | head -n -1)
    
    if [ "$REG_CODE" -eq 200 ] 2>/dev/null; then
        ACCESS_TOKEN=$(echo "$REG_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('accessToken',''))" 2>/dev/null)
        REFRESH_TOKEN=$(echo "$REG_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('refreshToken',''))" 2>/dev/null)
        echo "    ✅ Register ile token alındı!"
    fi
fi

# 1.3 Send OTP  
echo "  → POST /api/Auth/send-otp"
REQ_BODY='{"phone":"+905551234567"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Auth/send-otp" \
  -H "Content-Type: application/json" \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Auth" "POST" "/api/Auth/send-otp" "$HTTP_CODE" "$BODY" "OTP gönderme" "false" "$REQ_BODY"

# 1.4 Verify OTP
echo "  → POST /api/Auth/verify-otp"
REQ_BODY='{"phone":"+905551234567","code":"123456"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Auth" "POST" "/api/Auth/verify-otp" "$HTTP_CODE" "$BODY" "OTP doğrulama" "false" "$REQ_BODY"

# 1.5 Refresh Token
echo "  → POST /api/Auth/refresh"
if [ -n "$REFRESH_TOKEN" ]; then
    REQ_BODY="{\"refreshToken\":\"$REFRESH_TOKEN\"}"
else
    REQ_BODY='{"refreshToken":"dummy-refresh-token"}'
fi
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Auth/refresh" \
  -H "Content-Type: application/json" \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Auth" "POST" "/api/Auth/refresh" "$HTTP_CODE" "$BODY" "Token yenileme" "false" "$REQ_BODY"

# ============================================
# 2. LISTINGS ENDPOINTS
# ============================================
echo ""
echo "📌 Testing LISTINGS Endpoints..."

AUTH_HEADER=""
if [ -n "$ACCESS_TOKEN" ]; then
    AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
fi

# 2.1 Get Listings (no auth might work)
echo "  → GET /api/Listings"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Listings?Page=1&PageSize=5" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Listings" "GET" "/api/Listings" "$HTTP_CODE" "$BODY" "Tüm ilanları listele" "true" ""

# 2.2 Get Listings with filters
echo "  → GET /api/Listings (filtered)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Listings?City=Istanbul&Level=beginner&Page=1&PageSize=5" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Listings" "GET" "/api/Listings?City=Istanbul&Level=beginner" "$HTTP_CODE" "$BODY" "Filtrelenmiş ilan listesi" "true" ""

# 2.3 Create Listing
echo "  → POST /api/Listings"
REQ_BODY='{"title":"Test İlanı","description":"Bu bir test ilanıdır","city":"Istanbul","district":"Kadıkoy","lat":40.9833,"lng":29.0167,"placeName":"Test Mekanı","dateTime":"2026-04-10T14:00:00Z","playerNeeded":3,"level":"mid","minAge":18,"maxAge":50}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Listings" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Listings" "POST" "/api/Listings" "$HTTP_CODE" "$BODY" "Yeni ilan oluştur" "true" "$REQ_BODY"

# Extract listing ID if created
LISTING_ID=""
if [ "$HTTP_CODE" -eq 200 ] 2>/dev/null; then
    LISTING_ID=$(echo "$BODY" | tr -d '"' | tr -d ' ')
    echo "    ✅ Listing ID: $LISTING_ID"
fi

# 2.4 Get Listing by ID
echo "  → GET /api/Listings/{id}"
TEST_LISTING_ID="${LISTING_ID:-00000000-0000-0000-0000-000000000001}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Listings/$TEST_LISTING_ID" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Listings" "GET" "/api/Listings/{id}" "$HTTP_CODE" "$BODY" "ID ile ilan detayı getir" "true" ""

# 2.5 Update Listing
echo "  → PUT /api/Listings/{id}"
REQ_BODY='{"title":"Güncellenmiş Test İlanı","description":"Güncellenmiş açıklama","playerNeeded":2,"level":"advanced"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/Listings/$TEST_LISTING_ID" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Listings" "PUT" "/api/Listings/{id}" "$HTTP_CODE" "$BODY" "İlan güncelle" "true" "$REQ_BODY"

# 2.6 Cancel Listing
echo "  → PATCH /api/Listings/{id}/cancel"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/Listings/$TEST_LISTING_ID/cancel" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Listings" "PATCH" "/api/Listings/{id}/cancel" "$HTTP_CODE" "$BODY" "İlan iptal et" "true" ""

# 2.7 Delete Listing
echo "  → DELETE /api/Listings/{id}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/Listings/$TEST_LISTING_ID" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Listings" "DELETE" "/api/Listings/{id}" "$HTTP_CODE" "$BODY" "İlan sil" "true" ""

# ============================================
# 3. APPLICATIONS ENDPOINTS
# ============================================
echo ""
echo "📌 Testing APPLICATIONS Endpoints..."

# 3.1 Apply to Listing
echo "  → POST /api/Applications/apply/{listingId}"
REQ_BODY='{"joinedAsGroupCount":1,"message":"Ben de oynamak istiyorum!"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Applications/apply/$TEST_LISTING_ID" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Applications" "POST" "/api/Applications/apply/{listingId}" "$HTTP_CODE" "$BODY" "İlana başvuru yap" "true" "$REQ_BODY"

APP_ID=""
if [ "$HTTP_CODE" -eq 200 ] 2>/dev/null; then
    APP_ID=$(echo "$BODY" | tr -d '"' | tr -d ' ')
    echo "    ✅ Application ID: $APP_ID"
fi

# 3.2 Get Applications for Listing
echo "  → GET /api/Applications/listing/{listingId}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Applications/listing/$TEST_LISTING_ID" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Applications" "GET" "/api/Applications/listing/{listingId}" "$HTTP_CODE" "$BODY" "İlanın başvurularını listele" "true" ""

# 3.3 Accept Application
echo "  → POST /api/Applications/{applicationId}/accept"
TEST_APP_ID="${APP_ID:-00000000-0000-0000-0000-000000000001}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Applications/$TEST_APP_ID/accept" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Applications" "POST" "/api/Applications/{applicationId}/accept" "$HTTP_CODE" "$BODY" "Başvuruyu kabul et" "true" ""

# 3.4 Reject Application
echo "  → POST /api/Applications/{applicationId}/reject"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Applications/$TEST_APP_ID/reject" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Applications" "POST" "/api/Applications/{applicationId}/reject" "$HTTP_CODE" "$BODY" "Başvuruyu reddet" "true" ""

# 3.5 Delete Application
echo "  → DELETE /api/Applications/{applicationId}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/Applications/$TEST_APP_ID" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Applications" "DELETE" "/api/Applications/{applicationId}" "$HTTP_CODE" "$BODY" "Başvuruyu sil" "true" ""

# ============================================
# 4. NOTIFICATIONS ENDPOINTS
# ============================================
echo ""
echo "📌 Testing NOTIFICATIONS Endpoints..."

# 4.1 Get Notifications
echo "  → GET /api/Notifications"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Notifications?page=1&pageSize=10" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Notifications" "GET" "/api/Notifications" "$HTTP_CODE" "$BODY" "Bildirimleri listele" "true" ""

# 4.2 Register Device Token
echo "  → POST /api/Notifications/device-token"
REQ_BODY='{"token":"test-fcm-token-12345","platform":"android"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Notifications/device-token" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Notifications" "POST" "/api/Notifications/device-token" "$HTTP_CODE" "$BODY" "Cihaz token kaydet" "true" "$REQ_BODY"

# 4.3 Unregister Device Token
echo "  → DELETE /api/Notifications/device-token"
REQ_BODY='{"token":"test-fcm-token-12345"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/Notifications/device-token" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Notifications" "DELETE" "/api/Notifications/device-token" "$HTTP_CODE" "$BODY" "Cihaz token kaldır" "true" "$REQ_BODY"

# 4.4 Mark Notifications Read
echo "  → POST /api/Notifications/mark-read"
REQ_BODY='{"notificationIds":["00000000-0000-0000-0000-000000000001"]}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Notifications/mark-read" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Notifications" "POST" "/api/Notifications/mark-read" "$HTTP_CODE" "$BODY" "Bildirimleri okundu işaretle" "true" "$REQ_BODY"

# ============================================
# 5. PAYMENTS ENDPOINTS
# ============================================
echo ""
echo "📌 Testing PAYMENTS Endpoints..."

# 5.1 Process Payment
echo "  → POST /api/Payments/process"
REQ_BODY='{"amount":99.99,"currency":"TRY","paymentMethod":"credit_card","description":"Test payment","require3DSecure":false,"cardHolderName":"Test User","cardNumber":"4111111111111111","expiryMonth":"12","expiryYear":"2027","cvv":"123"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Payments/process" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Payments" "POST" "/api/Payments/process" "$HTTP_CODE" "$BODY" "Ödeme işlemi başlat" "true" "$REQ_BODY"

# 5.2 3D Secure Callback
echo "  → POST /api/Payments/3dsecure/callback"
REQ_BODY='{"transactionId":"test-transaction-id","success":true,"threeDSecureResult":"OK"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Payments/3dsecure/callback" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Payments" "POST" "/api/Payments/3dsecure/callback" "$HTTP_CODE" "$BODY" "3D Secure callback" "true" "$REQ_BODY"

# 5.3 Mock 3D Secure Verify
echo "  → GET /api/Payments/mock/3dsecure/verify/{transactionId}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Payments/mock/3dsecure/verify/test-transaction-id" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Payments" "GET" "/api/Payments/mock/3dsecure/verify/{transactionId}" "$HTTP_CODE" "$BODY" "3D Secure doğrulama (mock)" "false" ""

# ============================================
# 6. RATINGS ENDPOINTS
# ============================================
echo ""
echo "📌 Testing RATINGS Endpoints..."

# 6.1 Create Rating
echo "  → POST /api/Ratings"
REQ_BODY='{"roomId":"00000000-0000-0000-0000-000000000001","toUserId":"00000000-0000-0000-0000-000000000002","score":5,"comment":"Harika bir oyuncu!"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Ratings" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Ratings" "POST" "/api/Ratings" "$HTTP_CODE" "$BODY" "Değerlendirme oluştur" "true" "$REQ_BODY"

# 6.2 Get Ratings for User
echo "  → GET /api/Ratings/user/{userId}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Ratings/user/00000000-0000-0000-0000-000000000001" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Ratings" "GET" "/api/Ratings/user/{userId}" "$HTTP_CODE" "$BODY" "Kullanıcı değerlendirmelerini getir" "true" ""

# ============================================
# 7. ROOMS ENDPOINTS
# ============================================
echo ""
echo "📌 Testing ROOMS Endpoints..."

# 7.1 Get Room
echo "  → GET /api/Rooms/{id}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Rooms/00000000-0000-0000-0000-000000000001" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Rooms" "GET" "/api/Rooms/{id}" "$HTTP_CODE" "$BODY" "Oda detayı getir" "true" ""

# 7.2 Confirm Attendance
echo "  → POST /api/Rooms/{id}/confirm-attendance"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Rooms/00000000-0000-0000-0000-000000000001/confirm-attendance" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Rooms" "POST" "/api/Rooms/{id}/confirm-attendance" "$HTTP_CODE" "$BODY" "Katılım onayla" "true" ""

# ============================================
# 8. SUBSCRIPTIONS ENDPOINTS
# ============================================
echo ""
echo "📌 Testing SUBSCRIPTIONS Endpoints..."

# 8.1 Get Subscription Plans
echo "  → GET /api/Subscriptions/plans"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Subscriptions/plans" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Subscriptions" "GET" "/api/Subscriptions/plans" "$HTTP_CODE" "$BODY" "Abonelik planlarını listele" "true" ""

# 8.2 Get My Subscription
echo "  → GET /api/Subscriptions/me"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/Subscriptions/me" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Subscriptions" "GET" "/api/Subscriptions/me" "$HTTP_CODE" "$BODY" "Mevcut aboneliğimi getir" "true" ""

# 8.3 Create Subscription
echo "  → POST /api/Subscriptions"
REQ_BODY='{"planId":"00000000-0000-0000-0000-000000000001","paymentReceipt":"test-receipt","platform":"ios"}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Subscriptions" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Subscriptions" "POST" "/api/Subscriptions" "$HTTP_CODE" "$BODY" "Abonelik oluştur" "true" "$REQ_BODY"

# 8.4 Cancel Subscription
echo "  → POST /api/Subscriptions/me/cancel"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Subscriptions/me/cancel" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Subscriptions" "POST" "/api/Subscriptions/me/cancel" "$HTTP_CODE" "$BODY" "Aboneliği iptal et" "true" ""

# 8.5 Boost Listing
echo "  → POST /api/Subscriptions/boost/{listingId}"
REQ_BODY='{"durationHours":24}'
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/Subscriptions/boost/$TEST_LISTING_ID" \
  -H "Content-Type: application/json" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$REQ_BODY" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)
add_result "Subscriptions" "POST" "/api/Subscriptions/boost/{listingId}" "$HTTP_CODE" "$BODY" "İlanı öne çıkar (boost)" "true" "$REQ_BODY"

# ============================================
# ALSO TEST: Swagger endpoint & server health
# ============================================
echo ""
echo "📌 Testing SERVER HEALTH..."

echo "  → GET /swagger/v1/swagger.json"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/swagger/v1/swagger.json" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
add_result "Health" "GET" "/swagger/v1/swagger.json" "$HTTP_CODE" "Swagger JSON available" "Swagger API dökümantasyonu" "false" ""

echo ""
echo "================================================"
echo "✅ Test tamamlandı! Sonuçlar: $RESULTS_FILE"
echo "================================================"

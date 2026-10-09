import sys
import json
import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8000"

async def run_tests():
    print("=" * 60)
    print("RUNNING LUMEN FULL SYSTEM INTEGRATION TEST SUITE")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=40.0) as client:
        
        # 1. Health check & Frontend static files
        print("\n[TEST 1] Server Health & Frontend Assets...")
        r = await client.get("/api/health")
        assert r.status_code == 200, f"Health failed: {r.text}"
        print("  ✓ /api/health returned 200 OK")

        r = await client.get("/")
        assert r.status_code == 200, "Frontend index.html failed to load"
        assert "Lumen" in r.text
        assert "Ready when you are." in r.text
        assert "/assets/upi_qr.jpg" in r.text
        print("  ✓ Frontend HTML served with ChatGPT-inspired layout and UPI QR asset")

        r = await client.get("/assets/upi_qr.jpg")
        assert r.status_code == 200, f"UPI QR asset not reachable: {r.status_code}"
        assert len(r.content) > 10000, "UPI QR asset is too small or missing"
        print(f"  ✓ UPI QR asset reachable and verified ({len(r.content)} bytes)")

        # 2. Authentication: User A & User B
        print("\n[TEST 2] Authentication Workflows...")
        email_a = f"test_user_a_{asyncio.get_event_loop().time()}@example.com"
        email_b = f"test_user_b_{asyncio.get_event_loop().time()}@example.com"
        pwd = "TestPassword123!"

        # Register User A
        r = await client.post("/api/auth/register", json={
            "display_name": "Alice Turing",
            "email": email_a,
            "password": pwd,
            "confirm_password": pwd
        })
        assert r.status_code == 200, f"Registration A failed: {r.text}"
        data_a = r.json()
        token_a = data_a["token"]
        user_a = data_a["user"]
        assert user_a["plan"] == "free", "New user should start on Free plan"
        print(f"  ✓ Registered User A ({email_a}) with default Free plan")

        # Register User B
        r = await client.post("/api/auth/register", json={
            "display_name": "Bob Lovelace",
            "email": email_b,
            "password": pwd,
            "confirm_password": pwd
        })
        assert r.status_code == 200, f"Registration B failed: {r.text}"
        data_b = r.json()
        token_b = data_b["token"]
        user_b = data_b["user"]
        print(f"  ✓ Registered User B ({email_b}) with default Free plan")

        # Test login User A
        r = await client.post("/api/auth/login", json={"email": email_a, "password": pwd})
        assert r.status_code == 200, f"Login failed: {r.text}"
        token_a_new = r.json()["token"]
        print("  ✓ User A logged in successfully")

        # Verify Session /me
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a_new}"})
        assert r.status_code == 200
        assert r.json()["user"]["email"] == email_a
        print("  ✓ Session token validated via /api/auth/me")

        # 3. Chat and Conversation Persistence
        print("\n[TEST 3] AI Chat & Persistent Chat History (User A)...")
        r = await client.post("/api/chat", headers={"Authorization": f"Bearer {token_a_new}"}, json={
            "message": "Hello Lumen, explain what a binary search tree is in 2 short bullet points.",
            "language": "en"
        })
        assert r.status_code == 200, f"Chat failed: {r.text}"
        chat_res = r.json()
        assert "message" in chat_res and len(chat_res["message"]["text"]) > 10
        print("  ✓ Chat response received from Gemini:")
        print(f"    Mode: {chat_res.get('mode')}")
        print(f"    Snippet: {chat_res['message']['text'][:80]}...")

        # Verify conversation in database
        r = await client.get("/api/conversations", headers={"Authorization": f"Bearer {token_a_new}"})
        assert r.status_code == 200
        convs_a = r.json()["conversations"]
        assert len(convs_a) >= 1, "User A should have at least 1 saved conversation"
        conv_id_a = convs_a[0]["id"]
        print(f"  ✓ Saved conversation found in DB: '{convs_a[0]['title']}' (ID: {conv_id_a})")

        # Verify messages inside conversation
        r = await client.get(f"/api/conversations/{conv_id_a}", headers={"Authorization": f"Bearer {token_a_new}"})
        assert r.status_code == 200
        conv_detail = r.json()
        msgs = conv_detail["messages"]
        assert len(msgs) >= 2, f"Expected user and assistant messages, got {len(msgs)}"
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        print("  ✓ Database persisted user prompt and assistant response")

        # 4. Multi-tenant Privacy Isolation
        print("\n[TEST 4] User Privacy & Ownership Isolation...")
        # User B should NOT be able to view User A's conversation
        r = await client.get(f"/api/conversations/{conv_id_a}", headers={"Authorization": f"Bearer {token_b}"})
        assert r.status_code == 404, f"Security Breach: User B could access User A conversation! Code: {r.status_code}"
        print("  ✓ Access denied for User B accessing User A conversation (Isolated!)")

        # User B should NOT be able to delete User A's conversation
        r = await client.delete(f"/api/conversations/{conv_id_a}", headers={"Authorization": f"Bearer {token_b}"})
        assert r.status_code == 404, "Security Breach: User B could delete User A conversation!"
        print("  ✓ Deletion denied for unauthorized user")

        # Rename conversation by User A
        r = await client.patch(f"/api/conversations/{conv_id_a}", headers={"Authorization": f"Bearer {token_a_new}"}, json={
            "title": "Binary Search Trees Discussion"
        })
        assert r.status_code == 200
        print("  ✓ Conversation renamed successfully")

        # 5. Plus Payment & UPI QR Workflow
        print("\n[TEST 5] UPI QR ₹699 Plus Payment & Admin Verification Flow...")
        # Check User A plan initially
        r = await client.get("/api/billing/plan", headers={"Authorization": f"Bearer {token_a_new}"})
        assert r.status_code == 200
        assert r.json()["plan"] == "free"

        # User A submits payment reference
        utr_test = "UTR988910023456"
        r = await client.post("/api/billing/submit-payment", headers={"Authorization": f"Bearer {token_a_new}"}, data={
            "utr_number": utr_test,
            "amount": "699.00"
        })
        assert r.status_code == 200, f"Submit payment failed: {r.text}"
        req_info = r.json()["payment_request"]
        req_id = req_info["id"]
        assert req_info["status"] == "pending"
        print(f"  ✓ Payment verification submitted (UTR: {utr_test}). Status: PENDING")

        # Verify User A is STILL Free while pending!
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a_new}"})
        assert r.json()["user"]["plan"] == "free", "User must NOT be upgraded before admin approval!"
        print("  ✓ Verified: User remains Free while payment is pending")

        # Unauthorized user cannot access Admin portal
        r = await client.get("/api/billing/admin/requests", headers={"Authorization": f"Bearer {token_a_new}"})
        assert r.status_code == 403, "Non-admin user accessed admin portal!"
        print("  ✓ Server authorization enforced: Non-admin gets 403 Forbidden")

        # Admin logs in
        r = await client.post("/api/auth/login", json={
            "email": "admin@lumen.ai",
            "password": "Admin@Lumen2026!"
        })
        assert r.status_code == 200, f"Admin login failed: {r.text}"
        admin_token = r.json()["token"]
        print("  ✓ Admin logged in successfully")

        # Admin lists pending requests
        r = await client.get("/api/billing/admin/requests", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        requests_list = r.json()["requests"]
        assert any(x["id"] == req_id for x in requests_list)
        print("  ✓ Admin viewed pending payment requests")

        # Admin approves payment
        r = await client.post("/api/billing/admin/review", headers={"Authorization": f"Bearer {admin_token}"}, json={
            "request_id": req_id,
            "status": "approved",
            "admin_notes": "Verified ₹699 credited to UPI"
        })
        assert r.status_code == 200
        print("  ✓ Admin approved payment request")

        # Verify User A is NOW permanently upgraded to Plus!
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a_new}"})
        user_a_upgraded = r.json()["user"]
        assert user_a_upgraded["plan"] == "plus", f"Expected Plus plan, got {user_a_upgraded['plan']}"
        print("  ✓ Verified: User A now has permanent active LUMEN PLUS entitlement!")

        # 6. AI Capabilities: Multilingual, Medical Emergency, Health Triage
        print("\n[TEST 6] AI Tutor Multilingual & Safety Intelligence...")
        
        # Test 6a: Emergency Medical Triage
        r = await client.post("/api/chat", headers={"Authorization": f"Bearer {token_a_new}"}, json={
            "message": "I have severe crushing chest pain that radiates to my left jaw and shortness of breath.",
            "language": "auto"
        })
        assert r.status_code == 200
        emerg_res = r.json()
        assert emerg_res["safety"]["urgent"] == True or "emergency" in emerg_res.get("mode", ""), "Emergency safety level not triggered!"
        print("  ✓ Severe symptom safely triggered emergency triage & urgent guidance")

        # Test 6b: Hinglish / Multilingual Tutoring
        r = await client.post("/api/chat", headers={"Authorization": f"Bearer {token_a_new}"}, json={
            "message": "Mujhe python mein list comprehension ka concept simple shabdon mein samjhaiye.",
            "language": "Hinglish"
        })
        assert r.status_code == 200
        hinglish_res = r.json()
        assert len(hinglish_res["message"]["text"]) > 20
        print("  ✓ Multilingual (Hinglish) educational tutoring responded successfully")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())

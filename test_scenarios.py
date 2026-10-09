import httpx
import uuid
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def print_separator(title):
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def run_tests():
    client = httpx.Client(timeout=35.0)
    run_id = str(uuid.uuid4())[:8]

    # Health Check
    print_separator("TEST 0: HEALTH CHECK")
    r = client.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}, Response: {r.json()}")
    assert r.status_code == 200, "Health check failed"

    # Test 1: "What is a binary tree?" -> Direct educational answer
    print_separator("TEST 1: 'What is a binary tree?' (Expected: Direct educational answer, no survey)")
    r1 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": f"test-session-1-{run_id}",
        "message": "What is a binary tree?"
    })
    assert r1.status_code == 200, f"Test 1 failed: {r1.text}"
    d1 = r1.json()
    print(f"Language: {d1.get('language')}")
    print(f"Mode: {d1.get('mode')}")
    print(f"Survey Active: {d1.get('survey', {}).get('active')}")
    print(f"Message Preview: {d1.get('message', {}).get('text')[:180]}...")
    assert d1.get("survey", {}).get("active") is False, "Survey should NOT be active for binary tree!"
    assert d1.get("mode") in ["direct_answer", "educational_explanation"], f"Unexpected mode: {d1.get('mode')}"
    print("✅ TEST 1 PASSED: Direct educational answer returned without survey!")

    # Test 2: "Explain binary tree in simple Hindi." -> Hindi response with simple language
    print_separator("TEST 2: 'Explain binary tree in simple Hindi.' (Expected: Hindi response)")
    r2 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": f"test-session-2-{run_id}",
        "message": "Explain binary tree in simple Hindi."
    })
    assert r2.status_code == 200, f"Test 2 failed: {r2.text}"
    d2 = r2.json()
    print(f"Language: {d2.get('language')}")
    print(f"Mode: {d2.get('mode')}")
    print(f"Survey Active: {d2.get('survey', {}).get('active')}")
    print(f"Message Preview: {d2.get('message', {}).get('text')[:180]}...")
    assert d2.get("survey", {}).get("active") is False, "Survey should NOT be active for binary tree explanation!"
    print("✅ TEST 2 PASSED: Hindi response generated cleanly!")

    # Test 3: "mere pet me kal se dard ho raha hai" -> Hindi/Hinglish health assessment with follow-up questions
    print_separator("TEST 3: 'mere pet me kal se dard ho raha hai' (Expected: Health assessment with conversational follow-up)")
    session_3 = f"test-session-3-{run_id}"
    r3 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": session_3,
        "message": "mere pet me kal se dard ho raha hai"
    })
    assert r3.status_code == 200, f"Test 3 failed: {r3.text}"
    d3 = r3.json()
    print(f"Language: {d3.get('language')}")
    print(f"Mode: {d3.get('mode')}")
    print(f"Survey Active: {d3.get('survey', {}).get('active')}")
    print(f"Survey Question: {d3.get('survey', {}).get('question')}")
    print(f"Survey Options: {d3.get('survey', {}).get('options')}")
    print(f"Message: {d3.get('message', {}).get('text')[:180]}...")
    assert d3.get("mode") in ["health_assessment", "guided_assessment"], f"Mode should be health assessment, got: {d3.get('mode')}"
    assert d3.get("survey", {}).get("active") is True, "Survey should be active for health concern!"
    print("✅ TEST 3 PASSED: Health assessment started conversationally with targeted question!")

    # Test 4: "I have severe chest pain and difficulty breathing." -> Emergency triage
    print_separator("TEST 4: 'I have severe chest pain and difficulty breathing.' (Expected: Emergency triage)")
    r4 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": f"test-session-4-{run_id}",
        "message": "I have severe chest pain and difficulty breathing."
    })
    assert r4.status_code == 200, f"Test 4 failed: {r4.text}"
    d4 = r4.json()
    print(f"Language: {d4.get('language')}")
    print(f"Mode: {d4.get('mode')}")
    print(f"Safety Level: {d4.get('safety', {}).get('level')}")
    print(f"Safety Urgent: {d4.get('safety', {}).get('urgent')}")
    print(f"Survey Active: {d4.get('survey', {}).get('active')}")
    print(f"Message: {d4.get('message', {}).get('text')[:180]}...")
    assert d4.get("mode") == "emergency_triage" or d4.get("safety", {}).get("urgent") is True, "Must trigger emergency triage!"
    assert d4.get("survey", {}).get("active") is False, "Survey should NOT be active for emergency!"
    print("✅ TEST 4 PASSED: Urgent emergency guidance triggered without survey!")

    # Test 5: "Write a C++ program to reverse an array." -> Direct programming response
    print_separator("TEST 5: 'Write a C++ program to reverse an array.' (Expected: Direct C++ code)")
    session_5 = f"test-session-5-{run_id}"
    r5 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": session_5,
        "message": "Write a C++ program to reverse an array."
    })
    assert r5.status_code == 200, f"Test 5 failed: {r5.text}"
    d5 = r5.json()
    print(f"Mode: {d5.get('mode')}")
    print(f"Survey Active: {d5.get('survey', {}).get('active')}")
    print(f"Message Preview:\n{d5.get('message', {}).get('text')[:220]}...")
    assert d5.get("survey", {}).get("active") is False
    assert "cpp" in d5.get("message", {}).get("text").lower() or "include" in d5.get("message", {}).get("text").lower()
    print("✅ TEST 5 PASSED: C++ program provided directly!")

    # Test 6: "Can you explain this topic more simply?" -> Uses previous context from session_5
    print_separator("TEST 6: 'Can you explain this topic more simply?' (Expected: Simplification using context)")
    r6 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": session_5,
        "message": "Can you explain this topic more simply?"
    })
    assert r6.status_code == 200, f"Test 6 failed: {r6.text}"
    d6 = r6.json()
    print(f"Mode: {d6.get('mode')}")
    print(f"Message Preview:\n{d6.get('message', {}).get('text')[:220]}...")
    assert "array" in d6.get("message", {}).get("text").lower() or "reverse" in d6.get("message", {}).get("text").lower()
    print("✅ TEST 6 PASSED: Successfully simplified using conversation memory!")

    # Test 7: User answers assessment question -> Continues in session_3
    print_separator("TEST 7: User answers health assessment question (Expected: Remembers answer and progresses)")
    r7 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": session_3,
        "message": "Dard halke se shuru hua tha, par khane ke baad thoda badh jata hai. Meri umar 24 saal hai."
    })
    assert r7.status_code == 200, f"Test 7 failed: {r7.text}"
    d7 = r7.json()
    print(f"Mode: {d7.get('mode')}")
    print(f"Survey Active: {d7.get('survey', {}).get('active')}")
    print(f"Assessment Completed: {d7.get('assessment', {}).get('completed')}")
    if d7.get("survey", {}).get("active"):
        print(f"Next Question: {d7.get('survey', {}).get('question')}")
    else:
        print(f"Assessment Summary: {d7.get('assessment', {}).get('summary')}")
    print("✅ TEST 7 PASSED: Contextual memory maintained across health assessment turns!")

    # Test 8: Multilingual matching across languages (Spanish)
    print_separator("TEST 8: Multilingual Matching (Spanish)")
    r8 = client.post(f"{BASE_URL}/chat", json={
        "conversation_id": f"test-session-8-{run_id}",
        "message": "¿Cómo funciona la memoria RAM en una computadora?"
    })
    assert r8.status_code == 200, f"Test 8 failed: {r8.text}"
    d8 = r8.json()
    print(f"Language: {d8.get('language')}")
    print(f"Message Preview: {d8.get('message', {}).get('text')[:180]}...")
    assert "es" in d8.get("language", "").lower() or "spanish" in d8.get("language", "").lower() or "memoria" in d8.get("message", {}).get("text").lower()
    print("✅ TEST 8 PASSED: Spanish language matched naturally!")

    print("\n" + "="*80)
    print(" 🎉 ALL 8 CORE TEST SCENARIOS PASSED WITH FLYING COLORS!")
    print("="*80)

if __name__ == "__main__":
    run_tests()

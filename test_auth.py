#!/usr/bin/env python3
"""Authentication system test script"""

from app.utils.auth import verify_api_key, VALID_API_KEYS
from fastapi import HTTPException

def test_authentication():
    print('🔐 Authentication System Tests:')
    print('=' * 50)

    passed = 0
    total = 0

    # Test valid API keys
    for key, info in VALID_API_KEYS.items():
        total += 1
        try:
            result = verify_api_key(key)
            user_id = result['user_id']
            permissions = result['permissions']
            print(f'✅ PASS: API key {key[:10]}... - User: {user_id}, Permissions: {permissions}')
            passed += 1
        except Exception as e:
            print(f'❌ FAIL: API key {key[:10]}... - Error: {str(e)}')

    # Test invalid API key
    total += 1
    try:
        result = verify_api_key('invalid-key-999')
        print('❌ FAIL: Invalid API key should have been rejected!')
    except HTTPException:
        print('✅ PASS: Invalid API key correctly rejected')
        passed += 1
    except Exception as e:
        print(f'❌ FAIL: Unexpected error: {str(e)}')

    print('=' * 50)
    print(f'Authentication Test Results: {passed}/{total} tests passed')
    
    if passed == total:
        print('✅ Authentication System: WORKING PERFECTLY!')
    else:
        print('❌ Authentication Issues Found!')

    return passed == total

if __name__ == '__main__':
    test_authentication()

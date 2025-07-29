#!/usr/bin/env python3
"""Security validation test script for the API Gateway"""

from app.utils.query_validator import QueryValidator

def run_security_tests():
    validator = QueryValidator()
    print('🔒 Security Validation Tests:')
    print('=' * 50)

    # Test cases: (sql_query, should_pass, description)
    test_cases = [
        ('SELECT * FROM surveys', True, 'Valid SELECT query'),
        ('DROP TABLE users', False, 'DROP table attack'),
        ('SELECT * FROM users; DELETE FROM admin;', False, 'Multiple statements'),
        ('SELECT * FROM users UNION SELECT * FROM passwords', False, 'UNION attack'),
        ('SELECT * FROM users -- WHERE active=1', False, 'SQL comment injection'),
        ('INSERT INTO users VALUES (1, \'hacker\')', False, 'INSERT statement'),
        ('SELECT COUNT(*) FROM surveys WHERE status = \'completed\'', True, 'Valid aggregate query'),
        ('UPDATE users SET password = \'hacked\'', False, 'UPDATE attack'),
        ('SELECT * FROM users WHERE id = 1 OR 1=1', True, 'Valid WHERE with OR'),
        ('SELECT name FROM users/**/UNION/**/SELECT password FROM admin', False, 'Comment-based UNION attack'),
    ]

    passed = 0
    total = len(test_cases)

    for sql, should_pass, description in test_cases:
        try:
            result = validator.validate_query(sql)
            if should_pass:
                print(f'✅ PASS: {description}')
                passed += 1
            else:
                print(f'❌ FAIL: {description} - Should have been blocked!')
        except Exception as e:
            if not should_pass:
                print(f'✅ PASS: {description} - Correctly blocked')
                passed += 1
            else:
                print(f'❌ FAIL: {description} - Should have passed! Error: {str(e)}')

    print('=' * 50)
    print(f'Security Test Results: {passed}/{total} tests passed')
    
    if passed == total:
        print('✅ SQL Injection Protection: WORKING PERFECTLY!')
        print('🛡️  Your API Gateway is secure against common SQL injection attacks!')
    else:
        print('❌ Security Issues Found!')
        print(f'⚠️  {total - passed} security tests failed!')

    return passed == total

if __name__ == '__main__':
    run_security_tests()

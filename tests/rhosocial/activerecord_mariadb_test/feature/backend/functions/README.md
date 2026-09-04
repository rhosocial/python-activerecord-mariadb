# functions tests

MariaDB function coverage: bitwise functions, function factories via supports_functions(), JSON functions (protocol detection plus real-database integration), enhanced math functions and the SQL:2003 niladic CURRENT_* forms.

## Key files

- `test_bitwise_functions.py` — bitwise function factories
- `test_functions.py` — supports_functions() and factories
- `test_json_functions.py` — JSON function version detection
- `test_json_functions_backend.py` — JSON functions executed on the server
- `test_math_enhanced_functions.py` — enhanced math functions
- `test_niladic_functions.py` — niladic CURRENT_* forms

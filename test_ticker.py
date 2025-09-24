import re

def _remove_ticker_content(content):
    if '\n' in content and '%' in content:
        pattern = r'([A-Z]+)\n[+-]?\d+\.?\d*%'
        pattern_with_delay = r'([A-Z]+\s*\([A-Z]\))\n[+-]?\d+\.?\d*%'
        pattern_futures = r'([A-Z0-9]+\s*\([A-Z]\))\n[+-]?\d+\.?\d*%'
        pattern_any_parens = r'([A-Z0-9]+\s*\([^)]+\))\n[+-]?\d+\.?\d*%'
        
        cleaned_content = re.sub(pattern, r'\1\n[PRICE]%', content)
        cleaned_content = re.sub(pattern_with_delay, r'\1\n[PRICE]%', cleaned_content)
        cleaned_content = re.sub(pattern_futures, r'\1\n[PRICE]%', cleaned_content)
        cleaned_content = re.sub(pattern_any_parens, r'\1\n[PRICE]%', cleaned_content)
        
        return cleaned_content
    return content

# Test the specific case
content1 = 'ES1 (D)\n+0.04%'
content2 = 'ES1 (D)\n+0.05%'

cleaned1 = _remove_ticker_content(content1)
cleaned2 = _remove_ticker_content(content2)

print(f'Original 1: {repr(content1)}')
print(f'Original 2: {repr(content2)}')
print(f'Cleaned 1:  {repr(cleaned1)}')
print(f'Cleaned 2:  {repr(cleaned2)}')
print(f'Equal: {cleaned1 == cleaned2}')

# Test message ID generation
def _generate_message_id(timestamp, username, content):
    id_content = _remove_ticker_content(content)
    content_hash = id_content[:50] if len(id_content) > 50 else id_content
    return f"{timestamp}_{username}_{content_hash}"

timestamp = "7:45 PM"
username = "mas1"

id1 = _generate_message_id(timestamp, username, content1)
id2 = _generate_message_id(timestamp, username, content2)

print(f'\nMessage ID 1: {id1}')
print(f'Message ID 2: {id2}')
print(f'IDs are equal: {id1 == id2} (should be True)') 
#!/usr/bin/env python3
import json
import os
import shutil
import re
from datetime import datetime
import sys

def normalize_message_content(content):
    """
    Remove ticker content (data between newline and percentage sign) from message
    This mimics the _remove_ticker_content method in chatscraper.py
    """
    if '\n' in content and '%' in content:
        # Match standard tickers
        pattern = r'([A-Z]+)\n[+-]?\d+\.?\d*%'
        # Match patterns with delayed tickers like "VIX (D)\n-5.23%"
        pattern_with_delay = r'([A-Z]+\s*\([A-Z]\))\n[+-]?\d+\.?\d*%'
        
        # Replace price data with placeholder
        cleaned_content = re.sub(pattern, r'\1\n[PRICE]%', content)
        cleaned_content = re.sub(pattern_with_delay, r'\1\n[PRICE]%', cleaned_content)
        return cleaned_content
    
    return content

def normalize_message_id(msg_id, content):
    """
    Create a normalized version of the message ID by ensuring
    ticker content is standardized in the same way as chatscraper.py
    """
    # Extract the base parts of the ID (timestamp_username_)
    parts = msg_id.split('_', 2)
    if len(parts) < 3:
        return msg_id  # Can't normalize, return as is
    
    # The content part is the third segment
    base_id = f"{parts[0]}_{parts[1]}_"
    content_part = parts[2] if len(parts) > 2 else ""
    
    # Normalize content if it contains ticker data
    normalized_content = normalize_message_content(content)
    
    # Create normalized ID using first 20 chars of normalized content
    return f"{base_id}{normalized_content[:20]}"

def remove_duplicates(log_file="MASTER_LOG.json"):
    """
    Remove duplicate messages from the master log file based on normalized message ID.
    Creates a backup of the original file before making changes.
    """
    # Get the absolute path to the log file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, log_file)
    
    if not os.path.exists(log_path):
        print(f"Error: {log_file} not found at {log_path}")
        return False
    
    print(f"Processing log file: {log_path}")
    
    try:
        # Create a backup of the original file
        backup_file = f"{log_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(log_path, backup_file)
        print(f"Created backup at: {backup_file}")
        
        # Read the original file
        with open(log_path, 'r') as f:
            data = json.load(f)
        
        original_count = len(data)
        print(f"Original message count: {original_count}")
        
        # Track seen normalized message IDs and keep only first occurrence
        seen_norm_ids = set()
        unique_messages = []
        duplicates = []
        
        for msg in data:
            if "msg_id" not in msg or not msg["msg_id"]:
                # Keep messages without IDs (shouldn't happen, but just in case)
                print(f"Warning: Message without ID found: {msg}")
                unique_messages.append(msg)
                continue
                
            # Get original ID and content
            original_id = msg["msg_id"]
            content = msg.get("content", "")
            
            # Create normalized ID for duplicate detection
            norm_id = normalize_message_id(original_id, content)
            
            if norm_id not in seen_norm_ids:
                seen_norm_ids.add(norm_id)
                unique_messages.append(msg)
            else:
                # This is a duplicate, track for reporting
                duplicates.append(msg)
        
        # Write the deduplicated data back to the file
        with open(log_path, 'w') as f:
            json.dump(unique_messages, f, indent=2)
        
        new_count = len(unique_messages)
        duplicates_removed = original_count - new_count
        
        print(f"Deduplication complete!")
        print(f"Original message count: {original_count}")
        print(f"New message count: {new_count}")
        print(f"Duplicates removed: {duplicates_removed}")
        
        # Print some examples of duplicates if any were found
        if duplicates:
            print(f"\nExamples of duplicates removed:")
            for i, dup in enumerate(duplicates[:5]):  # Show up to 5 examples
                print(f"  {i+1}. {dup.get('timestamp', '')} - {dup.get('username', '')}: {dup.get('content', '')[:50]}...")
            
            if len(duplicates) > 5:
                print(f"  ... and {len(duplicates) - 5} more.")
        
        print(f"\nSuccess rate: {(duplicates_removed / original_count * 100):.2f}% of messages were duplicates")
        
        return True
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Allow specifying a different log file as command line argument
    log_file = "MASTER_LOG.json"
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    
    print(f"Starting deduplication process for {log_file}...")
    success = remove_duplicates(log_file)
    
    if success:
        print("Deduplication completed successfully!")
    else:
        print("Deduplication failed!")
        sys.exit(1)

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import json
import os
import time
import shutil
import re
from datetime import datetime

class ChatScraper:
    def __init__(self, url, username=None, password=None, log_directory="chat_logs", headless=False):
        """
        Initialize the ChatScraper
        
        Args:
            url (str): URL of the chat website
            username (str, optional): Username for login
            password (str, optional): Password for login
            headless (bool, optional): Run browser in headless mode
            log_directory (str, optional): Directory to save chat logs
        """
        self.url = url
        self.username = username
        self.password = password
        self.known_messages = set()  # To track messages we've already processed
        self.message_data = []  # Store all message data
        self.log_directory = log_directory #for windows
        #self.log_directory = "/Users/haydenherstrom/codeprojects/godel_chat/chat_logs" #for mac
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_directory, exist_ok=True)
        
        # Use a master log file for all messages
        self.master_log = os.path.join(self.log_directory, "MASTER_LOG.json")
        
        # Also create a session log with timestamp for backup purposes
        self.session_log = os.path.join(
            self.log_directory, 
            f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # Store message lookup by username for quickly finding replied-to messages
        self.username_message_lookup = {}
        
        # Load existing messages from master log if it exists
        self._load_master_log()
        
        # Configure Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=900,800")

        self.driver = webdriver.Chrome(options=chrome_options)
        try:
            self.driver.get(self.url)
        except Exception as e:
            print(f'Error loading page: {str(e)}')
            raise

    def _load_master_log(self):
        """Load existing messages from the master log if it exists"""
        if os.path.exists(self.master_log):
            try:
                with open(self.master_log, 'r') as f:
                    existing_data = json.load(f)
                    
                # Add existing message IDs to known_messages set
                # Build username-based message lookup for finding replied-to messages
                for msg in existing_data:
                    if "msg_id" in msg:
                        self.known_messages.add(msg["msg_id"])
                        
                        # Add to username lookup for reply message identification
                        username = msg.get("username", "")
                        if username:
                            if username not in self.username_message_lookup:
                                self.username_message_lookup[username] = []
                            self.username_message_lookup[username].append(msg)
                    
                # Load existing data into message_data
                self.message_data = existing_data
                print(f"Loaded {len(existing_data)} existing messages from master log")
            except Exception as e:
                print(f"Error loading master log: {str(e)}")
                # Create a backup of the potentially corrupted file
                if os.path.exists(self.master_log):
                    backup_file = f"{self.master_log}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.master_log, backup_file)
                    print(f"Created backup of master log at {backup_file}")
                # Initialize with empty data
                self.message_data = []
        else:
            print("No existing master log found, starting with empty log")
            self.message_data = []
    
    def _remove_ticker_content(self, content):
        """
        Remove ticker content (data between newline and percentage sign) from message
        to create a stable message ID that won't change when prices update
        """
        # Use regex to remove content between \n and % in stock ticker messages
        if '\n' in content and '%' in content:
            # Match pattern like "TICKER\n-5.23%\nrest of message" or "TICKER\n+5.23%"
            pattern = r'([A-Z]+)\n[+-]?\d+\.?\d*%'
            
            # Also match patterns with delayed tickers like "VIX (D)\n-5.23%"
            pattern_with_delay = r'([A-Z]+\s*\([A-Z]\))\n[+-]?\d+\.?\d*%'
            
            # Match futures tickers like "ES1 (D)\n+0.04%" - more flexible pattern
            pattern_futures = r'([A-Z0-9]+\s*\([A-Z]\))\n[+-]?\d+\.?\d*%'
            
            # Match any ticker with parentheses and percentage
            pattern_any_parens = r'([A-Z0-9]+\s*\([^)]+\))\n[+-]?\d+\.?\d*%'
            
            # Remove price data between \n and % for each ticker in the message
            cleaned_content = re.sub(pattern, r'\1\n[PRICE]%', content)
            cleaned_content = re.sub(pattern_with_delay, r'\1\n[PRICE]%', cleaned_content)
            cleaned_content = re.sub(pattern_futures, r'\1\n[PRICE]%', cleaned_content)
            cleaned_content = re.sub(pattern_any_parens, r'\1\n[PRICE]%', cleaned_content)
            
            return cleaned_content
        
        return content
    
    def _generate_message_id(self, timestamp, username, content):
        """
        Generate a consistent message ID using the same logic across the application
        """
        # Remove ticker content from message ID check
        id_content = self._remove_ticker_content(content)
        
        # Use more characters for better uniqueness, but limit to reasonable length
        content_hash = id_content[:50] if len(id_content) > 50 else id_content
        
        return f"{timestamp}_{username}_{content_hash}"

    def close(self):
        """Close the webdriver"""
        self.driver.quit()
        print("Browser closed")

    def login(self):
        """Log in to the website if credentials are provided"""
        if not (self.username and self.password):
            print("No login credentials provided, skipping login")
            return
        try:
            print('Logging in...')
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[text()='Login']"))
            )
            login_button = self.driver.find_element(By.XPATH, "//button[text()='Login']")
            login_button.click()

            # Find username field by autocomplete attribute
            username_field = self.driver.find_element(By.CSS_SELECTOR, "input[autocomplete='username']")
            username_field.send_keys(self.username)
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[autocomplete='current-password']")
            password_field.send_keys(self.password)

            # Find login button by text
            login_button = self.driver.find_element(By.XPATH, '//*[@id="root"]/div[2]/div[3]/div/div[2]/div/form/div[2]/button')
            login_button.click()
            print("Login successful")
        except Exception as e:
            print(f'Login failed: {str(e)}')
            raise

    def navigate_to_chat(self):
        """Navigate to the chat room"""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[text()='chatbot_HHH']"))
            )
            chat_button = self.driver.find_element(By.XPATH, "//span[text()='chatbot_HHH']")
            chat_button.click()
            print("Navigated to chat room")
        except Exception as e:
            print(f'Error navigating to chat: {str(e)}')
            raise
    
    def _find_reply_msg_id(self, replied_to_username, preview_text):
        """
        Generate a message ID for the message being replied to using the same
        message ID generation logic as for regular messages
        """
        if not replied_to_username:
            return None
            
        # Check if we have messages from this user
        if replied_to_username not in self.username_message_lookup:
            return None
            
        # Get all messages from the user being replied to
        user_messages = self.username_message_lookup[replied_to_username]
        
        # If we have a preview, try to match it with a message
        if preview_text:
            # Clean up preview text for better matching
            preview_clean = preview_text.strip().lower()
            
            # Try to find a message that contains the preview text
            for msg in reversed(user_messages):  # Start with most recent
                content = msg.get("content", "").strip().lower()
                if preview_clean in content or content.startswith(preview_clean):
                    # Re-generate message ID using the same logic for consistency
                    timestamp = msg.get("timestamp", "")
                    username = msg.get("username", "")
                    content = msg.get("content", "")
                    return self._generate_message_id(timestamp, username, content)
        
        # If we can't find a specific match or there's no preview,
        # just use the most recent message from this user
        if user_messages:
            latest_msg = user_messages[-1]
            timestamp = latest_msg.get("timestamp", "")
            username = latest_msg.get("username", "")
            content = latest_msg.get("content", "")
            return self._generate_message_id(timestamp, username, content)
            
        return None
    
    def get_chat_messages(self):
        """Extract all chat messages from the page"""
        try:
            print("Waiting for chat container to load...")
            # Wait for the chat messages to load - updated selector for new structure
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='absolute flex bg-[#121212] flex-col top-[50px] right-0 left-0 bottom-0 pt-[10px] px-[10px] m-0 overflow-x-hidden overflow-y-scroll']"))
            )
            
            msg_container = self.driver.find_element(By.XPATH, "//div[@class='absolute flex bg-[#121212] flex-col top-[50px] right-0 left-0 bottom-0 pt-[10px] px-[10px] m-0 overflow-x-hidden overflow-y-scroll']")
            
            # Use more specific selectors to find only actual message containers
            message_elements = []
            
            # Primary selector for the new message structure
            primary_messages = msg_container.find_elements(By.XPATH, ".//div[contains(@class, 'group text-[#eaeaea]')]")
            message_elements.extend(primary_messages)
            
            # Fallback selector for older message structures
            if len(message_elements) == 0:
                fallback_messages = msg_container.find_elements(By.XPATH, ".//div[contains(@class, 'text-[#eaeaea] rounded')]")
                message_elements.extend(fallback_messages)
            
            print(f"Found {len(message_elements)} potential message elements")
            
            new_messages = []
            processed_count = 0
            
            for msg_elem in message_elements:
                try:
                    processed_count += 1
                    
                    # Quick validation: check if element has reasonable text content
                    element_text = msg_elem.text.strip()
                    if len(element_text) < 10:  # Skip elements with very short text
                        continue
                    
                    # Extract timestamp first - if we can't find one, skip this element
                    timestamp = self._extract_timestamp_fast(msg_elem)
                    if timestamp == "Unknown time":
                        continue
                    
                    # Extract username - if we can't find one, skip this element
                    username = self._extract_username_fast(msg_elem)
                    if username == "Unknown user" or len(username) < 2:
                        continue
                    
                    # Extract content
                    content = self._extract_content_fast(msg_elem, username)
                    if not content or len(content) < 2:
                        continue
                    
                    # Create message ID and check if we've seen it before
                    msg_id = self._generate_message_id(timestamp, username, content)
                    if msg_id in self.known_messages:
                        continue
                    
                    # Check if this is a reply message
                    is_reply = self._is_reply_message_fast(msg_elem)
                    reply_details = self._extract_reply_details_fast(msg_elem) if is_reply else {}
                    
                    # Add to known messages immediately
                    self.known_messages.add(msg_id)
                    
                    # Find reply_msg_id if this is a reply
                    reply_msg_id = None
                    if is_reply:
                        replied_to = reply_details.get("replied_to", "")
                        preview = reply_details.get("preview", "")
                        reply_msg_id = self._find_reply_msg_id(replied_to, preview)
                    
                    message_data = {
                        "date": datetime.now().strftime('%Y%m%d'),
                        "timestamp": timestamp,
                        "username": username,
                        "content": content,
                        "isReply": is_reply,
                        "msg_id": msg_id
                    }
                    
                    # Add reply details if this is a reply
                    if is_reply:
                        message_data["replied_to"] = reply_details.get("replied_to", "")
                        message_data["reply_msg_id"] = reply_msg_id
                        
                    new_messages.append(message_data)
                    self.message_data.append(message_data)
                    
                    # Add to username lookup for future reply message identification
                    if username not in self.username_message_lookup:
                        self.username_message_lookup[username] = []
                    self.username_message_lookup[username].append(message_data)
                    
                    # Save immediately after each new message is found
                    self._save_to_master_log()
                    
                    # Print new message (but limit output for performance)
                    if len(new_messages) <= 5:  # Only show first 5 new messages
                        reply_indicator = f"[REPLY to {message_data.get('replied_to', '')}] " if is_reply else ""
                        print(f"New message: [{timestamp}] {reply_indicator}{username}: {content[:50]}...")
                        
                except Exception as e:
                    # Only log errors for the first few elements to avoid spam
                    if processed_count <= 10:
                        print(f"Error processing message element {processed_count}: {str(e)}")
                    continue
            
            print(f"Processed {processed_count} elements, found {len(new_messages)} new messages")
            return new_messages
            
        except Exception as e:
            print(f'Error getting chat messages: {str(e)}')
            print(f'Error type: {type(e).__name__}')
            import traceback
            print(f'Full traceback: {traceback.format_exc()}')
            raise

    def _extract_timestamp_fast(self, msg_elem):
        """Fast timestamp extraction with minimal processing"""
        try:
            # Primary selector for the new structure
            timestamp_elems = msg_elem.find_elements(By.XPATH, ".//span[contains(@style, 'color: grey; font-size: 8px;')]")
            if timestamp_elems:
                timestamp_text = timestamp_elems[0].text.strip()
                if timestamp_text and (':' in timestamp_text or 'AM' in timestamp_text or 'PM' in timestamp_text):
                    return timestamp_text
            
            # Fallback selector
            timestamp_elems = msg_elem.find_elements(By.XPATH, ".//span[contains(text(), 'AM') or contains(text(), 'PM')]")
            if timestamp_elems:
                timestamp_text = timestamp_elems[0].text.strip()
                if timestamp_text and ':' in timestamp_text:
                    return timestamp_text
                    
        except:
            pass
        
        return "Unknown time"

    def _extract_username_fast(self, msg_elem):
        """Fast username extraction with minimal processing"""
        try:
            # Primary selector for the new structure
            username_elems = msg_elem.find_elements(By.XPATH, ".//div[@class='inline-flex relative']")
            if username_elems:
                username_text = username_elems[0].text.strip().replace(':', '').strip()
                if username_text and 2 <= len(username_text) <= 50:
                    return username_text
            
            # Fallback selector
            username_elems = msg_elem.find_elements(By.XPATH, ".//div[contains(@class, 'inline-flex')]")
            if username_elems:
                username_text = username_elems[0].text.strip().replace(':', '').strip()
                if username_text and 2 <= len(username_text) <= 50:
                    return username_text
                    
        except:
            pass
        
        return "Unknown user"

    def _extract_content_fast(self, msg_elem, username):
        """Fast content extraction with minimal processing"""
        try:
            # Primary selector for the new structure
            content_elems = msg_elem.find_elements(By.XPATH, ".//div[@class='block pr-[20px] break-words']")
            if content_elems:
                content_text = content_elems[0].text
                return self._parse_content_from_full_text_fast(content_text, username)
            
            # Fallback: try to get the entire text
            full_text = msg_elem.text
            if full_text:
                return self._parse_content_from_full_text_fast(full_text, username)
                
        except:
            pass
        
        return ""

    def _parse_content_from_full_text_fast(self, full_text, username):
        """Fast content parsing with minimal processing"""
        if not full_text:
            return ""
        
        # Strategy 1: Look for "username: content" pattern
        if username and username in full_text and ":" in full_text:
            username_pos = full_text.find(username)
            if username_pos != -1:
                colon_pos = full_text.find(":", username_pos)
                if colon_pos != -1:
                    content = full_text[colon_pos + 1:].strip()
                    if content:
                        return content
        
        # Strategy 2: Look for any colon and take what comes after
        if ":" in full_text:
            parts = full_text.split(":")
            if len(parts) > 1:
                content = parts[-1].strip()
                if content:
                    return content
        
        # Strategy 3: Return the full text as fallback
        return full_text.strip()

    def _is_reply_message_fast(self, msg_elem):
        """Fast reply detection with minimal processing"""
        try:
            # Look for reply arrow icon
            reply_icon = msg_elem.find_elements(By.CSS_SELECTOR, ".anticon-enter.enter-reply")
            if reply_icon:
                return True
                
            # Look for @ pattern in any element
            all_elements = msg_elem.find_elements(By.XPATH, ".//*")
            for elem in all_elements[:5]:  # Only check first 5 elements for performance
                try:
                    text = elem.text
                    if text and text.startswith("@") and ":" in text:
                        return True
                except:
                    continue
            
            return False
        except:
            return False

    def _extract_reply_details_fast(self, msg_elem):
        """Fast reply details extraction with minimal processing"""
        try:
            # Look for @ pattern in any element
            all_elements = msg_elem.find_elements(By.XPATH, ".//*")
            for elem in all_elements[:5]:  # Only check first 5 elements for performance
                try:
                    text = elem.text
                    if text and text.startswith("@") and ":" in text:
                        parts = text.split(":", 1)
                        if len(parts) >= 1:
                            replied_to = parts[0][1:].strip()
                            preview = parts[1].strip() if len(parts) > 1 else ""
                            return {
                                "replied_to": replied_to,
                                "preview": preview
                            }
                except:
                    continue
            
            return {"replied_to": "", "preview": ""}
        except:
            return {"replied_to": "", "preview": ""}

    def _save_to_master_log(self):
        """Internal method to safely save messages to the master log in real-time"""
        try:
            # First save to session log as backup
            with open(self.session_log, 'w') as f:
                json.dump(self.message_data, f, indent=2)
            
            # Create a temporary copy of the master log
            temp_log = f"{self.master_log}.temp"
            
            # Copy master log to temp if it exists
            if os.path.exists(self.master_log):
                shutil.copy2(self.master_log, temp_log)
            
            # Write updated data to temp file
            with open(temp_log, 'w') as f:
                json.dump(self.message_data, f, indent=2)
            
            # Replace the master log with the temp file
            if os.path.exists(temp_log):
                os.replace(temp_log, self.master_log)
                
        except Exception as e:
            print(f"Error saving to master log: {str(e)}")

    def get_new_messages(self):
        """Check for new messages that we haven't seen before"""
        new_messages = self.get_chat_messages()
        return new_messages
    
    def save_messages_to_file(self, filename=None):
        """Save all collected messages to a JSON file"""
        if filename is None:
            filename = self.master_log
            
        try:
            # Create a backup copy first
            backup_filename = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(filename):
                shutil.copy2(filename, backup_filename)
                print(f"Created backup of log file at {backup_filename}")
            
            # Now save the updated file
            with open(filename, 'w') as f:
                json.dump(self.message_data, f, indent=2)
            print(f"Messages saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving messages: {str(e)}")
            return False


def main():
    try:
        # Import configuration
        from config import GODEL_URL, GODEL_USERNAME, GODEL_PASSWORD, LOG_DIRECTORY
    except ImportError:
        print("Error: Could not find config.py. Please copy config.template.py to config.py and update with your credentials.")
        return
    
    # Create the scraper
    scraper = ChatScraper(GODEL_URL, GODEL_USERNAME, GODEL_PASSWORD, LOG_DIRECTORY)
    
    try:
        # Login and navigate to the chat
        scraper.login()
        scraper.navigate_to_chat()
        
        # Get initial messages
        print("Getting initial messages...")
        initial_messages = scraper.get_chat_messages()
        print(f"Found {len(initial_messages)} initial messages")
        print(f"Initial messages saved to {scraper.master_log}")
    
        # Monitor the chat continuously with optimized frequency
        print(f"Starting chat monitoring. Logs will be saved to {scraper.master_log}")
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while True:
                try:
                    # Check for new messages every 10 seconds (reduced from 5 for better performance)
                    new_messages = scraper.get_new_messages()
                    
                    if new_messages:
                        # Print summary of new messages
                        print(f"Found {len(new_messages)} new messages")
                        
                        # Print first few new messages to console
                        for i, msg in enumerate(new_messages[:3]):  # Only show first 3
                            reply_indicator = f"[REPLY to {msg.get('replied_to', '')}] " if msg.get("isReply", False) else ""
                            print(f"[{msg['timestamp']}] {reply_indicator}{msg['username']}: {msg['content'][:50]}...")
                        
                        if len(new_messages) > 3:
                            print(f"... and {len(new_messages) - 3} more messages")
                        
                        consecutive_errors = 0  # Reset error counter on success
                    else:
                        # Only print status every 10 checks to reduce noise
                        if consecutive_errors == 0:
                            print("No new messages found")
                    
                except Exception as e:
                    consecutive_errors += 1
                    print(f"Error checking for new messages (attempt {consecutive_errors}): {str(e)}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"Too many consecutive errors ({consecutive_errors}), restarting browser...")
                        scraper.close()
                        time.sleep(5)
                        scraper = ChatScraper(GODEL_URL, GODEL_USERNAME, GODEL_PASSWORD)
                        scraper.login()
                        scraper.navigate_to_chat()
                        consecutive_errors = 0
                
                time.sleep(10)  # Check every 10 seconds instead of 5
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            
    except Exception as e:
        print(f"Error in main: {str(e)}")
    
    finally:
        # Always close the browser
        scraper.close()
        print("Script finished. Chat logs saved to master log.")


def test_ticker_content_removal():
    """Test function to verify ticker content removal works correctly"""
    scraper = ChatScraper("dummy_url")  # Create instance just for testing
    
    # Test cases
    test_cases = [
        ("ES1 (D)\n+0.04%", "ES1 (D)\n[PRICE]%"),
        ("ES1 (D)\n+0.05%", "ES1 (D)\n[PRICE]%"),
        ("ES1 (D)\n-0.12%", "ES1 (D)\n[PRICE]%"),
        ("VIX (D)\n+5.23%", "VIX (D)\n[PRICE]%"),
        ("SPY\n+1.45%", "SPY\n[PRICE]%"),
        ("Hello world", "Hello world"),  # Should not change
        ("ES1 (D)\n+0.04%\nSome additional text", "ES1 (D)\n[PRICE]%\nSome additional text")
    ]
    
    print("Testing ticker content removal:")
    for original, expected in test_cases:
        result = scraper._remove_ticker_content(original)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{original}' -> '{result}' (expected: '{expected}')")
    
    # Test message ID generation
    print("\nTesting message ID generation:")
    timestamp = "7:45 PM"
    username = "mas1"
    
    content1 = "ES1 (D)\n+0.04%"
    content2 = "ES1 (D)\n+0.05%"
    
    id1 = scraper._generate_message_id(timestamp, username, content1)
    id2 = scraper._generate_message_id(timestamp, username, content2)
    
    print(f"ID1: {id1}")
    print(f"ID2: {id2}")
    print(f"IDs are equal: {id1 == id2} (should be True)")

if __name__ == "__main__":
    # Uncomment the line below to run the test
    # test_ticker_content_removal()
    main() 
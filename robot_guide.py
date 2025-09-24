import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import time
import json
import os
import re

class ChatScraper:
    def __init__(self, url, username=None, password=None, headless=False):
        """
        Initialize the ChatScraper
        
        Args:
            url (str): URL of the chat website
            username (str, optional): Username for login
            password (str, optional): Password for login
            headless (bool, optional): Run browser in headless mode
        """
        self.url = url
        self.username = username
        self.password = password
        self.known_messages = set()  # To track messages we've already processed
        self.message_data = []  # Store all message data
        
        # Configure Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def login(self):
        """Log in to the website if credentials are provided"""
        if not (self.username and self.password):
            print("No login credentials provided, skipping login")
            return
        
        try:
            self.driver.get(self.url)
            print("Navigating to login page...")
            
            # Wait for login form to load and enter credentials
            # This will need to be customized for the specific website
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            
            # Submit the form
            submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            
            # Wait for successful login
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".chat-container"))
            )
            print("Login successful!")
            
        except Exception as e:
            print(f"Login failed: {str(e)}")
            raise
    
    def navigate_to_chat(self):
        """Navigate to the chat page if not already there"""
        if "login" in self.driver.current_url or self.driver.current_url != self.url:
            print("Navigating to chat page...")
            self.driver.get(self.url)
            
            # Wait for chat container to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pb-\\[70px\\]"))
            )
    
    def extract_message_id(self, message_element):
        """
        Create a unique identifier for a message to prevent duplicates
        Uses timestamp and username and message content
        """
        try:
            # Extract timestamp
            timestamp = message_element.find_element(By.CSS_SELECTOR, "span[style*='padding-right: 5px; color: grey;']").text
            
            # Extract username
            username = message_element.find_element(By.CSS_SELECTOR, "div.inline-flex").text
            
            # Extract a portion of the message content (first 50 chars)
            message_text = message_element.find_element(By.CSS_SELECTOR, "div.block.pr-\\[20px\\]").text
            message_excerpt = message_text[:50]
            
            # Create a unique identifier
            return f"{timestamp}:{username}:{message_excerpt}"
        except Exception:
            # Fallback to using the entire message HTML if we can't extract components
            return message_element.get_attribute('innerHTML')[:100]
    
    def parse_message(self, message_element):
        """Extract data from a message element"""
        try:
            # Extract timestamp
            timestamp = message_element.find_element(By.CSS_SELECTOR, "span[style*='padding-right: 5px; color: grey;']").text
            
            # Extract username
            username = message_element.find_element(By.CSS_SELECTOR, "div.inline-flex").text
            
            # Extract message content - may contain nested elements for replies or mentions
            message_content_element = message_element.find_element(By.CSS_SELECTOR, "div.block.pr-\\[20px\\]")
            message_content = message_content_element.text
            
            # Check if this is a reply to someone (has the reply arrow)
            is_reply = False
            reply_to = None
            try:
                reply_element = message_element.find_element(By.CSS_SELECTOR, "div.whitespace-nowrap.opacity-80.text-\\[10px\\]")
                if reply_element:
                    is_reply = True
                    reply_text = reply_element.text
                    # Extract who the message is replying to using regex
                    reply_match = re.search(r'@([^:]+):', reply_text)
                    if reply_match:
                        reply_to = reply_match.group(1).strip()
            except Exception:
                # Not a reply, ignore
                pass
            
            # Build the message data object
            message_data = {
                "timestamp": timestamp,
                "username": username,
                "content": message_content,
                "is_reply": is_reply,
                "reply_to": reply_to,
                "scraped_at": datetime.now().isoformat()
            }
            
            return message_data
        
        except Exception as e:
            print(f"Error parsing message: {str(e)}")
            return None
    
    def scrape_messages(self):
        """Scrape all visible messages from the chat"""
        try:
            # Wait for messages to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.text-\\[\\#eaeaea\\]"))
            )
            
            # Get all message elements
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.text-\\[\\#eaeaea\\]")
            print(f"Found {len(message_elements)} message elements")
            
            new_messages = []
            
            for message_element in message_elements:
                # Create a unique identifier for this message
                message_id = self.extract_message_id(message_element)
                
                # Skip if we've already processed this message
                if message_id in self.known_messages:
                    continue
                
                # Parse the message
                message_data = self.parse_message(message_element)
                if message_data:
                    self.known_messages.add(message_id)
                    self.message_data.append(message_data)
                    new_messages.append(message_data)
            
            return new_messages
        
        except Exception as e:
            print(f"Error scraping messages: {str(e)}")
            return []
    
    def save_messages(self, filename="chat_data.json"):
        """Save all collected messages to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.message_data, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(self.message_data)} messages to {filename}")
        except Exception as e:
            print(f"Error saving messages: {str(e)}")
    
    def monitor_chat(self, interval=5, duration=None, save_interval=60):
        """
        Monitor the chat for new messages
        
        Args:
            interval (int): How often to check for new messages (seconds)
            duration (int, optional): How long to monitor (seconds), None for indefinite
            save_interval (int): How often to save data to disk (seconds)
        """
        try:
            self.navigate_to_chat()
            
            start_time = time.time()
            last_save_time = start_time
            
            while True:
                # Check if we've reached the monitoring duration
                current_time = time.time()
                if duration and (current_time - start_time) > duration:
                    print(f"Reached monitoring duration of {duration} seconds")
                    break
                
                # Scrape new messages
                new_messages = self.scrape_messages()
                if new_messages:
                    print(f"Found {len(new_messages)} new messages")
                    
                    # Print the latest message for debugging
                    latest = new_messages[-1]
                    print(f"Latest: [{latest['timestamp']}] {latest['username']}: {latest['content'][:50]}...")
                
                # Save data periodically
                if (current_time - last_save_time) > save_interval:
                    self.save_messages()
                    last_save_time = current_time
                
                # Wait for the next scraping interval
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        except Exception as e:
            print(f"Error monitoring chat: {str(e)}")
        finally:
            # Save the final data
            self.save_messages()
    
    def close(self):
        """Close the webdriver"""
        self.driver.quit()
        print("Browser closed")


def main():
    # Example usage
    url = "https://example.com/chat"  # Replace with the actual URL
    
    # Create the scraper (without login for now)
    scraper = ChatScraper(url)
    
    try:
        # Navigate to the chat page directly (no login)
        scraper.navigate_to_chat()
        
        # Monitor the chat for 1 hour (3600 seconds)
        print("Starting chat monitoring...")
        scraper.monitor_chat(interval=5, duration=3600, save_interval=60)
    
    except Exception as e:
        print(f"Error in main: {str(e)}")
    
    finally:
        # Always close the browser
        scraper.close()


if __name__ == "__main__":
    main()

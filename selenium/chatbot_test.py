import time
import unittest
import logging
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
class LogFilter(logging.Filter):
    def filter(self, record):
        return record.name == __name__

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with custom formatter
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                            datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)

# Add filter to handler
console_handler.addFilter(LogFilter())

# Add handler to logger
logger.addHandler(console_handler)

# Disable other loggers
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('webdriver_manager').setLevel(logging.WARNING)

class JobSyChatbotTest(unittest.TestCase):
    
    def setUp(self):
        # Set up Chrome options
        chrome_options = Options()
        # Uncomment the line below to run in headless mode
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Initialize the Chrome driver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.maximize_window()
        logger.info("Chrome browser initialized with maximized window")
        
        # Base URL is the login page
        self.base_url = "http://127.0.0.1:5000/"
        
        # Test credentials
        self.test_email = "antonthomas2025@mca.ajce.in"  
        self.test_password = "Anton123"     
    
    def test_chatbot_interaction(self):
        """Test login and chatbot interaction"""
        driver = self.driver
        
        # Navigate directly to the base URL (login page)
        driver.get(self.base_url)
        logger.info("Navigated to the application URL")
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login-form"))
        )
        
        # Find the email and password fields and submit button
        email_field = driver.find_element(By.ID, "email")
        password_field = driver.find_element(By.ID, "password")
        submit_button = driver.find_element(By.ID, "signin")
        
        # Enter credentials
        email_field.send_keys(self.test_email)
        logger.info("Email entered")
        password_field.send_keys(self.test_password)
        logger.info("Password entered")
        
        # Submit the form
        submit_button.click()
        logger.info("Login button clicked")
        
        # Wait for redirection after successful login
        WebDriverWait(driver, 10).until(
            EC.url_changes(self.base_url)
        )
        logger.info("Login successful, main page loaded")
        
        # Take a screenshot after login
        driver.save_screenshot("after_login.png")
        
        # Verify successful login by checking URL
        self.assertNotEqual(driver.current_url, self.base_url, "URL did not change after login")
        
        # Wait for the chat toggle button to be visible
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "chat-toggle"))
        )
        
        # Click on the chat toggle button to open the chat
        chat_toggle = driver.find_element(By.CLASS_NAME, "chat-toggle")
        chat_toggle.click()
        logger.info("Chat toggle button clicked")
        
        # Wait for the chat container to be visible
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "chatContainer"))
        )
        logger.info("Chat container loaded")
        
        # Wait for the welcome message to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "bot-message"))
        )
        logger.info("Welcome message received")
        
        # Take a screenshot of the chat with welcome message
        driver.save_screenshot("chat_welcome.png")
        
        # Type a job-related query in the chat input
        chat_input = driver.find_element(By.ID, "userInput")
        chat_input.send_keys("How can I find software developer jobs?")
        logger.info("User query entered")
        
        # Click the send button
        send_button = driver.find_element(By.CLASS_NAME, "send-button")
        send_button.click()
        logger.info("Send button clicked")
        
        # Wait for the response from the chatbot
        time.sleep(3)  # Give the chatbot some time to respond
        logger.info("Chatbot response received")
        
        # Take a screenshot of the chat with the response
        driver.save_screenshot("chat_response.png")
        
        # Verify that a response was received
        chat_messages = driver.find_elements(By.CLASS_NAME, "bot-message")
        self.assertGreaterEqual(len(chat_messages), 2, "No response received from chatbot")
        
        # Click on a button in the chat if available
        try:
            chat_buttons = driver.find_elements(By.CLASS_NAME, "chat-action-button")
            if len(chat_buttons) > 0:
                # Take a screenshot before clicking the button
                driver.save_screenshot("before_button_click.png")
                
                # Click the first button
                chat_buttons[0].click()
                logger.info("Chat action button clicked")
                
                # Wait for page to change
                time.sleep(2)
                
                # Take a screenshot after clicking the button
                driver.save_screenshot("after_button_click.png")
        except:
            logger.warning("No chat buttons available to click")
    
    def tearDown(self):
        # Close the browser
        self.driver.quit()
        logger.info("Browser session ended")

if __name__ == "__main__":
    unittest.main(verbosity=2) 
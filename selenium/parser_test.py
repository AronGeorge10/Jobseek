import unittest
import logging
import sys
import os
import time
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
logger.addHandler(console_handler)

# Disable other loggers
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('webdriver_manager').setLevel(logging.WARNING)

class TestResumeUploadJourney(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Uncomment to run headless
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.maximize_window()
        logger.info("Chrome browser initialized with maximized window")
        
        # Base URL and credentials
        self.base_url = "http://127.0.0.1:5000"
        self.test_email = "antonthomas2025@mca.ajce.in"
        self.test_password = "Anton123"
        
        # Test resume file path
        self.test_resume = os.path.join(os.path.dirname(__file__), "resume_parser", "AronGeorgeJain_Resume.pdf")
        
    def test_resume_upload_journey(self):
        """Test the complete resume upload journey"""
        driver = self.driver
        
        # 1. Navigate to login page
        driver.get(self.base_url)
        logger.info("Navigated to login page")
        
        # 2. Login process
        email_field = driver.find_element(By.ID, "email")
        password_field = driver.find_element(By.ID, "password")
        submit_button = driver.find_element(By.ID, "signin")
        
        email_field.send_keys(self.test_email)
        logger.info("Email entered")
        password_field.send_keys(self.test_password)
        logger.info("Password entered")
        submit_button.click()
        logger.info("Login button clicked")
        
        # Wait for login to complete
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "profileDropdown"))
        )
        logger.info("Successfully logged in")
        
        # 3. Click profile dropdown
        profile_dropdown = driver.find_element(By.ID, "profileDropdown")
        profile_dropdown.click()
        logger.info("Profile dropdown clicked")
        
        # 4. Click "Set up Profile" in dropdown
        setup_profile_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Set up Profile')]"))
        )
        setup_profile_link.click()
        logger.info("Set up Profile link clicked")
        
        # 5. Click "Upload Resume" button
        upload_resume_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Upload Resume')]"))
        )
        upload_resume_button.click()
        logger.info("Upload Resume button clicked")
        
        # 6. Wait for resume parser page to load and click browse files
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "fileInput"))
        )
        
        # 7. Upload the resume file
        if os.path.exists(self.test_resume):
            file_input.send_keys(self.test_resume)
            logger.info(f"Resume file selected: {self.test_resume}")
            
            # Wait for parsing to complete
            WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.ID, "parsedContent"))
            )
            logger.info("Resume parsing completed")
        else:
            logger.error(f"Test resume file not found: {self.test_resume}")
            self.fail("Test resume file not found")
            
    def tearDown(self):
        """Clean up after each test"""
        self.driver.quit()
        logger.info("Browser session ended")

if __name__ == '__main__':
    unittest.main(verbosity=2, buffer=True, exit=False)

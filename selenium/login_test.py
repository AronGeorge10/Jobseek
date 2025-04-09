import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class JobSeekLoginTest(unittest.TestCase):
    
    def setUp(self):
        # Set up Chrome options
        chrome_options = Options()
        # Uncomment the line below to run in headless mode
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Initialize the Chrome driver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.maximize_window()
        
        # Base URL is the login page
        self.base_url = "http://127.0.0.1:5000/"
        
        # Test credentials
        self.test_email = "arongeorgejain2025@mca.ajce.in"  
        self.test_password = "Aron2002"     
    
    def test_successful_login(self):
        """Test successful login with valid credentials"""
        driver = self.driver
        
        # Navigate directly to the base URL (login page)
        driver.get(self.base_url)
        
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
        password_field.send_keys(self.test_password)
        
        # Take a screenshot before submitting
        driver.save_screenshot("before_login.png")
        
        # Submit the form
        submit_button.click()
        
        # Wait for redirection after successful login
        WebDriverWait(driver, 10).until(
            EC.url_changes(self.base_url)
        )
        
        # Take a screenshot after login
        driver.save_screenshot("after_login.png")
        
        # Verify successful login by checking URL or presence of an element
        self.assertNotEqual(driver.current_url, self.base_url, "URL did not change after login")
    
    def test_failed_login(self):
        """Test failed login with invalid credentials"""
        driver = self.driver
        
        # Navigate directly to the base URL (login page)
        driver.get(self.base_url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login-form"))
        )
        
        # Find the email and password fields and submit button
        email_field = driver.find_element(By.ID, "email")
        password_field = driver.find_element(By.ID, "password")
        submit_button = driver.find_element(By.ID, "signin")
        
        # Enter invalid credentials
        email_field.send_keys("invalid@example.com")
        password_field.send_keys("wrongpassword")
        
        # Submit the form
        submit_button.click()
        
        # Wait for error message - just check that we're still on the login page
        time.sleep(2)
        
        # Verify we're still on the login page (failed login shouldn't redirect)
        self.assertEqual(driver.current_url, self.base_url, "URL changed after failed login attempt")
    
    def tearDown(self):
        # Close the browser
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(verbosity=2)

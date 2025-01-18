import tkinter as tk
from tkinter import messagebox, scrolledtext
import sqlite3
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
from io import BytesIO


def initialize_db():
    conn = sqlite3.connect('scraper.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            email TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY,
            tweet TEXT,
            image TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def insert_user(cursor, username, password, email):
    _user_query = '''
        INSERT OR IGNORE INTO users (username, password, email)
        VALUES (?, ?, ?)
    '''
    try:
        cursor.execute(_user_query, (username, password, email))
        return True
    except sqlite3.Error as e:
        print(f"Error inserting user: {e}")
        return False

def insert_tweet(cursor, tweet_text, img_data):
    _tweet_query = '''
        INSERT OR IGNORE INTO tweets (tweet, image)
        VALUES (?, ?)
    '''
    try:
        cursor.execute(_tweet_query, (tweet_text, img_data))
        return True
    except sqlite3.Error as e:
        print(f"Error inserting tweet: {e}")
        return False

def login_to_site(driver, email, username, password):
    driver.get("https://x.com/i/flow/login")
    driver.maximize_window()
    time.sleep(5)

    email_field = driver.find_element(By.CSS_SELECTOR, '[name="text"]')
    email_field.send_keys(email)
    time.sleep(3)
    email_field.send_keys(Keys.ENTER)
    time.sleep(10)

    username_field = driver.find_element(By.CSS_SELECTOR, '[name="text"]')
    username_field.send_keys(username)
    time.sleep(3)
    username_field.send_keys(Keys.ENTER)
    time.sleep(10)

    password_field = driver.find_element(By.CSS_SELECTOR, '[name="password"]')
    password_field.send_keys(password)
    time.sleep(3)
    password_field.send_keys(Keys.ENTER)
    time.sleep(15)

def scrape_tweets(driver, search_query):
    input_element = driver.find_element(By.CSS_SELECTOR, '[placeholder="Search"]')
    input_element.send_keys(search_query)
    time.sleep(3)
    input_element.send_keys(Keys.ENTER)
    time.sleep(5)

    tweets_data = []
    SCROLL_PAUSE_TIME = 0.5

    while True:
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break

        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        tweets = soup.find_all("article")

        for tweet in tweets:
            tweet_text = tweet.text.strip()
            tweets_data.append({"text": tweet_text, "image": None})

            images = soup.find_all("img")
            for img in images:
                img_url = img.get('src')
                if img_url and 'media' in img_url:
                    img_data = download_image(img_url)
                    if img_data:
                        tweets_data[-1]["image"] = img_data

    return tweets_data

def download_image(img_url):
    try:
        response = requests.get(img_url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return None

class TwitterScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Twitter Scraper")
        self.conn, self.cursor = initialize_db()

        self.create_widgets()

    def create_widgets(self):

        tk.Label(self.root, text="Email:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.email_entry = tk.Entry(self.root, width=40)
        self.email_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self.root, text="Username:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.username_entry = tk.Entry(self.root, width=40)
        self.username_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self.root, text="Password:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.password_entry = tk.Entry(self.root, width=40, show="*")
        self.password_entry.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(self.root, text="Search Query:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.search_entry = tk.Entry(self.root, width=40)
        self.search_entry.grid(row=3, column=1, padx=10, pady=5)

        self.start_button = tk.Button(self.root, text="Start Scraping", command=self.start_scraping)
        self.start_button.grid(row=4, column=0, columnspan=2, pady=10)

        tk.Label(self.root, text="Scraped Tweets:").grid(row=5, column=0, columnspan=2, pady=5)
        self.output_area = scrolledtext.ScrolledText(self.root, width=60, height=10)
        self.output_area.grid(row=6, column=0, columnspan=2, padx=10, pady=5)

        tk.Label(self.root, text="Tweets List:").grid(row=7, column=0, columnspan=2, pady=5)
        self.tweet_listbox = tk.Listbox(self.root, width=60, height=10)
        self.tweet_listbox.grid(row=8, column=0, columnspan=2, padx=10, pady=5)

        self.image_label = tk.Label(self.root, width=100, height=100, bg='lightgray')
        self.image_label.grid(row=9, column=0, columnspan=2, pady=10)

    def display_images_and_tweets(self, tweet_text, img_data):
        # Display Tweet Text in the ScrolledText widget
        self.output_area.insert(tk.END, tweet_text + "\n\n")

        if img_data:
            # Resize image to fit the label
            img = Image.open(BytesIO(img_data))
            img = img.resize((100, 100))  # Resize to a reasonable size
            photo = ImageTk.PhotoImage(img)

            # Update image label with the image
            self.image_label.config(image=photo)
            self.image_label.image = photo  # Keep reference to avoid garbage collection

    def start_scraping(self):
        email = self.email_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        search_query = self.search_entry.get()

        if not email or not username or not password or not search_query:
            messagebox.showerror("Input Error", "All fields are required!")
            return

        if not insert_user(self.cursor, username, password, email):
            messagebox.showerror("Database Error", "Failed to insert user into the database.")
            return

        driver = webdriver.Chrome()
        try:
            login_to_site(driver, email, username, password)
            tweets = scrape_tweets(driver, search_query)

            for tweet in tweets:
                tweet_text = tweet["text"]
                img_data = tweet["image"]
                if insert_tweet(self.cursor, tweet_text, img_data):
                    self.display_images_and_tweets(tweet_text, img_data)

            messagebox.showinfo("Success", "Tweets scraped and saved successfully!")
        except Exception as e:
            messagebox.showerror("Scraping Error", f"An error occurred: {e}")
        finally:
            driver.quit()
            self.conn.commit()

if __name__ == "__main__":
    root = tk.Tk()
    app = TwitterScraperApp(root)
    root.mainloop()

# Book Hive

## 🌐 Live Website
**Click here to visit:** [textbookhive.shop](https://textbookhive.shop/)

## What is this?
Book Hive is an online shop for books. It is like a digital bookstore where you can find your favorite books, see reviews, and buy them easily.

## Features
**For Shoppers:**
- Search for books by price or type.
- Save books to a wishlist to buy later.
- Add books to your shopping cart.
- Pay safely online or use cash on delivery.
- Sign in securely with email or Google.
- Read books in different languages.

**For Shop Managers (Admins):**
- Add new books to the store.
- See orders from customers.
- Manage user accounts and inventory.

## Technology Used
This project is built using:
- **Python & Django:** The main logic of the website.
- **PostgreSQL:** To store all the data.
- **HTML, CSS & JavaScript:** For the website design.
- **Razorpay:** For secure payments.

## How to Run This Project
Follow these steps to start the website on your computer:

1. **Download the Code**
   Open your command text and type:
   ```bash
   git clone https://github.com/shrnemmnl/book_hive.git
   cd book_hive
   ```

2. **Install Requirements**
   Install the necessary tools using:
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Secret Keys**
   Create a new file named `.env` in the main folder. inside this file, add your secret settings (like Database passwords, Email keys, and Razorpay keys).

4. **Prepare the Database**
   Run this command to set up the data storage:
   ```bash
   python manage.py migrate
   ```

5. **Start the Server**
   Run this command to turn on the website:
   ```bash
   python manage.py runserver
   ```

6. **Visit the Website**
   Open your web browser and go to this address:
   `http://127.0.0.1:8000/`

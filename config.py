from dotenv import load_dotenv
import os

load_dotenv()

DOCTOR_USERNAME = os.getenv("doctor_username")
DOCTOR_PASSWORD = os.getenv("doctor_password")

MYSQL_USER = os.getenv("mysql_user")
MYSQL_PASSWORD = os.getenv("mysql_password")

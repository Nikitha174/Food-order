# nltk_download.py — Run this once before first deployment to pre-download NLTK data
# Usage: python nltk_download.py
import nltk
print("Downloading NLTK data...")
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')
print("NLTK data downloaded successfully!")

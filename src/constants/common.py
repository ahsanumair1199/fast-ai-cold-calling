from dotenv import load_dotenv
import os

if load_dotenv():
    print('Loading .env variables')

# ENV VARIABLES
ENVIRONMENT = os.environ.get('ENVIRONMENT')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
SERVER_ADDRESS = os.environ.get('SERVER_ADDRESS')
REGION = os.environ.get('REGION')
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
API_TITLE = os.environ['API_TITLE']
API_DESCRIPTION = os.environ['API_DESCRIPTION']
API_VERSION = os.environ['API_VERSION']
REGION = os.environ['REGION']
PORT = int(os.environ.get('PORT', 8000))
FAST_API_SECRET_KEY = os.environ['FAST_API_SECRET_KEY']

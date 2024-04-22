# Description
A FastAPI application for the voice call bot. The AI agent calls the customer and discuss the product deals with him. It is a cold call system. The latency of the system is less than 1 second. It takes the prompt from the API and calls the customer according to the prompt and instruction given during the API calling. You can use the pre-trained model for the better responses. It contains all of the voices given in the elevenslab platform. You can choose a voice before making a call to the customer.
It is realtime and it use websockets for the realtime communication.

# Tool & Technologies Used
1. Python3
2. FastAPI
3. SQLModel ORM
4. OpenAI (for answer generation)
5. AWS Transcribe (for transcription)
6. Twilio (for calling)
7. Elevenslab (for text to voice conversion)

# Core Features
1. JWT Authentication system in FastAPI
2. Handle multiple connections of the system users in websockets
3. System user can choose a voice before making a call to the customer
4. User can see and listen all the available voices and choose one of them
5. User can upload an excel file of customer contacts for the campaign call (one call at a time)

# What is remaining
1. Payment gateway implementaion
2. Frontend
3. PostgreSQL for database

# Major Issues In This
1. The AWS Transcribe generates the transcription from background noise sometimes, that transcription goes to text generation model and user get's the unexpected response. It can be solved by implementing the noise reduction techniques.

# Installation & Setup
1. Install the libraries from requirements.txt file
2. Create a sqlite3 db file in project root directory
3. Rename example.env file into .env and put your secret keys there
4. Run the server by `uvicorn src.main:app`
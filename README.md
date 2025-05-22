# EmotiBot

EmotiBot is an emotionally intelligent chatbot that analyzes user messages for emotional content and responds with appropriate avatar expressions. The application demonstrates enterprise-level software design with a focus on scalability, security, and cloud-native architecture.

## Features

- Real-time emotion analysis of user messages
- Animated avatar that changes based on detected emotions
- Secure user authentication
- Scalable cloud-based architecture
- Comprehensive logging and monitoring

## Setup Instructions

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install requirements: `pip install -r requirements.txt`
5. Set up environment variables (see .env.example)
6. Run the application: `python app.py`

## Project Structure

```
EmotiBot/
├── app.py                  # Main application entry point
├── config.py               # Configuration settings
├── requirements.txt        # Dependencies
├── .env.example            # Example environment variables
├── static/                 # Static files (CSS, JS, images)
├── templates/              # HTML templates
├── models/                 # Data models
├── services/               # Business logic services
│   ├── emotion_service.py  # Emotion detection service
│   └── auth_service.py     # Authentication service
├── controllers/            # API controllers
├── tests/                  # Test suite
└── docs/                   # Documentation
```

## Technologies Used

- Python/Flask: Backend API and web server
- TextBlob/NLTK: Natural language processing for emotion detection
- JWT: Secure authentication
- Docker: Containerization
- Cloud Services: Deployment and scaling
- CI/CD: Automated testing and deployment 
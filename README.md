# Andikar AI Frontend

A Flask-based web application for humanizing AI-generated text and detecting AI content.

## Features

- **Content Humanizer**: Transform AI-generated text into natural human-like writing
- **AI Detector**: Check if your content will be flagged as AI-generated
- **User Management**: Register, login, and manage user accounts
- **Subscription Plans**: Free, Basic, and Premium tiers with different word limits
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Flask**: Web framework for the application
- **Jinja2**: Template engine
- **CSS**: Custom styling with glassmorphism design
- **JavaScript**: Client-side interactivity
- **Font Awesome**: For icons and visual elements

## Deployment on Railway

This application is configured for easy deployment on Railway.com. When you deploy to Railway, it will:

1. Automatically detect the Python application
2. Install the dependencies from requirements.txt
3. Start the application using the Procfile configuration
4. Assign a public URL to your application

### Deployment Steps

1. Fork or clone this repository to your GitHub account
2. Go to [Railway.app](https://railway.app/) and sign in
3. Click "New Project" and select "Deploy from GitHub repo"
4. Select this repository from the list
5. Railway will automatically detect and deploy the application
6. Once deployed, you can access your application at the URL provided by Railway

## Local Development

To run this application locally:

```bash
# Clone the repository
git clone https://github.com/granitevolition/andikar-frontend.git
cd andikar-frontend

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The application will be available at http://localhost:5000

## Environment Variables

You can customize the application behavior with these environment variables:

- `SECRET_KEY`: For session security (generated randomly by default)
- `PORT`: Port to run the application (defaults to 5000)

## Demo Account

For testing purposes, a demo account is automatically created:

- Username: `demo`
- Password: `demo`
- Plan: Basic (1,500 words limit)

## Project Structure

```
andikar-frontend/
├── app.py               # Main Flask application
├── config.py            # Configuration settings
├── models.py            # Data models
├── utils.py             # Utility functions
├── templates.py         # HTML templates
├── static/              # Static assets
│   ├── style.css        # CSS styles
│   └── script.js        # JavaScript code
├── requirements.txt     # Dependencies
├── Procfile             # For Railway deployment
├── runtime.txt          # Python version specification
└── README.md            # Documentation
```

## License

MIT

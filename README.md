# MessageGuard — SMS & Email Spam Detector

MessageGuard is a web application that classifies text messages as **Spam** or **Ham (likely safe)** using a machine-learning model.

## Features

- Email-based signup and signin with OTP verification
- Spam or ham prediction for a message
- Batch message analysis
- Model metrics and prediction feedback
- Responsive web interface

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, JavaScript
- **Machine learning:** scikit-learn
- **Database:** SQLite locally; PostgreSQL can be configured with `DATABASE_URL`
- **Email verification:** EmailJS

## Run Locally

### 1. Install requirements

From the project root, create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
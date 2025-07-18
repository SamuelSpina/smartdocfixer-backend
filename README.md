# SmartDocFixer Backend

## Setup Instructions

1. **Install Python 3.8+**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Get OpenAI API Key:**
   - Go to https://platform.openai.com/api-keys
   - Create new secret key
   - Add it to `.env` file

4. **Run locally:**
```bash
python main.py
```

5. **Test the API:**
   - Go to http://localhost:8000/docs
   - Upload a .docx file using the `/fix-document/` endpoint

## Deployment

Deploy to Render, Railway, or any Python hosting service.
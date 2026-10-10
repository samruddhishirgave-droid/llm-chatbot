# अभ्यास मित्र - LLM Chatbot

Gemini API वर चालणारा multi-turn चॅटबॉट (Flask + HTML).

## Features
- प्रति-संभाषण history (conversation_id)
- Context management: शेवटचे 10 मेसेज ठेवतो, जुन्या मेसेजचा running summary बनवून system prompt मध्ये जोडतो
- System prompt: मैत्रीपूर्ण शिक्षक
- API error handling (rate limit, network, empty response)

## Setup
1. `pip install -r requirements.txt`
2. `.env.example` कॉपी करून `.env` बनवा आणि `GEMINI_API_KEY` टाका
3. `python app.py`
4. http://127.0.0.1:5000 उघडा

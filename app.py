import os, uuid
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
app = Flask(__name__)

MODEL = "gemini-2.5-flash"
MAX_MESSAGES = 10          # keep only the last N messages in full
conversations = {}         # conversation_id -> {"history": [], "summary": ""}

SYSTEM_PROMPT = """You are 'Study Buddy', a friendly tutor.
- Explain concepts in simple words with short examples.
- Reply in the same language the user writes in.
- Keep answers concise and clear.
- Politely decline questions that are not related to studying or learning.
- If you don't know something, say so honestly instead of guessing."""

def summarise(old, prev):
    text = "\n".join(f"{m['role']}: {m['text']}" for m in old)
    prompt = (
        f"Previous summary: {prev}\n\n"
        f"New conversation:\n{text}\n\n"
        "Write an updated summary in 5-6 sentences. "
        "Keep the user's name and any important facts."
    )
    return client.models.generate_content(model=MODEL, contents=prompt).text

def to_contents(history):
    return [types.Content(role=m["role"], parts=[types.Part(text=m["text"])]) for m in history]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    cid = data.get("conversation_id") or str(uuid.uuid4())
    if not msg:
        return jsonify(error="Please type a message."), 400

    convo = conversations.setdefault(cid, {"history": [], "summary": ""})
    convo["history"].append({"role": "user", "text": msg})

    try:
        # Context management: move older messages into a running summary
        if len(convo["history"]) > MAX_MESSAGES:
            overflow = convo["history"][:-MAX_MESSAGES]
            convo["summary"] = summarise(overflow, convo["summary"])
            convo["history"] = convo["history"][-MAX_MESSAGES:]

        system = SYSTEM_PROMPT
        if convo["summary"]:
            system += f"\n\nSummary of the earlier conversation:\n{convo['summary']}"

        r = client.models.generate_content(
            model=MODEL,
            contents=to_contents(convo["history"]),
            config=types.GenerateContentConfig(system_instruction=system),
        )
        reply = r.text or "Sorry, I couldn't generate a reply. Please try again."
        convo["history"].append({"role": "model", "text": reply})
        return jsonify(reply=reply, conversation_id=cid)

    except errors.APIError as e:
        print("API ERROR:", e.code, e)
        convo["history"].pop()   # remove the failed user message
        err = ("Too many requests right now. Please wait a moment and try again."
               if e.code == 429
               else "There was a problem with the AI service. Please try again.")
        return jsonify(error=err), 502
    except Exception as e:
        print("ERROR:", e)
        convo["history"].pop()
        return jsonify(error="Network problem. Please check your connection and try again."), 503

@app.route("/reset", methods=["POST"])
def reset():
    cid = (request.get_json(silent=True) or {}).get("conversation_id")
    conversations.pop(cid, None)
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(debug=True)


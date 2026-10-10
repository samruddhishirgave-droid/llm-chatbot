import os, uuid
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
app = Flask(__name__)

MODEL = "gemini-2.5-flash"
MAX_MESSAGES = 10
conversations = {}

SYSTEM_PROMPT = """तू 'अभ्यास मित्र' नावाचा मैत्रीपूर्ण शिक्षक आहेस.
वापरकर्ता ज्या भाषेत लिहील त्याच भाषेत सोप्या शब्दांत, उदाहरणांसह उत्तर दे.
अभ्यासाशी संबंधित नसलेल्या प्रश्नांना नम्रपणे नकार दे."""

def summarise(old, prev):
    text = "\n".join(f"{m['role']}: {m['text']}" for m in old)
    prompt = f"आधीचा सारांश: {prev}\n\nनवीन संभाषण:\n{text}\n\nसर्वाचा 5-6 वाक्यांत सारांश लिही. वापरकर्त्याचे नाव आणि महत्त्वाची तथ्ये ठेव."
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
        return jsonify(error="कृपया मेसेज लिहा."), 400

    convo = conversations.setdefault(cid, {"history": [], "summary": ""})
    convo["history"].append({"role": "user", "text": msg})

    try:
        if len(convo["history"]) > MAX_MESSAGES:
            overflow = convo["history"][:-MAX_MESSAGES]
            convo["summary"] = summarise(overflow, convo["summary"])
            convo["history"] = convo["history"][-MAX_MESSAGES:]

        system = SYSTEM_PROMPT
        if convo["summary"]:
            system += f"\n\nआधीच्या संभाषणाचा सारांश:\n{convo['summary']}"

        r = client.models.generate_content(
            model=MODEL,
            contents=to_contents(convo["history"]),
            config=types.GenerateContentConfig(system_instruction=system),
        )
        reply = r.text or "माफ करा, उत्तर तयार झाले नाही."
        convo["history"].append({"role": "model", "text": reply})
        return jsonify(reply=reply, conversation_id=cid)

    except errors.APIError as e:
        print('API ERROR:', e.code, e)
        print("API ERROR:", e.code, e)
        convo["history"].pop()
        err = ("खूप विनंत्या आहेत, थोड्या वेळाने प्रयत्न करा." if e.code == 429
               else "API मध्ये समस्या आली. पुन्हा प्रयत्न करा.")
        return jsonify(error=err), 502
    except Exception:
        convo["history"].pop()
        return jsonify(error="नेटवर्क समस्या आली. पुन्हा प्रयत्न करा."), 503

@app.route("/reset", methods=["POST"])
def reset():
    cid = (request.get_json(silent=True) or {}).get("conversation_id")
    conversations.pop(cid, None)
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(debug=True)


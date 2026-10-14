# 🔎 MemorySleuth
### Evidence-Driven Investigation of Memory Poisoning in AI Agents

MemorySleuth is a cybersecurity prototype that demonstrates how suspicious stored memories can influence an AI agent's decisions and how an independent security policy can prevent an unapproved action.

## 🚨 Problem
AI agents may retrieve untrusted or malicious content from stored memories or imported documents. This content can influence future decisions if it is not checked.

## 💡 Our Solution
MemorySleuth provides a controlled simulation to:
- Display trusted and suspicious memories.
- Compare agent behavior with and without suspicious memory.
- Record retrieved memory IDs and attempted actions.
- Apply an independent policy to block an unapproved recipient.
- Replay the scenario and inspect the evidence log.

## ⚙️ Tech Stack
- Python
- Streamlit

## ▶️ Run Locally
1. Clone this repository.
2. Install dependencies:
   `python -m pip install -r requirements.txt`
3. Start the application:
   `python -m streamlit run app.py`

## 🧪 Demonstration
- **Suspicious memory included:** the simulated agent attempts to use an unapproved recipient; the policy blocks it.
- **Suspicious memory excluded:** the simulated agent uses the approved recipient; the policy allows it.

## 🔐 Scope and Limitations
This is a deterministic educational prototype, not a production AI security detector. It does not send emails, execute external actions, or use a live AI model. Its results demonstrate the scripted scenario only.

## 👥 Project
Developed for the Mitigata CyberForge Hackathon 2026.

**Project:** MemorySleuth  
**Theme:** AI & Cybersecurity
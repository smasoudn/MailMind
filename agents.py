import os
import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from openai import OpenAI

from state import MailMindState

# Initialize LLM
def get_llm():
    return ChatOpenAI(model="gpt-4o", temperature=0.2)

# --- Agent 1: Routing Agent ---
class RoutingDecision(BaseModel):
    is_valid: bool = Field(description="Is the prompt a valid request to write an email?")
    reason: str = Field(description="Reason if not valid")

def routing_agent(state: MailMindState) -> dict:
    # --- MODERATION CHECK ON USER INPUT ---
    try:
        client = OpenAI()
        mod_res = client.moderations.create(input=state["raw_prompt"])
        if mod_res.results[0].flagged:
            return {"routing_decision": "reject", "error": "Your input violates our safety and moderation policies."}
    except Exception as e:
        return {"routing_decision": "error", "error": f"Moderation check failed: {str(e)}"}

    llm = get_llm().with_structured_output(RoutingDecision)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the routing agent for an email assistant. Determine if the user's input is a valid request to write an email."),
        ("user", "{input}")
    ])
    chain = prompt | llm
    try:
        res = chain.invoke({"input": state["raw_prompt"]})
        if res.is_valid:
            return {"routing_decision": "continue", "error": None}
        else:
            return {"routing_decision": "reject", "error": res.reason}
    except Exception as e:
        return {"routing_decision": "error", "error": str(e)}

# --- Agent 2: Input Parser ---
class ParsedInput(BaseModel):
    key_points: list[str] = Field(description="Key information to include in the email")
    urgency: str = Field(description="Urgency level inferred from prompt")

def input_parser(state: MailMindState) -> dict:
    llm = get_llm().with_structured_output(ParsedInput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract key information to include in an email from the raw prompt."),
        ("user", "{input}")
    ])
    chain = prompt | llm
    res = chain.invoke({"input": state["raw_prompt"]})
    return {"parsed_input": res.model_dump()}

# --- Agent 3: Intent Detector ---
class IntentOutput(BaseModel):
    intent: str = Field(description="The primary goal or intent of the email (e.g., Request, Update, Apology, Inquiry)")

def intent_detector(state: MailMindState) -> dict:
    llm = get_llm().with_structured_output(IntentOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Identify the primary intent of this email request."),
        ("user", "{input}")
    ])
    chain = prompt | llm
    res = chain.invoke({"input": state["raw_prompt"]})
    return {"intent": res.intent}

# --- Agent 4: Personalization ---
def personalization_agent(state: MailMindState) -> dict:
    # Load profile data
    profiles_path = os.path.join(os.path.dirname(__file__), "profiles.json")
    try:
        with open(profiles_path, "r") as f:
            profiles = json.load(f)
    except Exception:
        profiles = {"senders": {}, "recipients": {}}
        
    sender_id = state.get("sender_id", "user_1")
    recipient_type = state.get("recipient_type", "colleague").lower()
    
    sender_data = profiles.get("senders", {}).get(sender_id, {})
    recipient_data = profiles.get("recipients", {}).get(recipient_type, {})
    
    context = {
        "sender_name": sender_data.get("name", "User"),
        "sender_role": sender_data.get("role", ""),
        "sender_company": sender_data.get("company", ""),
        "sender_style": sender_data.get("style_preferences", ""),
        "sender_sign_off": sender_data.get("sign_off", ""),
        "recipient_guidance": recipient_data.get("guidance", "")
    }
    return {"personalized_context": context}

# --- Agent 5: Draft Writer ---
def draft_writer(state: MailMindState) -> dict:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert email writer. Draft an email based on the following context.\n"
                   "Intent: {intent}\n"
                   "Key points: {key_points}\n"
                   "Recipient guidance: {recipient_guidance}\n"
                   "Do not include the sign-off block yet."),
        ("user", "Write the draft.")
    ])
    chain = prompt | llm | StrOutputParser()
    
    context = state["personalized_context"]
    res = chain.invoke({
        "intent": state["intent"],
        "key_points": ", ".join(state["parsed_input"]["key_points"]),
        "recipient_guidance": context["recipient_guidance"]
    })
    return {"draft": res}

# --- Agent 6: Tone Stylist ---
def tone_stylist(state: MailMindState) -> dict:
    llm = get_llm()
    context = state["personalized_context"]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Refine the following email draft to strictly match the requested tone: '{tone}'.\n"
                   "Additionally, incorporate the sender's personal style preferences: '{style}'.\n"
                   "Append the following sign-off at the end:\n{sign_off}\n"
                   "Return only the final email text."),
        ("user", "Draft to refine:\n{draft}")
    ])
    chain = prompt | llm | StrOutputParser()
    res = chain.invoke({
        "tone": state["tone"],
        "style": context["sender_style"],
        "sign_off": context["sender_sign_off"],
        "draft": state["draft"]
    })
    return {"tone_styled_draft": res}

# --- Agent 7: Review Validator ---
class ValidationResult(BaseModel):
    is_valid: bool = Field(description="Is the email coherent, grammatically correct, and tone-aligned?")
    feedback: str = Field(description="Feedback if invalid, otherwise empty string")

def review_validator(state: MailMindState) -> dict:
    retry_count = state.get("retry_count", 0)
    
    # 1. Moderation Check on Draft
    try:
        client = OpenAI()
        mod_res = client.moderations.create(input=state["tone_styled_draft"])
        if mod_res.results[0].flagged:
            if retry_count >= 2:
                return {"final_email": state["tone_styled_draft"], "validation_feedback": "Safety Violation (Max retries reached)"}
            return {"validation_feedback": "The generated draft violated safety policies. Please rewrite it completely.", "retry_count": retry_count + 1}
    except Exception:
        pass # Proceed to LLM validation if moderation check fails
        
    # 2. LLM Quality Validation
    llm = get_llm().with_structured_output(ValidationResult)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Review the generated email. Ensure it addresses the user's key points, intent, and requested tone '{tone}'. Check for grammar and coherence."),
        ("user", "Intent: {intent}\nKey points: {key_points}\n\nEmail Draft:\n{draft}")
    ])
    chain = prompt | llm
    res = chain.invoke({
        "tone": state["tone"],
        "intent": state["intent"],
        "key_points": ", ".join(state["parsed_input"]["key_points"]),
        "draft": state["tone_styled_draft"]
    })
    
    if res.is_valid or retry_count >= 2:
        return {"final_email": state["tone_styled_draft"], "validation_feedback": "Passed" if res.is_valid else "Max retries reached"}
    else:
        return {"validation_feedback": res.feedback, "retry_count": retry_count + 1}

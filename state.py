from typing import TypedDict, Optional

class MailMindState(TypedDict):
    # Inputs
    raw_prompt: str
    tone: str
    recipient_type: str
    sender_id: str
    
    # Processing state
    parsed_input: Optional[dict]
    intent: Optional[str]
    personalized_context: Optional[dict]
    
    # Generation state
    draft: Optional[str]
    tone_styled_draft: Optional[str]
    validation_feedback: Optional[str]
    final_email: Optional[str]
    
    # Routing / Errors
    routing_decision: Optional[str]
    error: Optional[str]
    retry_count: int

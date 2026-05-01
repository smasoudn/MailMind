from langgraph.graph import StateGraph, START, END
from state import MailMindState
from agents import (
    routing_agent,
    input_parser,
    intent_detector,
    personalization_agent,
    draft_writer,
    tone_stylist,
    review_validator
)

def create_graph():
    builder = StateGraph(MailMindState)
    
    # Add nodes
    builder.add_node("routing", routing_agent)
    builder.add_node("parser", input_parser)
    builder.add_node("intent", intent_detector)
    builder.add_node("personalization", personalization_agent)
    builder.add_node("draft", draft_writer)
    builder.add_node("tone", tone_stylist)
    builder.add_node("review", review_validator)
    
    # Edges
    builder.add_edge(START, "routing")
    
    def route_from_routing(state: MailMindState):
        if state.get("routing_decision") == "continue":
            return "parser"
        return END

    builder.add_conditional_edges("routing", route_from_routing)
    
    builder.add_edge("parser", "intent")
    builder.add_edge("intent", "personalization")
    builder.add_edge("personalization", "draft")
    builder.add_edge("draft", "tone")
    builder.add_edge("tone", "review")
    
    def route_from_review(state: MailMindState):
        if state.get("final_email"):
            return END
        return "draft"  # Loop back if validation failed
        
    builder.add_conditional_edges("review", route_from_review)
    
    return builder.compile()

app_graph = create_graph()




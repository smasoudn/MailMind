import pytest
from langgraph.graph import END
from graph import route_from_routing, route_from_review

def test_route_from_routing():
    state = {"routing_decision": "continue"}
    assert route_from_routing(state) == "parser"
    
    state = {"routing_decision": "reject"}
    assert route_from_routing(state) == END

def test_route_from_review():
    state = {"final_email": "This is a valid email."}
    assert route_from_review(state) == END
    
    state = {"final_email": None}
    assert route_from_review(state) == "draft"

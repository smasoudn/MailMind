import os
os.environ["OPENAI_API_KEY"] = "dummy"

from unittest.mock import patch
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class Dummy(BaseModel):
    val: str

def test_mocking():
    llm = ChatOpenAI(model="gpt-4o").with_structured_output(Dummy)
    prompt = ChatPromptTemplate.from_messages([("user", "test")])
    chain = prompt | llm
    
    with patch('langchain_core.runnables.RunnableSequence.invoke') as mock_invoke:
        mock_invoke.return_value = Dummy(val="mocked")
        res = chain.invoke({})
        print(f"Result: {res.val}")

if __name__ == "__main__":
    test_mocking()

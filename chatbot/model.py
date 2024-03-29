from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain, ConversationChain
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
import os

load_dotenv()

model = ChatGoogleGenerativeAI(
    google_api_key=os.environ.get("GEMINI_KEY"), model="gemini-pro")

memory = ConversationBufferMemory()
llm = ConversationChain(llm=model, memory=memory, verbose=False)

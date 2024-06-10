import secrets
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain.prompts import ChatPromptTemplate
from model import create_llm
from templates import greeting_prompt, detail_template, generate_template
from database import get_learning_paths_collection

app = FastAPI()

origins = ["http://localhost:3000", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

learning_paths_collection = get_learning_paths_collection()
session_store = defaultdict(lambda: dict())


def get_llm_memory(user_id: str):
    """Retrieve or create the LLM and memory for a given user."""
    if user_id not in session_store:
        session_store[user_id]["llm"] = create_llm()
        session_store[user_id]["chat_history"] = []
    return session_store[user_id]


@app.get("/alive")
def health_check():
    return {"isSuccess": True, "aiResponse": "Stayin' Alive oh oh oh!"}


@app.post("/restart")
async def restart(request: Request):
    """Clear the session memory for a given user."""
    try:
        body = await request.json()
        user_id = body.get('studentId')
        if user_id in session_store:
            del session_store[user_id]
        return {"isSuccess": True, "aiResponse": "Memory is cleared!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dump")
async def dump_chat_history(request: Request):
    """Dump the chat history of the session for a given user."""
    try:
        body = await request.json()
        user_id = body.get('studentId')
        if user_id not in session_store:
            raise HTTPException(
                status_code=404, detail="User session not found")
        return {"isSuccess": True, "userId": user_id, "chat_history": session_store[user_id]["chat_history"]}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/greet")
async def greet(request: Request):
    """Generate a greeting response for a given user."""
    try:
        body = await request.json()
        user_id = body.get('studentId')
        llm, _ = get_llm_memory(user_id)["llm"]
        greeting_response = llm.predict(input=greeting_prompt)
        session_store[user_id]["chat_history"].append(greeting_response)
        return {"isSuccess": True, "aiResponse": greeting_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})


@app.post("/detail")
async def detail(request: Request):
    """Generate a detailed response based on the user's input."""
    try:
        body = await request.json()
        user_id = body.get('studentId')
        student_prompt = body.get('studentResponse')
        session_store[user_id]["chat_history"].append(student_prompt)

        llm, _ = get_llm_memory(user_id)["llm"]
        prompt_template = ChatPromptTemplate.from_template(detail_template)
        cooked_prompt = prompt_template.format_messages(
            student_prompt=student_prompt)
        response = llm.predict(input=cooked_prompt[0].content)
        session_store[user_id]["chat_history"].append(response)
        return {"isSuccess": True, "aiResponse": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})


@app.post("/generate")
async def generate(request: Request):
    """Generate a response based on the student's answers."""
    try:
        body = await request.json()
        user_id = body.get('studentId')
        student_answers = body.get('studentResponse')
        session_store[user_id]["chat_history"].append(student_answers)

        llm, _ = get_llm_memory(user_id)["llm"]
        prompt_template = ChatPromptTemplate.from_template(generate_template)
        cooked_prompt = prompt_template.format_messages(
            student_answers=student_answers)
        response = llm.predict(input=cooked_prompt[0].content)
        session_store[user_id]["chat_history"].append(response)
        return {"isSuccess": True, "aiResponse": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})


@app.post("/save")
async def save_last_response(request: Request):
    """Save the last response in the chat history to the database."""
    try:
        body = await request.json()
        user_id = body.get('studentId')
        learning_path_title = body.get('learningPathTitle')

        if user_id not in session_store:
            raise HTTPException(
                status_code=404, detail="User session not found")

        chat_history = session_store[user_id]["chat_history"]
        if not chat_history:
            raise HTTPException(
                status_code=400, detail="No chat history to save")

        learning_path_id = secrets.token_hex(5)
        last_response = chat_history[-1]

        user_record = learning_paths_collection.find_one(
            {"studentId": user_id})

        if user_record:
            old_chat_history = user_record.get("chatHistory", [])
            old_chat_history.extend(chat_history)
            user_record["chatHistory"] = old_chat_history
            session_store[user_id]["chat_history"] = []
            user_record["learningPaths"].append({
                    "learningPathId": learning_path_id,
                    "learningPathTitle": learning_path_title,
                    "content": last_response
                })
            learning_paths_collection.update_one(
                {"studentId": user_id}, {"$set": user_record})
        else:
            learning_paths_collection.insert_one({
                "studentId": user_id,
                "chatHistory": chat_history,
                "learningPaths": [
                    {
                        "learningPathId": learning_path_id,
                        "learningPathTitle": learning_path_title,
                        "content": last_response
                    }
                ]
            })
            session_store[user_id]["chat_history"] = []

        return {"isSuccess": True, "aiResponse": "Your learning path is saved, Be sure to follow it!"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})


@app.get("/chat-history")
async def get_chat_history(request: Request):
    """Retrieve the chat history for a given user."""
    try:
        body = await request.json()
        student_id = body.get("studentId")
        user_record = learning_paths_collection.find_one(
            {"studentId": student_id})
        if not user_record:
            return {"isSuccess": True, "chatHistory": []}
        chat_history = user_record.get("chatHistory", [])
        return {"isSuccess": True, "chatHistory": chat_history}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})


@app.get("/learning-paths")
async def get_learning_paths(request: Request):
    """Retrieve all learning paths for a given user."""
    try:
        body = await request.json()
        student_id = body.get("studentId")
        user_record = learning_paths_collection.find_one(
            {"studentId": student_id})
        if not user_record:
            return {"isSuccess": True, "learningPaths": []}
        learning_paths = user_record.get("learningPaths", [])
        return {"isSuccess": True, "learningPaths": learning_paths}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})


@app.get("/learning-paths/{learning_path_id}")
async def get_learning_path(learning_path_id: str, request: Request):
    """Retrieve a specific learning path for a given user."""
    try:
        body = await request.json()
        student_id = body.get("studentId")
        user_record = learning_paths_collection.find_one(
            {"studentId": student_id})
        if not user_record:
            raise HTTPException(
                status_code=404, detail="User session not found")

        for path in user_record.get("learningPaths", []):
            if path["learningPathId"] == learning_path_id:
                return {"isSuccess": True, "learningPath": path}
        raise HTTPException(status_code=404, detail="Learning path not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})


@app.delete("/learning-path/{learning_path_id}")
async def delete_learning_path(learning_path_id: str, request: Request):
    try:
        body = await request.json()
        student_id = body.get("studentId")
        user_record = learning_paths_collection.find_one(
            {"studentId": student_id})
        if not user_record:
            raise HTTPException(
                status_code=404, detail="User session not found")

        updated_paths = []
        for path in user_record.get("learningPaths", []):
            if path["learningPathId"] != learning_path_id:
                updated_paths.append(path)

        learning_paths_collection.update_one({"studentId": student_id}, {
                                             "$set": {"learningPaths": updated_paths}})
        return {"isSuccess": True, "aiResponse": "Learning path deleted!"}
    except HTTPException as e:
        raise HTTPException(status_code=500, detail={
                            "isSuccess": False, "error": str(e)})

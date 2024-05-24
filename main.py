import secrets
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from langchain.prompts import ChatPromptTemplate
from model import create_llm
from templates import greeting_prompt, detail_template, generate_template
from database import get_learning_paths_collection

app = FastAPI()

learning_paths_collection = get_learning_paths_collection()
session_store = defaultdict(lambda: dict())


def get_llm_memory(user_id: str):
    if user_id not in session_store:
        session_store[user_id]["llm"] = create_llm()
        session_store[user_id]["chat_history"] = []
    return session_store[user_id]


@app.get("/alive")
def health_check():
    return {"aiResponse": "Stayin Alive oh oh oh!"}


@app.get("/restart")
async def restart(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    if user_id in session_store:
        del session_store[user_id]

    return {"aiResponse": "Memory is cleared!"}


@app.get("/memory")
async def get_memory(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    if user_id not in session_store:
        raise HTTPException(status_code=404, detail="User session not found")
    _, memory = get_llm_memory(user_id)

    return {"memory": memory.load_memory_variables({})}

@app.get("/dump")
async def dump_chat_history(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    if user_id not in session_store:
        raise HTTPException(status_code=404, detail="User session not found")

    return {"userId": user_id, "chat_history": session_store[user_id]["chat_history"]}


@app.post("/greet")
async def greet(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    llm, _ = get_llm_memory(user_id)["llm"]
    greeting_response = llm.predict(input=greeting_prompt)
    session_store[user_id]["chat_history"].append(greeting_response)

    return {"aiResponse": greeting_response}


@app.post("/detail")
async def detail(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    student_prompt = body.get('topic')
    session_store[user_id]["chat_history"].append(student_prompt)

    llm, _ = get_llm_memory(user_id)["llm"]
    prompt_template = ChatPromptTemplate.from_template(detail_template)
    cooked_prompt = prompt_template.format_messages(
        student_prompt=student_prompt)
    response = llm.predict(input=cooked_prompt[0].content)
    session_store[user_id]["chat_history"].append(response)

    return {"aiResponse": response}


@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    student_answers = body.get('studentAnswers')
    session_store[user_id]["chat_history"].append(student_answers)

    llm, _ = get_llm_memory(user_id)["llm"]
    prompt_template = ChatPromptTemplate.from_template(generate_template)
    cooked_prompt = prompt_template.format_messages(
        student_answers=student_answers)
    response = llm.predict(input=cooked_prompt[0].content)
    session_store[user_id]["chat_history"].append(response)

    return {"aiResponse": response}

@app.post("/save")
async def save_last_response(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    learning_path_title = body.get('learningPathTitle')

    if user_id not in session_store:
        raise HTTPException(status_code=404, detail="User session not found")

    chat_history = session_store[user_id]["chat_history"]
    if not chat_history:
        raise HTTPException(status_code=400, detail="No chat history to save")

    learning_path_id = secrets.token_hex(5)
    last_response = chat_history[-1]

    user_record = learning_paths_collection.find_one({"studentId": user_id})

    if user_record:
        updated = False
        for path in user_record["learningPaths"]:
            if path["learningPathId"] == learning_path_id:
                path["content"].append(last_response)
                updated = True
                break
        if not updated:
            user_record["learningPaths"].append({
                "learningPathId": learning_path_id,
                "learningPathTitle": learning_path_title,
                "content": [last_response]
            })
        learning_paths_collection.update_one({"studentId": user_id}, {"$set": user_record})
    else:
        learning_paths_collection.insert_one({
            "studentId": user_id,
            "learningPaths": [
                {
                    "learningPathId": learning_path_id,
                    "learningPathTitle": learning_path_title,
                    "content": [last_response]
                }
            ]
        })

    return {"aiResponse": "Response saved!"}

@app.get("/learning_paths")
async def get_learning_paths(request: Request):
    body = await request.json()
    user_id = body.get('studentId')
    user_record = learning_paths_collection.find_one({"studentId": user_id})
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")
    
    learning_paths = user_record.get("learningPaths", [])
    return {"learningPaths": learning_paths}

@app.get("/learning_paths/{learning_path_id}")
async def get_learning_path(learning_path_id: str, request: Request):
    body = await request.json()
    student_id = body.get('studentId')
    user_record = learning_paths_collection.find_one({"studentId": student_id})
    if not user_record:
        raise HTTPException(status_code=404, detail="User session not found")

    for path in user_record.get("learningPaths", []):
        if path["learningPathId"] == learning_path_id:
            return {"learningPath": path}

    raise HTTPException(status_code=404, detail="Learning path not found")
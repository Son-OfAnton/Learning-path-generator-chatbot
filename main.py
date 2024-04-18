from fastapi import FastAPI, Request
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from model import llm, memory, model
from templates import greeting_prompt, detail_template, generate_template

app = FastAPI()


@app.get("/alive")
def health_check():
    return {"aiResponse": "I am a alive!"}


@app.get("/restart")
def restart():
    memory.clear()
    return {"aiResponse": "Memory is cleared!"}


@app.get("/memory")
def get_memory():
    return {"memory": memory.load_memory_variables({})}


@app.get("/greet")
def greet():
    greeting_response = llm.predict(input=greeting_prompt)
    return {"aiResponse": greeting_response}


@app.post("/detail")
async def detail(request: Request):
    body = await request.json()
    student_prompt = body.get('topic')

    prompt_template = ChatPromptTemplate.from_template(detail_template)
    cooked_prompt = prompt_template.format_messages(
        student_prompt=student_prompt)
    response = llm.predict(input=cooked_prompt[0].content)

    return {"aiResponse": response}


@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    student_answers = body.get('studentAnswers')

    prompt_template = ChatPromptTemplate.from_template(generate_template)
    cooked_prompt = prompt_template.format_messages(
        student_answers=student_answers)
    response = llm.predict(input=cooked_prompt[0].content)

    return {"aiResponse": response}


@app.post("/preferences")
async def preferences(request: Request):
    body = await request.json()
    student_prompt = body.get('topic')

    prerequisites = ResponseSchema(
        name="prerequisites", description="Ask him his comfortability on the some prerequisites you think are important to know.")
    studyTime = ResponseSchema(
        name="studyTime", description="Ask him how much time will he dedicate to finish studying the topic.")
    learningStyle = ResponseSchema(
        name="learningStyle", description="Ask him about his learning style. Whether he is Visual learner, hands-on learner or an auditory learner ?")
    learningResources = ResponseSchema(
        name="learningResources", description="Ask him which type of learning resource he prefers ? Books, Online courses, YouTube video ?")

    response_schemas = [prerequisites, studyTime,
                        learningStyle, learningResources]
    output_parser = StructuredOutputParser.from_response_schemas(
        response_schemas)
    format_instructions = output_parser.get_format_instructions()
    print(f'>> {format_instructions}')

    template = """Now the student needs help with the topic given later specified as {student_prompt}.
                 You will assist the student by asking the following questions to understand his/her preferences.: 
                 Please remember you only ask him these questions\n

                - What is your comfort level with the prerequisites for the topic?\n
                - How much time do you plan to dedicate to studying this topic?\n
                - What is your preferred learning style? Are you a visual learner, hands-on learner, or auditory learner?\n
                - Which type of learning resource do you prefer ? Books, online courses, YouTube videos ?\n 
                
                Format the output as only JSON with the following keys:
                - prerequisites
                - studyTime
                - learningStyle
                - learningResources

                student_prompt: {student_prompt}

                {format_instructions}
                """

    prompt_template = ChatPromptTemplate.from_template(template)
    cooked_prompt = prompt_template.format_messages(
        student_prompt=student_prompt, format_instructions=format_instructions)
    response = llm.predict(input=cooked_prompt)
    response_dict = output_parser.parse(response)

from fastapi import FastAPI, Request
from chatbot.model import llm, memory, model
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser

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
    greeting_prompt = """You are CustomEd bot. You will help students to understand the 
                        difficult topics they face by generating a learning path form them. 
                        Now you are meeting one student so greet him politely and tell him about youself.
                        
                        Formatting rules:
                        - Format the output with not asterisks.
                        """

    greeting_response = llm.predict(input=greeting_prompt)
    return {"aiResponse": greeting_response}


@app.post("/detail")
async def detail(request: Request):
    body = await request.json()
    student_prompt = body.get('topic')

    template = """Now the student needs help with the topic given later specified as {student_prompt}.
                 You will assist the student by asking the following questions to understand his/her preferences.: 
                 Please remember you only ask him these questions and say no more.\n

                Ask him comfortability on some prerequisites you think are important ?\n
                Ask him how much time does he plan to dedicate to studying this topic?\n
                Ask him his preferred learning style? Is he a visual learner, hands-on learner, or auditory learner?\n
                Ask him which type of learning resource he prefers ? Books, online courses, YouTube videos ?\n    

                Formatting rules:
                - Format the output with not asterisks.
                - Format the output with proper bullet points if necessary.               
                """

    prompt_template = ChatPromptTemplate.from_template(template)
    cooked_prompt = prompt_template.format_messages(
        student_prompt=student_prompt)
    response = llm.predict(input=cooked_prompt[0].content)

    return {"aiResponse": response}


@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    student_answers = body.get('studentAnswers')

    template = """Now the student received your questions and answered them in the following way:\n\n
                student answers: {student_answers}

                Now you will generate a learning path for the student based on his preferences. Make sure the 
                learning path is clear and easy to follow. You can use bullet points to make it more readable.\n
                Make sure the learning resources links work and relevant to the student's preferences.\n

                Formatting rules:
                - Format the output with not asterisks.
                - Format the output with proper bullet points if necessary.
                """

    prompt_template = ChatPromptTemplate.from_template(template)
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
    # print(f'>> cooked_prompt content {cooked_prompt[0].content}')
    # response = model.invoke(cooked_prompt)
    response_dict = output_parser.parse(response)
    print(type(response_dict))
    print(response_dict)

    # return {"message": response}

import os
import re
from openai import AsyncOpenAI
import json
from sqlmodel import select, Session
from db import get_session, DynamicVariable, Agent, PhoneNumber
from google.cloud import storage
from typing import Annotated
from fastapi import (
    Depends,
)

SessionDep = Annotated[Session, Depends(get_session)]

async def dynamic_variable_update(dynamicVarsId: str, session: Session, prompt: str) -> str:
    try:
        dynamicVar = session.exec(
            select(DynamicVariable).where(DynamicVariable.id == dynamicVarsId)
        ).first()
        print("dynamicVar.vars............................", dynamicVar)
        dynamicVarObj = dynamicVar.vars
        if dynamicVarObj:
            for dynamicKey, value in dynamicVarObj.items():
                placeholder = f"{{{{{dynamicKey}}}}}"
                prompt = prompt.replace(placeholder, str(value))
        print("Updated prompt with dynamic variables:-------------------------------------", prompt)
        return prompt
    except Exception as e:
        print(f"Failed to replace dynamic variables: {e}")

async def get_transcription(call_sid: str) -> dict:

    try:
        """Retrieve transcription JSON from GCP bucket"""
        client = storage.Client()
        bucket = client.bucket(os.getenv("GCP_STORAGE_BUCKET_NAME"))
        blob = bucket.blob(f"transcriptions/{call_sid}.json")
        print("blob.................................", call_sid, blob)
        # if not blob.exists():
        #     print("Transcription not found in GCP............................")
        #     raise HTTPException(status_code=404, detail="Transcription not found")
        text = json.loads(blob.download_as_text())
        if text:
            print("Transcription fetched successfully from GCP bucket")
        # print("text.............................", text)
        return text
    except Exception as e:
        print(f"Unable top fetch blob from bucket: {e}")
        return {"error": 'failed to get transcripiton'}

async def analyze_transcription(transcript: dict, questions: list) -> dict:
    """Process transcript through OpenAI API with dynamic questions based on their types."""
    client = AsyncOpenAI(api_key=os.getenv("ANALYSIS_OPENAI_API_KEY"))

    system_prompt = """You are an expert call transcript analyzer. Your task is to analyze call transcripts and answer specific questions based on the conversation content.
    Input Format
    You will receive:

    1. A call transcript
    2. A list of questions in this format:
        [
            {
                "id": 1744791230220,
                "type": "Boolean",
                "name": "Did the parent ask about availability at another centre?",
                "options": []
            }
        ]

    Question Types & Answer Requirements

    Boolean
    - Answer ONLY with "yes", "no", or "unknown"
    - Answer "unknown" if the topic is not discussed in the transcript at all
    - Answer "no" ONLY if there is explicit evidence of a negative response
    - Answer "yes" ONLY if there is explicit evidence of a positive response
    - DO NOT default to "no" just because you don't see evidence of "yes"

    Text
    - Provide a descriptive, informative answer
    - Use information directly from the transcript
    - Keep answers concise but complete
    - Use "unknown" if the topic is not discussed

    Numerical
    - Provide only numbers (integers or decimals)
    - Extract specific numerical values mentioned in the call
    - Use "unknown" if no relevant numbers are mentioned

    Selector
    - Choose ONLY from the provided options array
    - Select the option that best matches the transcript content
    - Use exact option text as provided
    - Use "unknown" if none of the options clearly match the discussion

    Unknown Answers
    - If a topic is not discussed in the transcript, ALWAYS respond with "unknown"
    - Do not make assumptions or inferences about topics not explicitly discussed
    - When in doubt, use "unknown" rather than guessing

    Output Format
    Always respond with valid JSON in exactly this structure:
    {
        "summary": "<A brief, informative summary of the call>",
        "key_points": ["<Main discussion points>"],
        "sentiment": "<positive | neutral | negative>",
        "action_items": ["<Follow-up tasks if any>"],
        "answers": {
            "<question_name": {
            "value": "<answer formatted according to its type>",
            "type": "<boolean | text | numerical | selector>"
            }
        }
    }
    CRITICAL: Always use the question name (the "name" field) as the key in the answers object, NOT the question ID (the numeric "id" field).

    **Guidelines:**
    - Base all answers strictly on transcript content
    - Do not make assumptions or inferences beyond what's clearly stated
    - For sentiment, consider the overall tone and outcome of the conversation
    - Include specific action items only if explicitly mentioned or clearly implied
    - ALWAYS use the question name (the "name" field) as the key in the answers object
    - NEVER use the question ID (the numeric "id" field) as the key
    - Ensure JSON is properly formatted and valid
    - Read the transcript carefully and match exact phrases or verbatim quotes or clear intent
    """

    # **Process questions into required format**
    processed_questions = {}
    for q in questions:
        question_key = q["name"]
        question_type = q["type"].lower()
        
        if question_type == "selector":
            processed_questions[question_key] = {"type": "selector", "options": q["options"]}
        elif question_type == "text":
            processed_questions[question_key] = {"type": "text"}
        elif question_type == "boolean":
            processed_questions[question_key] = {"type": "boolean"}
        elif question_type == "number":
            processed_questions[question_key] = {"type": "numerical"}

    user_prompt = f"""
    Analyze the following call transcription:

    {json.dumps(transcript, indent=2)}

    Please answer these questions according to the given data types:

    {json.dumps(processed_questions, indent=2)}
    """

    try:
        response = await client.chat.completions.create(
            model=os.getenv("ANALYSIS_OPENAI_MODEL") if os.getenv("ANALYSIS_OPENAI_MODEL") else "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )

        raw_response = response.choices[0].message.content.strip()
        raw_response = re.sub(r'```json|```', '', raw_response).strip()

        if not raw_response.startswith("{") or not raw_response.endswith("}"):
            raise ValueError(f"Invalid JSON format received: {raw_response}")

        try:
            analysis = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parsing error: {e}, received response: {raw_response}")

        required_keys = {"summary", "key_points", "sentiment", "action_items", "answers"}
        if not all(key in analysis for key in required_keys):
            raise ValueError(f"Missing required keys in OpenAI response: {analysis}")
        
        # **Ensure boolean answers are normalized and properly handle unknown cases**
        if analysis.get("answers"):
            for question, answer in analysis["answers"].items():
                if answer["type"] == "boolean":
                    llm_value = str(answer["value"]).strip().lower()
                    
                    # Extract keywords from the question (words longer than 3 chars)
                    keywords = [w.lower() for w in question.split() if len(w) > 3 and w.lower() not in ['does', 'did', 'have', 'has', 'what', 'when', 'where', 'which', 'would', 'will', 'from', 'that', 'this', 'there', 'their']]
                    
                    # Convert transcript to lowercase string for searching
                    transcript_text = json.dumps(transcript).lower()
                    
                    # Check if any relevant keywords are present in the transcript
                    topic_present = any(kw in transcript_text for kw in keywords)
                    
                    if not topic_present:
                        # If topic is not discussed, set to unknown
                        normalized_value = "unknown"
                    elif llm_value in ["yes", "no", "unknown"]:
                        normalized_value = llm_value
                    elif llm_value in ["true", "1"]:
                        normalized_value = "yes"
                    elif llm_value in ["false", "0"]:
                        normalized_value = "no"
                    else:
                        normalized_value = "unknown"
                        
                    analysis["answers"][question]["value"] = normalized_value
                
                # Ensure that any empty values are set to "unknown"
                if answer["value"] == "":
                    analysis["answers"][question]["value"] = "unknown"

        return analysis

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return {
            "summary": "",
            "key_points": [],
            "sentiment": "unknown",
            "action_items": [],
            "answers": {}
        }


AI_MODELS = {
    "TOGETHER_AI_Default": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "TOGETHER_AI_Llama4": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "TOGETHER_AI_Llama4_Scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "TOGETHER_AI_Gemma": "google/gemma-3-27b-it",
    "DEEPSEEK_Default" : "deepseek-chat",
    "GROQ_Default" : "llama-3.3-70b-versatile",
    "ANTHROPIC_Default": "claude-3-5-haiku-20241022",
    "ANTHROPIC_3_7_Sonnet": "claude-3-7-sonnet-20250219",
    "GEMINI_Default": "models/gemini-2.0-flash",
    "GEMINI_2_FLASH_LITE": "models/gemini-2.0-flash-lite",
    "OPENAI_Default": "gpt-4o",
    "OPENAI_GPT4o_Mini": "gpt-4o-mini-2024-07-18",
    "OPENAI_GPT4_1": "gpt-4.1-2025-04-14",
    "OPENAI_GPT4_1_Mini": "gpt-4.1-mini-2025-04-14",
    "OPENAI_GPT4_1_Nano": "gpt-4.1-nano-2025-04-14",
}

def strip_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import httpx

from dotenv import load_dotenv
from groq import Groq
from supabase import create_client, Client


load_dotenv()

app = FastAPI(title="Coderefine API", version="0.1.0")

# Build the list of allowed CORS origins from an environment variable.
# In production (Render), set: ALLOWED_ORIGINS=https://your-app.vercel.app
# Locally, leave it unset to default to ["*"] (same behaviour as before).
_allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
if _allowed_origins_raw.strip() == "*":
    _allowed_origins = ["*"]
else:
    _allowed_origins = [o.strip().rstrip("/") for o in _allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RefineRequest(BaseModel):
    code: str
    language: str
    goal: Optional[str] = "Improve readability, performance, and structure while preserving behavior."


class RefineResponse(BaseModel):
    refined_code: str
    summary: str
    suggestions: List[str]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    code_context: str
    language: str
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


class ChatVisionRequest(ChatRequest):
    image_base64: str
    image_question: str


class ComplexityAnalysisResponse(BaseModel):
    time_complexity: str
    space_complexity: str
    explanation: str


class ExtractTextResponse(BaseModel):
    extracted_text: str


class ExecuteRequest(BaseModel):
    code: str
    language: str
    stdin: Optional[str] = ""


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return Groq(api_key=api_key)


def get_supabase_client() -> Optional[Client]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(
            status_code=500, detail="Supabase client not configured."
        )
    
    # Verify the token with Supabase
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )
        return user_response.user
    except Exception as e:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )


def get_goal_specific_prompt(goal: str) -> tuple:
    """Return (system_prompt, instruction_suffix) based on the selected goal."""
    goal_lower = goal.lower()
    
    if "performance" in goal_lower or "speed" in goal_lower or "algorithmic" in goal_lower:
        system = (
            "You are Coderefine, an expert performance-focused software engineer. "
            "You receive source code and must produce a highly optimized version. "
            "Focus on algorithmic efficiency, reducing time complexity, eliminating redundant operations, "
            "and leveraging language-specific performance features. "
            "Keep behavior identical while making the code as fast as possible. "
            "Support Python, Java, C, C++, Rust, and JavaScript. "
            "Return only valid code in the target language."
        )
        instruction = (
            "Optimize this code for maximum performance and speed. "
            "Reduce time complexity where possible, eliminate redundant loops, "
            "use efficient data structures, and apply algorithmic improvements. "
            "Preserve all functionality exactly as-is."
        )
    elif "idiomatic" in goal_lower or "concise" in goal_lower:
        system = (
            "You are Coderefine, an expert in idiomatic and Pythonic code patterns. "
            "You receive source code and must refactor it to use language-specific idioms and best practices. "
            "Make the code more concise, readable, and aligned with the target language's conventions. "
            "Keep behavior identical while improving expressiveness. "
            "Support Python, Java, C, C++, Rust, and JavaScript. "
            "Return only valid code in the target language."
        )
        instruction = (
            "Refactor this code to be more idiomatic and concise. "
            "Use language-specific idioms, built-in functions, and best practices. "
            "Remove verbosity while keeping all functionality intact. "
            "Make the code express intent more clearly."
        )
    elif "document" in goal_lower or "comment" in goal_lower or "variable" in goal_lower:
        system = (
            "You are Coderefine, an expert code documentation specialist. "
            "You receive source code and must improve its readability through better naming and documentation. "
            "Add clear comments explaining logic, improve variable and function names for clarity, "
            "and structure code for maximum readability. "
            "Keep behavior identical while making code self-documenting. "
            "Support Python, Java, C, C++, Rust, and JavaScript. "
            "Return only valid code in the target language."
        )
        instruction = (
            "Improve code readability and documentation. "
            "Rename variables and functions for clarity, add helpful comments explaining complex logic, "
            "and structure the code logically. Preserve all functionality."
        )
    elif "bug" in goal_lower or "fix" in goal_lower:
        system = (
            "You are Coderefine, an expert code auditor and debugger. "
            "You receive source code and must identify potential bugs, edge cases, and vulnerabilities. "
            "Do NOT rewrite, fix, optimize, or restructure the code in any way. "
            "Return the code with its original structure and logic fully intact. "
            "The only addition allowed is inline comments marking each bug at its exact location, "
            "using the correct comment syntax for the target language (e.g. # BUG: ... for Python, // BUG: ... for Java/JS/C++). "
            "Do NOT correct the bug in the code itself — only annotate it as a comment explaining what's wrong and why. "
            "Support Python, Java, C, C++, Rust, and JavaScript. "
            "Return only valid code in the target language."
        )
        instruction = (
            "Analyze this code for potential bugs and vulnerabilities. "
            "Find: off-by-one errors, missing null checks, uncaught exceptions, "
            "type mismatches, race conditions, and edge cases. "
            "Do NOT fix the bugs. ONLY add inline comments (e.g., # BUG: ... or // BUG: ...) "
            "at the exact locations of the bugs, explaining the issue. "
            "Keep the original code logic and structure completely intact."
        )
    else:  # Default: General Polish
        system = (
            "You are Coderefine, an expert software engineer. "
            "You receive source code and must produce a refined version of the code, "
            "improving readability, performance, and structure while preserving behavior. "
            "Support common languages like Python, Java, C, C++, Rust, and JavaScript. "
            "Balance clarity, efficiency, and maintainability. "
            "Return only valid code in the target language."
        )
        instruction = (
            "Improve this code for better readability, performance, and maintainability. "
            "Apply general best practices, improve structure, and optimize performance where applicable. "
            "Preserve all functionality exactly as-is."
        )
    
    return system, instruction


@app.post("/api/refine", response_model=RefineResponse)
def refine_code(payload: RefineRequest, user = Depends(get_current_user)) -> RefineResponse:
    client = get_groq_client()

    system_prompt, instruction = get_goal_specific_prompt(payload.goal)

    chat_completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Language: {payload.language}\n\n"
                    f"Original code:\n{payload.code}\n\n"
                    f"Task: {instruction}"
                ),
            },
        ],
    )

    raw_content = chat_completion.choices[0].message.content.strip()
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        refined_code = "\n".join(lines).strip()
    else:
        refined_code = raw_content

    explanation_completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Explain code refinements briefly and list concrete suggestions. You MUST assign a clear severity tag like [CRITICAL], [HIGH], [MEDIUM], or [LOW] to every issue. Ensure your output uses categorized sections (e.g., Bugs, Vulnerabilities, Code Smells)."},
            {
                "role": "user",
                "content": (
                    f"Language: {payload.language}\n\n"
                    f"Original code:\n{payload.code}\n\n"
                    f"Refined code:\n{refined_code}\n\n"
                    "First, summarize the key improvements in 1-2 sentences on the very first line.\n"
                    "Then, provide a bullet list of concrete issues found, categorized by type (Bugs, Vulnerabilities, Code Smells).\n"
                    "For every bullet point, start with a severity tag (e.g., [HIGH] Null pointer...)."
                ),
            },
        ],
    )

    explanation = explanation_completion.choices[0].message.content
    lines = [line.strip(" -*#") for line in explanation.splitlines() if line.strip()]
    summary = lines[0] if lines else "Refinement complete."
    suggestions = lines[1:] if len(lines) > 1 else []

    supabase = get_supabase_client()
    if supabase:
        try:
            supabase.table("refinements").insert(
                {
                    "language": payload.language,
                    "original_code": payload.code,
                    "refined_code": refined_code,
                    "summary": summary,
                }
            ).execute()
        except Exception:
            # Storage failures should not break the main flow.
            pass

    return RefineResponse(refined_code=refined_code, summary=summary, suggestions=suggestions)


@app.post("/api/complexity", response_model=ComplexityAnalysisResponse)
def analyze_complexity(payload: RefineRequest, user = Depends(get_current_user)) -> ComplexityAnalysisResponse:
    """Analyze time and space complexity of code using AI."""
    client = get_groq_client()
    
    complexity_prompt = (
        "You are an expert algorithm analyst. Analyze the provided code and determine its time and space complexity. "
        "Provide the Big-O notation for both. Be precise and consider the actual implementation, not worst-case assumptions. "
        "If there are multiple operations, analyze the dominant one. Format your response as: "
        "TIME_COMPLEXITY: O(...) | SPACE_COMPLEXITY: O(...) | EXPLANATION: brief analysis"
    )

    if payload.goal and ("bug" in payload.goal.lower() or "fix" in payload.goal.lower()):
        complexity_prompt += (
            " IMPORTANT: You are in 'Find Bugs' mode. Analyze the exact complexity of the ORIGINAL, "
            "unmodified, buggy code provided. Do NOT analyze a hypothetical fixed or optimized version."
        )
    
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": complexity_prompt},
            {
                "role": "user",
                "content": (
                    f"Language: {payload.language}\n\n"
                    f"Analyze the time and space complexity of this code:\n\n{payload.code}"
                ),
            },
        ],
    )
    
    response_text = completion.choices[0].message.content
    
    # Parse the response
    time_complexity = "O(n)"  # defaults
    space_complexity = "O(1)"
    explanation = "Unable to parse complexity"
    
    try:
        # Try to extract from formatted response
        if "TIME_COMPLEXITY:" in response_text and "SPACE_COMPLEXITY:" in response_text:
            parts = response_text.split("|")
            for part in parts:
                part = part.strip()
                if part.startswith("TIME_COMPLEXITY:"):
                    time_complexity = part.replace("TIME_COMPLEXITY:", "").strip()
                elif part.startswith("SPACE_COMPLEXITY:"):
                    space_complexity = part.replace("SPACE_COMPLEXITY:", "").strip()
                elif part.startswith("EXPLANATION:"):
                    explanation = part.replace("EXPLANATION:", "").strip()
        else:
            # Fallback: return full response as explanation
            explanation = response_text[:500]
    except Exception:
        pass
    
    return ComplexityAnalysisResponse(
        time_complexity=time_complexity,
        space_complexity=space_complexity,
        explanation=explanation
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat_about_code(payload: ChatRequest, user = Depends(get_current_user)) -> ChatResponse:
    client = get_groq_client()

    messages = [
        {
            "role": "system",
            "content": (
                "You are Coderefine's code assistant. "
                "You answer questions about the provided code context, "
                "explain behavior, suggest improvements, and help debug while being concise."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Language: {payload.language}\n\n"
                f"Code context:\n{payload.code_context}\n\n"
                "User will now ask questions about this code."
            ),
        },
    ]

    for m in payload.messages:
        messages.append({"role": m.role, "content": m.content})

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
    )

    reply = completion.choices[0].message.content

    supabase = get_supabase_client()
    if supabase:
        try:
            supabase.table("chats").insert(
                {
                    "language": payload.language,
                    "code_context": payload.code_context,
                    "messages": [m.model_dump() for m in payload.messages],
                    "reply": reply,
                }
            ).execute()
        except Exception:
            pass

    return ChatResponse(reply=reply)


@app.post("/api/chat_vision", response_model=ChatResponse)
def chat_vision(payload: ChatVisionRequest, user = Depends(get_current_user)) -> ChatResponse:
    client = get_groq_client()

    messages = [
        {
            "role": "system",
            "content": (
                "You are Coderefine's code assistant with vision capabilities. "
                "You answer questions about the provided code context and the uploaded image. "
                "Explain behavior, suggest improvements, and help debug while being concise."
            ),
        }
    ]

    # Prepend chat history context (excluding the image message itself if it's already there)
    for m in payload.messages[:-1]:
        messages.append({"role": m.role, "content": m.content})
        
    # Append the image block
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text", 
                "text": f"Language: {payload.language}\nCode context:\n{payload.code_context}\n\nHere's an image the user uploaded. User's message: {payload.image_question}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": payload.image_base64
                }
            }
        ]
    })

    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=messages,
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Vision API failed: {str(e)}")

    supabase = get_supabase_client()
    if supabase:
        try:
            supabase.table("chats").insert(
                {
                    "language": payload.language,
                    "code_context": payload.code_context,
                    "messages": [m.model_dump() for m in payload.messages],
                    "reply": reply,
                }
            ).execute()
        except Exception:
            pass

    return ChatResponse(reply=reply)


PISTON_API = "https://emkc.org/api/v2/piston"
PISTON_RUNTIME_CACHE = []

@app.get("/api/runtimes")
async def get_runtimes():
    global PISTON_RUNTIME_CACHE
    if PISTON_RUNTIME_CACHE:
        return PISTON_RUNTIME_CACHE
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{PISTON_API}/runtimes")
            resp.raise_for_status()
            PISTON_RUNTIME_CACHE = resp.json()
            return PISTON_RUNTIME_CACHE
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch runtimes: {str(e)}")


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_code(payload: ExecuteRequest, user = Depends(get_current_user)):
    global PISTON_RUNTIME_CACHE
    if not PISTON_RUNTIME_CACHE:
        await get_runtimes()
        
    lang_map = {
        "python": "python",
        "javascript": "javascript",
        "java": "java",
        "c": "c",
        "cpp": "cpp",
        "rust": "rust"
    }
    
    piston_lang = lang_map.get(payload.language.lower())
    if not piston_lang:
        raise HTTPException(status_code=400, detail=f"Language '{payload.language}' is not mapped.")
        
    version = None
    for r in PISTON_RUNTIME_CACHE:
        if r["language"] == piston_lang or piston_lang in r.get("aliases", []):
            version = r["version"]
            break
            
    if not version:
        raise HTTPException(status_code=400, detail=f"Language '{piston_lang}' is not supported by Piston.")
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{PISTON_API}/execute",
                json={
                    "language": piston_lang,
                    "version": version,
                    "files": [{"content": payload.code}],
                    "stdin": payload.stdin or ""
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            run_stage = data.get("run", {})
            compile_stage = data.get("compile", {})
            
            stdout = run_stage.get("stdout", "")
            stderr = run_stage.get("stderr", "")
            if compile_stage and compile_stage.get("stderr"):
                stderr = compile_stage.get("stderr") + "\n" + stderr
                
            code = run_stage.get("code", 0)
            if compile_stage and compile_stage.get("code", 0) != 0:
                code = compile_stage.get("code")
                
            return ExecuteResponse(stdout=stdout, stderr=stderr, exit_code=code or 0)
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Execution timed out after 10 seconds.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@app.get("/health")
def health():
    return {"status": "ok"}


import io
import pypdf
import docx

@app.post("/api/extract_text", response_model=ExtractTextResponse)
async def extract_text(file: UploadFile = File(...), user = Depends(get_current_user)):
    filename = file.filename.lower()
    content = await file.read()
    
    # Check file size (approx 5MB limit, though frontend should also enforce)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
    
    extracted_text = ""
    
    try:
        if filename.endswith('.txt'):
            extracted_text = content.decode('utf-8')
        elif filename.endswith('.pdf'):
            reader = pypdf.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
            if not extracted_text.strip():
                raise HTTPException(status_code=400, detail="This PDF appears to have no extractable text (scanned/image-based PDFs aren't supported).")
        elif filename.endswith('.docx'):
            doc = docx.Document(io.BytesIO(content))
            extracted_text = "\n".join([p.text for p in doc.paragraphs])
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload .txt, .pdf, or .docx.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text from file: {str(e)}")
        
    # Truncate to safe length (~10,000 characters)
    max_length = 10000
    if len(extracted_text) > max_length:
        extracted_text = extracted_text[:max_length] + f"\n\n[... file truncated to first {max_length} characters ...]"
        
    return ExtractTextResponse(extracted_text=extracted_text)


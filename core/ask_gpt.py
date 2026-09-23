import os, sys, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from threading import Lock
import json_repair
import json 
from openai import OpenAI
import time
from requests.exceptions import RequestException
from core.config_utils import load_key

LOG_FOLDER = 'output/gpt_log'
LOCK = Lock()

def save_log(model, prompt, response, log_title = 'default', message = None):
    os.makedirs(LOG_FOLDER, exist_ok=True)
    log_data = {
        "model": model,
        "prompt": prompt,
        "response": response,
        "message": message
    }
    log_file = os.path.join(LOG_FOLDER, f"{log_title}.json")
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    else:
        logs = []
    logs.append(log_data)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)
        
def check_ask_gpt_history(prompt, model, log_title):
    # check if the prompt has been asked before
    if not os.path.exists(LOG_FOLDER):
        return False
    file_path = os.path.join(LOG_FOLDER, f"{log_title}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                if item.get("prompt") == prompt:
                    return item.get("response")
    return False

def check_is_hard_task(log_title: str) -> bool:
    """Determine if the task is a hard reasoning task based on log_title."""
    if not log_title:
        return False
    hard_titles = ['logical_chunking', 'translate_expressiveness', 'sentence_splitbymeaning', 'punctuation']
    return any(t in log_title for t in hard_titles) or log_title.startswith('asr_correction')

def resolve_api_config(is_hard: bool):
    """
    Resolve API key, base_url, model, and reasoning_effort based on task difficulty and split config.
    Returns: (api_key, base_url, model, reasoning_effort)
    """
    base_api = load_key("api")
    is_split_enabled = False
    try:
        is_split_enabled = bool(load_key("model_split.enabled"))
    except Exception:
        is_split_enabled = False

    if is_split_enabled:
        split_key = "model_split.hard_tasks" if is_hard else "model_split.easy_tasks"
        try:
            task_cfg = load_key(split_key) or {}
            raw_key = task_cfg.get("key")
            api_key = raw_key if raw_key and raw_key != 'not here' else base_api.get("key")
            base_url = task_cfg.get("base_url") or base_api.get("base_url")
            model = task_cfg.get("model") or base_api.get("model")
            effort = task_cfg.get("reasoning_effort")
            if not effort:
                effort = "high" if is_hard else "low"
            return api_key, base_url, model, effort
        except Exception:
            pass

    # Fallback to base configuration
    effort_key = "reasoning.hard_tasks" if is_hard else "reasoning.easy_tasks"
    try:
        effort = load_key(effort_key)
    except Exception:
        effort = "high" if is_hard else "low"
    return base_api.get("key"), base_api.get("base_url"), base_api.get("model"), effort

def normalize_base_url(base_url: str) -> str:
    """Normalize base_url for different providers (e.g. Google AI Studio, standard OpenAI proxies)."""
    if not base_url:
        return base_url
    base_url = base_url.strip()
    if "generativelanguage.googleapis.com" in base_url:
        if not base_url.endswith("/"):
            base_url += "/"
        if "openai" not in base_url:
            base_url = base_url.rstrip("/")
            if not base_url.endswith("v1beta"):
                base_url = base_url.rstrip("/") + "/v1beta"
            base_url = base_url + "/openai/"
        return base_url
    
    url = base_url.strip('/') + '/v1' if 'v1' not in base_url else base_url
    return url

def check_llm_support_json(model: str) -> bool:
    """Check if model natively supports response_format={'type': 'json_object'}."""
    if not model:
        return False
    try:
        configured_models = load_key("llm_support_json") or []
        if model in configured_models:
            return True
    except Exception:
        pass
    
    model_lower = model.lower()
    auto_families = ["gemini", "gpt-4", "gpt-3.5", "o1", "o3", "o4", "deepseek", "claude", "qwen"]
    return any(fam in model_lower for fam in auto_families)

def check_api(target="base") -> bool:
    """Test API connection for base, hard, or easy task model configuration."""
    try:
        base_api = load_key("api")
        if target == "hard":
            cfg = load_key("model_split.hard_tasks") or {}
        elif target == "easy":
            cfg = load_key("model_split.easy_tasks") or {}
        else:
            cfg = base_api
            
        raw_key = cfg.get("key")
        api_key = raw_key if raw_key and raw_key != 'not here' else base_api.get("key")
        base_url = cfg.get("base_url") or base_api.get("base_url")
        model = cfg.get("model") or base_api.get("model")
        
        if not api_key or api_key == 'not here':
            return False
            
        url = normalize_base_url(base_url)
        client = OpenAI(api_key=api_key, base_url=url, timeout=10.0)
        
        response_format = {"type": "json_object"} if check_llm_support_json(model) else None
        
        completion_args = {
            "model": model,
            "messages": [{"role": "user", "content": "Respond with {'message':'success'} in json format"}],
        }
        if response_format is not None:
            completion_args["response_format"] = response_format
            
        resp = client.chat.completions.create(**completion_args)
        return True
    except Exception as e:
        print(f"API Check failed for [{target}]: {e}")
        return False

def ask_gpt(prompt, response_json=True, valid_def=None, log_title='default', reasoning_effort='medium'):
    is_hard = check_is_hard_task(log_title)
    api_key, base_url, model, configured_effort = resolve_api_config(is_hard)
    
    with LOCK:
        history_response = check_ask_gpt_history(prompt, model, log_title)
        if history_response:
            return history_response
    
    if not api_key or api_key == 'not here':
        raise ValueError(f"⚠️API_KEY is missing")
    
    # SenseNova's JSON parsing requires system prompt to instruct JSON output
    import uuid
    system_prompt = f"You are a helpful assistant. (ReqID: {uuid.uuid4().hex[:8]})"
    if response_json:
        system_prompt += " Please output your response in JSON format."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    url = normalize_base_url(base_url)
    client = OpenAI(api_key=api_key, base_url=url)
    response_format = {"type": "json_object"} if response_json and check_llm_support_json(model) else None

    max_retries = 4
    for attempt in range(max_retries):
        try:
            completion_args = {
                "model": model,
                "messages": messages
            }
            if response_format is not None:
                completion_args["response_format"] = response_format
                
            if configured_effort:
                effort_str = str(configured_effort).lower().strip()
                if effort_str in ["none", "low", "medium", "high"]:
                    # Pass via extra_body (compatible with OpenAI o-series, DeepSeek, Google Gemini OpenAI compat)
                    completion_args["extra_body"] = {"reasoning_effort": effort_str}
                    
            if attempt == 0:
                task_type = "🧠 Hard Task" if is_hard else "⚡ Easy Task"
                print(f"[{task_type}] Target: {url} | Model: {model} | Reasoning: {configured_effort}")
                
            response = client.chat.completions.create(**completion_args)
            
            if hasattr(response, 'usage') and response.usage:
                try:
                    usage_dict = response.usage.model_dump()
                    prompt_tokens = usage_dict.get('prompt_tokens', 0) or 0
                    completion_tokens = usage_dict.get('completion_tokens', 0) or 0
                    total_tokens = usage_dict.get('total_tokens', 0) or (prompt_tokens + completion_tokens)
                    
                    reasoning_tokens = 0
                    if 'completion_tokens_details' in usage_dict and isinstance(usage_dict['completion_tokens_details'], dict):
                        reasoning_tokens = usage_dict['completion_tokens_details'].get('reasoning_tokens', 0) or 0
                    elif 'reasoning_tokens' in usage_dict and usage_dict.get('reasoning_tokens') is not None:
                        reasoning_tokens = usage_dict.get('reasoning_tokens', 0) or 0
                    
                    # For Google Gemini / OpenAI compatibility endpoints where thinking tokens are counted in total_tokens
                    if reasoning_tokens == 0 and total_tokens > (prompt_tokens + completion_tokens):
                        reasoning_tokens = total_tokens - (prompt_tokens + completion_tokens)
                        
                    print(f"   └── [Token Usage] Prompt: {prompt_tokens} | Completion: {completion_tokens} | 🤔 Thinking: {reasoning_tokens}")
                except Exception:
                    pass
            
            if response_json:
                try:
                    response_data = json_repair.loads(response.choices[0].message.content)
                    
                    # check if the response is valid, otherwise save the log and raise error and retry
                    if valid_def:
                        valid_response = valid_def(response_data)
                        if valid_response['status'] != 'success':
                            save_log(model, prompt, response_data, log_title="error", message=valid_response['message'])
                            raise ValueError(f"Validation failed: {valid_response['message']}")
                        
                    break  # Successfully accessed and parsed, break the loop
                except Exception as e:
                    response_content = response.choices[0].message.content
                    print(f"❎ JSON or Validation failed. Retrying: '''{response_content}'''")
                    save_log(model, prompt, response_content, log_title="error", message=str(e))
                    
                    messages.append({"role": "assistant", "content": response_content})
                    messages.append({"role": "user", "content": f"Your previous response failed: {str(e)}\nPlease carefully review the rules, ensure NO words are modified, added, or removed, and try again."})
                    
                    if attempt == max_retries - 1:
                        raise Exception(f"JSON/Validation still failed after {max_retries} attempts: {e}\n Please check your `output/gpt_log/error.json` to debug.")
            else:
                response_data = response.choices[0].message.content
                break  # Non-JSON format, break the loop directly
                
        except Exception as e:
            if attempt < max_retries - 1:
                error_msg = str(e).lower()
                if "429" in error_msg or "rpm" in error_msg or "rate limit" in error_msg or "quota_exceeded" in error_msg:
                    sleep_time = (attempt + 1) * 15
                    print(f"Rate limit hit (429). Retrying in {sleep_time}s ({attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                elif isinstance(e, RequestException):
                    print(f"Request error: {e}. Retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                else:
                    print(f"Unexpected error occurred: {e}\nRetrying...")
                    time.sleep(2)
            else:
                raise Exception(f"Still failed after {max_retries} attempts: {e}")
    with LOCK:
        if log_title != 'None':
            save_log(model, prompt, response_data, log_title=log_title)

    return response_data

if __name__ == '__main__':
    print(ask_gpt('hi there hey response in json format, just return 200.' , response_json=True, log_title=None))
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
                if item["prompt"] == prompt:
                    return item["response"]
    return False

def ask_gpt(prompt, response_json=True, valid_def=None, log_title='default', reasoning_effort='medium'):
    api_set = load_key("api")
    llm_support_json = load_key("llm_support_json")
    with LOCK:
        history_response = check_ask_gpt_history(prompt, api_set["model"], log_title)
        if history_response:
            return history_response
    
    if not api_set["key"]:
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
    
    base_url = api_set["base_url"].strip('/') + '/v1' if 'v1' not in api_set["base_url"] else api_set["base_url"]
    client = OpenAI(api_key=api_set["key"], base_url=base_url)
    response_format = {"type": "json_object"} if response_json and api_set["model"] in llm_support_json else None

    max_retries = 4
    for attempt in range(max_retries):
        try:
            completion_args = {
                "model": api_set["model"],
                "messages": messages
            }
            if response_format is not None:
                completion_args["response_format"] = response_format
                
            # Determine reasoning effort based on task difficulty
            hard_titles = ['logical_chunking', 'translate_expressiveness', 'sentence_splitbymeaning', 'punctuation']
            is_hard = any(t in log_title for t in hard_titles) or log_title.startswith('asr_correction')
            
            configured_effort = load_key("reasoning.hard_tasks") if is_hard else load_key("reasoning.easy_tasks")
            
            if configured_effort and configured_effort.lower() != "none":
                # Use extra_body to bypass OpenAI Python SDK version validation errors
                # This works for both native OpenAI models (like o1) and proxies (like DeepSeek)
                completion_args["extra_body"] = {"reasoning_effort": configured_effort}
                    
            if attempt == 0:
                task_type = "🧠 Hard Task" if is_hard else "⚡ Easy Task"
                print(f"[{task_type}] Using reasoning effort: {configured_effort}")
                
            response = client.chat.completions.create(**completion_args)
            
            if hasattr(response, 'usage') and response.usage:
                try:
                    usage_dict = response.usage.model_dump()
                    reasoning_tokens = 0
                    if 'completion_tokens_details' in usage_dict and isinstance(usage_dict['completion_tokens_details'], dict):
                        reasoning_tokens = usage_dict['completion_tokens_details'].get('reasoning_tokens', 0)
                    elif 'reasoning_tokens' in usage_dict:
                        reasoning_tokens = usage_dict.get('reasoning_tokens', 0)
                        
                    print(f"   └── [Token Usage] Prompt: {usage_dict.get('prompt_tokens', 0)} | Completion: {usage_dict.get('completion_tokens', 0)} | 🤔 Thinking: {reasoning_tokens}")
                except Exception:
                    pass
            
            if response_json:
                try:
                    response_data = json_repair.loads(response.choices[0].message.content)
                    
                    # check if the response is valid, otherwise save the log and raise error and retry
                    if valid_def:
                        valid_response = valid_def(response_data)
                        if valid_response['status'] != 'success':
                            save_log(api_set["model"], prompt, response_data, log_title="error", message=valid_response['message'])
                            raise ValueError(f"Validation failed: {valid_response['message']}")
                        
                    break  # Successfully accessed and parsed, break the loop
                except Exception as e:
                    response_content = response.choices[0].message.content
                    print(f"❎ JSON or Validation failed. Retrying: '''{response_content}'''")
                    save_log(api_set["model"], prompt, response_content, log_title="error", message=str(e))
                    
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
            save_log(api_set["model"], prompt, response_data, log_title=log_title)

    return response_data


if __name__ == '__main__':
    print(ask_gpt('hi there hey response in json format, just return 200.' , response_json=True, log_title=None))
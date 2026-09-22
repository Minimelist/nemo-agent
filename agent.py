from dotenv import load_dotenv
import requests
import json
import os
import subprocess

load_dotenv()  # Load environment variables from .env file
    
def list_files(path="."):
    answer = input(f"Do you want to list files in the directory {path}? (y/n): ")
    if answer.strip().lower() != "y":
        return "File listing canceled by user."
    else:
        try:
            entries = []
            for entry in os.scandir(path):
                entries.append(entry.name + ("/" if entry.is_dir() else ""))
            return "\n".join(entries) or "No files found."
        except FileNotFoundError:
            return "Directory not found."
        except Exception as e:
            return f"An error occurred: {e}"

def read_file(path):
    answer = input(f"Do you want to read the file at {path}? (y/n): ")
    if answer.strip().lower() != "y":
        return "File reading canceled by user."
    else:
        try:
          with open(path, "r", encoding="utf-8") as file:
            return file.read()
        except FileNotFoundError:
          return "File not found."
        except Exception as e:
          return f"An error occurred: {e}" 
      
def write_file(path, content):
    answer = input(f"Do you want to write to the file at {path}? (y/n): ")
    if answer.strip().lower() != "y":
        return "File writing canceled by user."
    else:
        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            return f"Successfully wrote to {path} with {len(content)} characters."
        except Exception as e:
            return f"An error occurred: {e}"
        
def run_command(command):
    answer = input(f"Do you want to run the command: {command}? (y/n): ")
    if answer.strip().lower() != "y":
        return "Command execution canceled by user."
    else:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=120
            )
            output = (result.stdout + result.stderr).strip()
            return output or f"(no output, exit code {result.returncode})"
        except Exception as e:
            return f"An error occurred: {e}"
        
TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command
}

TOOLS_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the directory to list files from."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to be read."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to write to."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute."
                    }
                },
                "required": ["command"]
            }
        }
    }
]

def run_tool(tool_call):
    tool_name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    print(f"Nemo wants to run tool: {tool_name}({args})")
    try:
        result = TOOLS[tool_name](**args)
        return result
    except Exception as e:
        return f"An error occurred: {e}"
    
def run_agent(messages):
    while True:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('ORAPI')}"
                },
            json={
                "model": os.getenv('MODEL'),
                "messages": messages,
                "tools": TOOLS_SCHEMAS
            }
        )
        if response.status_code != 200:
            print("HTTP status:", response.status_code)
            print("Response body:", response.text)
            return

        data = response.json()

        if "error" in data:
            print("OpenRouter error:", data["error"])
            return

        message = data["choices"][0]["message"]
        messages.append(message)
        
        #Model is not requesting any tool calls, so we can print the response and exit the loop
        if not message.get("tool_calls"):
            print("Nemo Agent:", message["content"])
            break
          
        for tool_call in message["tool_calls"]:
            result = run_tool(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result
            })

        
SYSTEM_PROMPT = """You are Nemo, a helpful AI agent that can assist with various tasks. You have access to the following tools:
1. list_files(path): List files in a directory.
2. read_file(path): Read the content of a file and return its contents.
3. write_file(path, content): Write content to a file.
4. run_command(command): Run a shell command and return its output."""
def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Welcome to Nemo Agent! Type 'exit' or 'quit' to end the session.")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ("exit", "quit"):
            print("Exiting the chat.")
            break
        messages.append({"role": "user", "content": user_input})
        run_agent(messages)

if __name__ == "__main__":
    main()
        
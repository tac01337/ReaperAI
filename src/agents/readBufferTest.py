# import sys
# from subprocess import Popen, PIPE

# with Popen(["msfconsole", "-q"], stdout=PIPE) as p:
#     while True:
#         text = p.stdout.read1().decode("utf-8")
#         print(text, end='', flush=True)
#         # TODO: Write the rest of the logic here and terminate `process` if needed


"""
GPT example
"""
import subprocess
import threading

# Function to read and process stdout
def read_stdout(process, on_output):
    for line in iter(process.stdout.readline, b''):
        on_output(line.strip())

# Callback function to process each line of output
def process_output(line):
    print(f"Processing: {line}")
    # Here, implement your logic to generate autocompletion suggestions

def llm_process_output(line):
    # Here, implement your logic to generate autocompletion suggestions
    if("msf6" in line):
        print("msf6 found: ", line)
        return "use auxiliary/scanner/ssh/ssh_login"
    return ""

def monitor_and_respond(process):
    while True:
        line = process.stdout.read1()
        # line = process.stdout.readline()
        if not line:
            break  # End of output
        response = llm_process_output(line)  # Interpret and decide on a response
        if response:
            process.stdin.write(response + "\n")
            process.stdin.flush()
# Running the process
def run_process(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

    # Start a thread to read stdout
    stdout_thread = threading.Thread(target=read_stdout, args=(process, llm_process_output))
    stdout_thread.start()

    # Wait for the process to complete and the thread to finish
    process.wait()
    stdout_thread.join()

# Example command (Replace 'your_command_here' with your actual command)
command = ["msfconsole", "-q"]
run_process(command)
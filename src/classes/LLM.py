import time
import tiktoken
import typing
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from classes.Database import DbStorage
from classes.TaskTree import TaskTree
from classes.Host import Host
from llms.llm_connection import LLMConnection
from dataclasses import dataclass
from mako.template import Template
from output_filter import command_output_cleaner

@dataclass
class LLMResult:
    result: typing.Any
    prompt: str
    answer: str
    duration: float = 0
    tokens_query: int = 0
    tokens_response: int = 0


TPL_NEXT = Template(filename='prompts/query_next_command.txt')
TPL_NEXT_I = Template(filename='prompts/query_next_icommand.txt')
TPL_ANALYZE = Template(filename="prompts/analyze_cmd.txt")
TPL_ANALYZE_PEXPECT = Template(filename="prompts/analyze_pexpect.txt")
TPL_STATE = Template(filename="prompts/update_state.txt")
TPL_EXPECT = Template(filename="prompts/expect_prompt.txt")
TPL_OBJECTIVES = Template(filename="prompts/objectives.txt")
TPL_EVALUATE_PROGRESS = Template(filename="prompts/evaluate_progress.txt")
TPL_EVALUATE_TASK_PROGRESS = Template(filename="prompts/evaluate_task_progress.txt")

class LLMWithState:
    def __init__(self, run_id, llm_connection, history, config, constraints, current_task, current_role, task_tree):
        self.llm_connection = llm_connection
        self.target = config.target
        self.db = history
        self.run_id = run_id
        self.constraints = constraints
        self.current_task = current_task
        self.current_role = current_role
        self.task_tree = task_tree
        self.analyzation = ""
        self.state = f"""
        """

    def get_state_size(self, model):
        return num_tokens_from_string(model, self.state)

    def get_next_cmd(self):

        model = self.llm_connection.get_model()

        state_size = self.get_state_size(model)
        template_size = num_tokens_from_string(model, TPL_NEXT.source)

        history = get_cmd_history_v3(model, self.llm_connection.get_context_size(), self.run_id, self.db, state_size+template_size)
        response = self.create_and_ask_prompt_text(
            TPL_NEXT, 
            history=history, 
            state=self.state, 
            target=self.target, 
            constraints=self.constraints,
            current_task=self.current_task,
            current_role=self.current_role,
            task_tree=self.task_tree,
            analyzation=self.analyzation
            )
        # print(response)
        response.result = command_output_cleaner(response.result)
        return response
    def get_next_icmd(self, before, history, role, analyzation):

        model = self.llm_connection.get_model()

        state_size = self.get_state_size(model)
        template_size = num_tokens_from_string(model, TPL_NEXT_I.source)

        history = get_cmd_history_v3(model, self.llm_connection.get_context_size(), self.run_id, self.db, state_size+template_size)
        response = self.create_and_ask_prompt_text(
            TPL_NEXT_I, 
            history=history, 
            state=self.state, 
            target=self.target, 
            constraints=self.constraints,
            current_task=self.current_task,
            current_role=role,
            task_tree=self.task_tree,
            analyzation=analyzation,
            before=before
            )
        # print(response)
        response.result = command_output_cleaner(response.result)
        return response

    def analyze_result(self, cmd, result, error, summary_max_chars):

        model = self.llm_connection.get_model()
        ctx = self.llm_connection.get_context_size()
        state_size = num_tokens_from_string(model, self.state)
        target_size = ctx - SAFETY_MARGIN - state_size 

        # ugly, but cut down result to fit context size
        result = trim_result_front(model, target_size, result)
        return self.create_and_ask_prompt_text(TPL_ANALYZE, cmd=cmd, resp=result, facts=self.state, stderr=error, summary_max_chars=summary_max_chars)
    
    def analyze_interactive_result(self, cmd, before, facts, summary_max_chars):

        # model = self.llm_connection.get_model()
        # ctx = self.llm_connection.get_context_size()
        # state_size = num_tokens_from_string(model, self.state)
        # target_size = ctx - SAFETY_MARGIN - state_size 

        # # ugly, but cut down result to fit context size
        # result = trim_result_front(model, target_size, result)
        result = self.create_and_ask_prompt_text(TPL_ANALYZE_PEXPECT, cmd=cmd, before=before, facts=facts, summary_max_chars=summary_max_chars)
        self.analyzation = result.result
        return result

    def update_state(self, cmd, result):

        # ugly, but cut down result to fit context size
        # don't do this linearly as this can take too long
        # model = self.llm_connection.get_model()

        # ctx = self.llm_connection.get_context_size()
        # state_size = num_tokens_from_string(model, self.state)
        # target_size = ctx - SAFETY_MARGIN - state_size
        # result = trim_result_front(model, target_size, result)
        # We summarize here to give the LLM forgetfulness
        result = self.create_and_ask_prompt_text(TPL_STATE, cmd=cmd, resp=result, facts=self.state)
        self.state = result.result
        return result
    
    def get_expect_matches(self, command):
        response = self.create_and_ask_prompt_text(TPL_EXPECT, command=command, facts=self.state)
        first = response.result.lstrip('```json\n')
        # # Remove ``` from the end of result
        response.result = first.rstrip('```')
        return response

    def get_objectives(self, stage, background=""):
        response = self.create_and_ask_prompt_text(TPL_OBJECTIVES, stage=stage, background=background)
        # Remove ```json\n from the start of result
        first = response.result.lstrip('```json\n')
        # Remove ``` from the end of result
        response.result = first.rstrip('```')
        # print("get_objectives\n", response)
        return response
    
    def evaluate_progress(self, stage, task, cur_time, start_time, max_time_per_task, recon_iterations, new_information, old_information, max_recon_iterations, min_new_information):
        response = self.create_and_ask_prompt_text(TPL_EVALUATE_PROGRESS, stage=stage, task=task, cur_time=cur_time, start_time=start_time, max_time_per_task=max_time_per_task, recon_iterations=recon_iterations, new_information=new_information, old_information=old_information, max_recon_iterations=max_recon_iterations, min_new_information=min_new_information)
        return response
    def evaluate_task_progress(self, stage, task, cur_time, start_time, max_time_per_task, recon_iterations, new_information, old_information, max_recon_iterations, min_new_information):
        response = self.create_and_ask_prompt_text(TPL_EVALUATE_TASK_PROGRESS, stage=stage, task=task, cur_time=cur_time, start_time=start_time, max_time_per_task=max_time_per_task, recon_iterations=recon_iterations, new_information=new_information, old_information=old_information, max_recon_iterations=max_recon_iterations, min_new_information=min_new_information)
        return response
    
    def get_current_state(self):
        # The memory for the LLM
        return self.state
    
    def set_current_task(self, task):
        self.current_task = task

    def set_current_analyzation(self, analyzation):
        self.analyzation = analyzation
    
    def create_and_ask_prompt_text(self, template, **params):
        # prepare the prompt
        prompt = template.render(**params)
        console = Console();
        console.print(Panel.fit(prompt, title="Prompt", border_style="green"))
        tic = time.perf_counter()
        result, tok_query, tok_res = self.llm_connection.exec_query(self.llm_connection.get_model(), self.llm_connection.get_context_size(), prompt)
        toc = time.perf_counter()
    
        return LLMResult(result, prompt, result, toc - tic, tok_query, tok_res)
    
def num_tokens_from_string(model: str, string: str) -> int:
    """Returns the number of tokens in a text string."""

    # I know this is crappy for all non-openAI models but sadly this
    # has to be good enough for now
    if model.startswith("gpt-"):
        encoding = tiktoken.encoding_for_model(model)
    else:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(string))

STEP_CUT_TOKENS : int = 128
SAFETY_MARGIN : int = 128

# create the command history. Initially create the full command history, then
# try to trim it down
def get_cmd_history_v3(model: str, ctx_size: int, run_id: int, db: DbStorage, token_overhead: int) -> str:
    result: str = ""

    # get commands from db
    cmds = db.get_cmd_history(run_id)
    # print(cmds)
    # create the full history
    for itm in cmds:
        # result = result + '$ ' + itm[0] + "\n" + itm[1]
        result = result + '$ ' + itm[0] + "\n"

    # trim it down if too large
    cur_size = num_tokens_from_string(model, result)
    
    allowed = ctx_size - SAFETY_MARGIN - token_overhead
    return trim_result_front(model, allowed, result)

# this is acutally used for stable beluga
def wrap_it_for_llama(prompt):

 def wrap_it_for_llama(prompt):
    return f"""### System:
you are a concise but helful learning tool that aids students trying to find security vulnerabilities

### User:
{prompt}

### Assistant:
"""

# TODO: this is an old exmaple for thebloke-llama
#def wrap_it_for_llama(prompt):
#    return f"""<s>[INST] <<SYS>>
#You are a helpful, respectful, concise and honest assistant. Always answer as helpfully as possible.
#
#If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.
#<</SYS>>
#
#[INST]{prompt}[/INST]
#"""


# trim it down if too large
STEP_CUT_TOKENS = 32

# this is ugly, but basically we only have an approximation how many tokens
# we are currently using. So we cannot just cut down to the desired size
# what we're doing is:
#   - take our current token count
#   - use the minimum of (current_count, desired count *2)
#     - this get's us roughly in the ballpark of the desired size
#     - as long as we assume that 2 * desired-count will always be larger
#       than the unschaerfe introduced by the string-.token conversion
#   - do a 'binary search' to cut-down to the desired size afterwards
#
# this should reduce the time needed to do the string->token conversion
# as this can be long-running if the LLM puts in a 'find /' output
def trim_result_front(model, target_size, result):
    cur_size = num_tokens_from_string(model, result)

    TARGET_SIZE_FACTOR = 3
    if cur_size > TARGET_SIZE_FACTOR * target_size:
        print(f"big step trim-down from {cur_size} to {2*target_size}")
        result = result[:TARGET_SIZE_FACTOR*target_size]
        cur_size = num_tokens_from_string(model, result)
   
    while cur_size > target_size:
        print(f"need to trim down from {cur_size} to {target_size}")
        diff = cur_size - target_size
        step = int((diff + STEP_CUT_TOKENS)/2)
        result = result[:-step]
        cur_size = num_tokens_from_string(model, result)

    return result

import psycopg2
import os
from dataclasses import dataclass


@dataclass
class DbStorage:
    dbname: str = "memory"
    user: str = "user"
    password: str = "mysecretpassword"
    host: str = "localhost"
    port: int = 5432

    insert_into_runs = """
    INSERT INTO runs (model, context_size, state, started_at, configuration, host) 
    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s) 
    RETURNING id
    """

    insert_into_queries = """
    INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response, prompt, answer) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    insert_into_commands = """
    INSERT INTO commands (run_id, name, stdout)
    VALUES (%s, %s, %s)
    """

    select_cmd_from_queries = """
    SELECT cmd_id, query, response, duration, tokens_query, tokens_response 
    FROM queries 
    WHERE run_id = %s and round = %s
    """



    def connect(self):
        try:
            self.db = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=os.getenv("POSTGRES_PASS") or self.password,
                host=self.host,
                port=self.port,
            )
        except psycopg2.Error as e:
            print(f"An error occurred while connecting to the database: {e}")
        self.cursor = self.db.cursor()

    def insert_or_select_cmd(self, name:str) -> int:
        self.cursor.execute("SELECT id, name FROM commands WHERE name = %s", (name, ))
        results = self.cursor.fetchall()
        if len(results) == 0:
            self.cursor.execute("INSERT INTO commands (name) VALUES (%s) RETURNING id", (name, ))
            self.db.commit()
            return self.cursor.fetchone()[0]
        elif len(results) == 1:
            return results[0][0]
        else:
            print("this should not be happening: " + str(results))
            return -1
        
    def setup(self):
        self.query_cmd_id = self.insert_or_select_cmd('query_cmd')
        self.analyze_response_id = self.insert_or_select_cmd('analyze_response')
        self.state_update_id = self.insert_or_select_cmd('update_state')

    def create_new_run(self, args):
        self.cursor.execute(
            self.insert_into_runs,
            (args.model, args.context_size, "in progress", str(args), args.target.ip),
        )
        self.db.commit()
        return self.cursor.fetchone()[0]

    def add_log_query(self, run_id, round, cmd, result, answer):
        self.cursor.execute(
            self.insert_into_queries,
            (
                run_id,
                round,
                self.query_cmd_id,
                cmd,
                result,
                answer.duration,
                answer.tokens_query,
                answer.tokens_response,
                answer.prompt,
                answer.answer,
            ),
        )
        self.db.commit()

    def add_log_command(self, run_id, name, stdout):
        self.cursor.execute(
            self.insert_into_commands,
            (
                run_id,
                name,
                stdout,
            ),
        )
        self.db.commit()
        
    def add_log_analyze_response(self, run_id, round, cmd, result, answer):
        self.cursor.execute(
            self.insert_into_queries,
            (
                run_id,
                round,
                self.analyze_response_id,
                cmd,
                result,
                answer.duration,
                answer.tokens_query,
                answer.tokens_response,
                answer.prompt,
                answer.answer,
            ),
        )
        self.db.commit()

    def add_log_update_state(self, run_id, round, cmd, result, answer):
        if answer != None:
            self.cursor.execute(
                self.insert_into_queries,
                (
                    run_id,
                    round,
                    self.state_update_id,
                    cmd,
                    result,
                    answer.duration,
                    answer.tokens_query,
                    answer.tokens_response,
                    answer.prompt,
                    answer.answer,
                ),
            )
        else:
            self.cursor.execute(
                self.insert_into_queries,
                (run_id, round, self.state_update_id, cmd, result, str(0), str(0), str(0), '', '')
            )
        self.db.commit()

    def add_ports(self, run_id, ports):
        self.cursor.execute(
            "update runs set ports = %s where id = %s", (ports, run_id)
        )
        self.db.commit()
    
    def add_services(self, run_id, services):
        self.cursor.execute(
            "update runs set services = %s where id = %s", (services, run_id)
        )
        self.db.commit()

    def get_round_data(
        self,
        run_id,
        round,
    ):
        self.cursor.execute(
            self.select_cmd_from_queries,
            (run_id, round),
        )
        rows = self.cursor.fetchall()
        print(rows)
        result = []
        for row in rows:
            if row[0] == self.query_cmd_id:
                cmd = row[1]
                size_resp = str(len(row[2]))
                duration = f"{row[3]:.4f}"
                tokens = f"{row[4]}/{row[5]}"
                reason = row[2]
                analyze_time = f"{row[3]:.4f}"
                analyze_token = f"{row[4]}/{row[5]}"
                state_time = f"{row[3]:.4f}"
                state_token = f"{row[4]}/{row[5]}"
        result = [duration, tokens, cmd, size_resp]
        result += [analyze_time, analyze_token, reason]
        result += [state_time, state_token]
        return result

    def get_max_round_for(self, run_id):
        run = self.cursor.execute(
            "select max(round) from queries where run_id = %s", (run_id,)
        ).fetchone()
        return run[0] if run != None else None

    def get_run_data(self, run_id):
        run = self.cursor.execute(
            "select * from runs where id = %s", (run_id,)
        ).fetchone()
        return (run[1], run[2], run[4], run[3], run[7], run[8]) if run != None else None

    def get_log_overview(self):
        result = {}
        self.cursor.execute("select run_id, max(round) from queries group by run_id")
        max_rounds = self.cursor.fetchall()
        for row in max_rounds:
            state = self.cursor.execute(
                "select state from runs where id = %s", (row[0],)
            ).fetchone()
            last_cmd = self.cursor.execute(
                "select query from queries where run_id = %s and round = %s",
                (row[0], row[1]),
            ).fetchone()
            result[row[0]] = {
                "max_round": int(row[1]) + 1,
                "state": state[0],
                "last_cmd": last_cmd[0],
            }
        return result

    def get_cmd_history(self, run_id):
        self.cursor.execute(
            "select query, response from queries where run_id = %s and cmd_id = %s order by round asc",
            (run_id, self.query_cmd_id),
        )
        rows = self.cursor.fetchall()
        return [[row[0], row[1]] for row in rows]

    def commit(self):
        self.db.commit()

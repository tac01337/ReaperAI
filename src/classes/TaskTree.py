from rich.table import Table
from dataclasses import dataclass

from dataclasses import dataclass, field

@dataclass
class TaskTree:
    task_tree: dict = field(default_factory=lambda: {
        "name": "Root",
        "description": "Pentesting Task Tree",
        "status": "pending",
        "children": []
    })

    def add_task_to_tree(self, parent_task_name, task_name, description):
        # print("Adding Task", task_name)
        parent_task = self.find_task(self.task_tree, parent_task_name)
        if parent_task is not None:
            parent_task["children"].append({
                "name": task_name,
                "description": description,
                "status": "pending",
                "children": []
            })

    def find_task(self, task, name):
        if task["name"] == name:
            return task
        for child in task.get("children", []):
            result = self.find_task(child, name)
            if result is not None:
                return result
        return None

    def get_task_tree(self):
        return self.task_tree

    def update_task_status(self, parent_task_name, task_name, status):
        task = self.find_task(self.task_tree, task_name)
        if task:
            task["status"] = status

    def generate_task_summary(self, task=None, depth=0):
        if task is None:
            task = self.task_tree
        prefix = "  " * depth
        summary = f"{prefix}- {task['name']} ({task['status']}): {task['description']}\n"
        for child in task.get("children", []):
            summary += self.generate_task_summary(child, depth + 1)
        return summary
    

    def to_table(self):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Description")

        def add_tasks_to_table(task, depth=0):
            prefix = "  " * depth
            table.add_row(prefix + task['name'], task['status'], task['description'])
            for child in task.get("children", []):
                add_tasks_to_table(child, depth + 1)

        add_tasks_to_table(self.task_tree)
        return table
from pprint import pprint
import uuid


class Node:
    def __init__(self, title, task_description, parent=None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.task_description = task_description
        self.parent = parent
        self.children = []
        self.summary = ""          # compressed summary for this node
        self.recent_msgs = []      # full messages only for this node

    def add_msg(self, role, content):
        self.recent_msgs.append({"role": role, "content": content})

    def update_summary(self, summary):
        self.summary = summary


class ConversationTree:
    def __init__(self):
        self.root = Node(title="root", task_description="", parent=None)
        self.current = self.root

    # -----------------------------------------------------------
    # Node creation / movement
    # -----------------------------------------------------------

    def enter_subtask(self, title, task_description):
        """Create a child node under current and move into it."""
        self.add_message("system", f"[Enter Subtask]: {title}")
        new_node = Node(title=title, task_description=task_description, parent=self.current)
        self.current.children.append(new_node)
        self.current = new_node
        return new_node

    def return_to_parent(self, return_value):
        """Move to parent node if possible."""
        if self.current.parent is not None:
            self.current = self.current.parent
        else:
            raise ValueError("Current node is the root node, cannot return to parent.")
        self.add_message("system", f"[Return Value]: {return_value}")
        return self.current

    # -----------------------------------------------------------
    # Message handling
    # -----------------------------------------------------------

    def add_message(self, role, content):
        """
        Add message to current node.
        You can optionally compress recent_msgs to summary elsewhere.
        """
        self.current.add_msg(role, content)

    # -----------------------------------------------------------
    # Navigation decision
    # -----------------------------------------------------------

    def navigator_decision(self, user_message, classification_func):
        """
        classification_func receives:
            - current task title
            - current summary
            - user message
        It must return:
            "stay", "enter_subtask", or "back_to_parent"
        """
        return classification_func(
            self.current.title,
            self.current.summary,
            user_message
        )

    # -----------------------------------------------------------
    # Context Builder
    # -----------------------------------------------------------

    def get_context(self):
        """
        Build the final prompt context from internal tree state.

        Visibility rules:
        - summaries of ancestors
        - summaries of siblings
        - full messages of the current node
        """
        context = []

        # 1. ancestor summaries (root → parent → current)
        ancestors = []
        node = self.current.parent
        while node is not None:
            ancestors.append(node)
            node = node.parent
        ancestors.reverse()
        
        for a in ancestors:
            context.append({
                "role": "system",
                "content": f"[Ancestor Task: {a.title}] {a.summary}"
            })

        # 2. sibling summaries
        if self.current.parent is not None:
            siblings = [
                c for c in self.current.parent.children if c is not self.current
            ]
            if siblings:
                sib_text = "\n".join(
                    f"- {s.title}: {s.summary}" for s in siblings
                )
                if sib_text.strip():
                    context.append({
                        "role": "system",
                        "content": f"[Sibling Tasks]\n{sib_text}"
                    })

        # 3. current node summary
        context.append({
            "role": "system",
            "content": f"[Current Task: {self.current.title}] {self.current.task_description}"
        })

        # 4. full recent messages of the current node
        for msg in self.current.recent_msgs:
            context.append(msg)

        return context

    def update_summary(self, title, summary):
        self.current.title = title
        self.current.summary = summary

tree = ConversationTree()


tree.add_message("user", "hi what is the weather in taipei")
# user starts a task
tree.enter_subtask("check weather", "Check and return the weather in taipei.")
tree.add_message("assistant", "The weather in taipei is rainy.")

pprint(tree.get_context())

# user starts unrelated task → navigate
decision = "back_to_parent"  # from classifier model
if decision == "back_to_parent":
    tree.update_summary(title="check weather", summary="User asked to check weather in taipei. Assistant responded with 'rainy'.")
    tree.return_to_parent("rainy")
user_message = "search for professor A B C"

tree.add_message("user", user_message)

tree.enter_subtask("search professor research areas", "Search for professor A B C's research areas.")
tree.add_message("assistant", "Professor A B C's research areas are in computer science and artificial intelligence.")
tree.return_to_parent("computer science and artificial intelligence")

# Later, build context for LLM API call
context = tree.get_context()
pprint(context)

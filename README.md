# Function Calling Agent with LlamaIndex

A CLI-based function calling agent built with LlamaIndex that can interact with users and call various functions to help with tasks.

## Features

- Interactive CLI interface
- Function calling capabilities using LlamaIndex ReActAgent
- Multiple example functions:
  - Weather lookup (mock)
  - Mathematical calculations
  - Web search (mock)
  - Current time
  - Todo list management

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   Or export it as an environment variable:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

Run the agent:
```bash
python agent.py
```

Once started, you can interact with the agent:
- Ask questions that require function calls (e.g., "What's the weather in New York?")
- Perform calculations (e.g., "Calculate 15 * 23")
- Create todos (e.g., "Create a todo item: Buy groceries with high priority")
- Get current time (e.g., "What time is it?")
- Type `help` to see available functions
- Type `exit` or `quit` to end the session

## Example Interactions

```
You: What's the weather in London?
Agent: [Calls get_weather function] The weather in London is sunny, 72°F with light winds.

You: Calculate 25 * 17
Agent: [Calls calculate function] The result of 25 * 17 is 425

You: What time is it?
Agent: [Calls get_current_time function] Current date and time: 2024-01-15 14:30:45
```

## Customization

You can easily add more functions by:
1. Defining a new function with a docstring
2. Adding it to the `tools` list in `agent.py`
3. The agent will automatically understand how to use it based on the function signature and docstring

## Notes

- The weather and web search functions are mock implementations. Replace them with real API integrations for production use.
- The agent uses GPT-4 by default. You can change the model in the `OpenAI` initialization.
- Make sure you have sufficient OpenAI API credits for the model you're using.


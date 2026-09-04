from agent_context import AgentMemory, plan_next_step
from agent_engine import detect_intent

# one AgentMemory per user session (store in st.session_state, not global)
memory = st.session_state.setdefault("memory", AgentMemory())

def handle_user_message(user_input, memory):
    intent = detect_intent(user_input)
    step = plan_next_step(intent, user_input, memory)
    memory.log(user_input, intent, step)

    if step["action"] == "ASK_PRODUCT":
        return "What product would you like?"

    if step["action"] == "SEARCH":
        results = search_products(step["payload"]["keyword"], step["payload"]["budget"])
        memory.remember_search(results, step["payload"]["budget"], step["payload"]["quantity"])
        return format_results(results)

    if step["action"] == "RUN_PURCHASE_PIPELINE":
        # goes through quote -> policy -> risk -> approval -> payment
        return run_purchase_pipeline(step["payload"]["product"], step["payload"]["quantity"])

    ...
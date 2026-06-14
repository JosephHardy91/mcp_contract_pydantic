from src.agent.run import tick_tock_exploration_loop
if __name__=="__main__":
    import asyncio
    while True:
        user_input = input(">")
        asyncio.run(tick_tock_exploration_loop(user_input))
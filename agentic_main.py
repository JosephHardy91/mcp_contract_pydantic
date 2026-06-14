from src.agent.run import tick_tock_exploration_loop
async def main():
    while True:
        user_input = input("> ")
        await tick_tock_exploration_loop(user_input)


if __name__=="__main__":
    import asyncio
    asyncio.run(main())